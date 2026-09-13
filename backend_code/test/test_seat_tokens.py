"""A seat's token, not its uuid, is what lets someone act as that player.

Every player's uuid is on every screen — player_list carries them all — so
anything that trusted a uuid would let any player act as any other, or read
their hand. These drive the real handlers to check that nothing does.
"""
import json

import pytest

from Database import database
from test.seats import TableSockets, join_over_http, token_for, view


@pytest.fixture
def clients(tmp_path, monkeypatch):
    import Main

    db_file = str(tmp_path / "test_game_state.db")
    monkeypatch.setattr(database, "get_database", lambda: db_file)
    database.build_game_state_table()
    Main.app.config['TESTING'] = True

    with Main.app.test_client() as http:
        table = TableSockets()
        yield http, table
        table.disconnect()


def _lobby(http, sock, names=('Ann', 'Bob', 'Cal', 'Dee', 'Eve')):
    code = http.get("/create").get_json()['game_code']
    return code, [sock.seat(http, code, name) for name in names]


def _stranger():
    """A socket that has never joined anything."""
    import Main

    return Main.socketio.test_client(Main.app)


def _named(received, name):
    return [message['args'][0] for message in received if message['name'] == name]


@pytest.mark.unit
def test_joining_hands_back_a_token_that_is_not_the_uuid(clients):
    http, _ = clients
    code = http.get("/create").get_json()['game_code']

    body = http.get(f"/join/{code}?nick_name=Ann").get_json()

    assert body['player_token']
    assert body['player_token'] != body['new_player_uuid']


@pytest.mark.unit
def test_no_token_ever_reaches_a_screen(clients):
    """Not in a view fetched over HTTP, and not in any broadcast."""
    http, sock = clients
    code, uuids = _lobby(http, sock)
    sock.emit('start_game', {'game_code': code, 'player_uuid': uuids[0]})

    sent = json.dumps([message['args'] for message in sock.get_received()])
    sent += json.dumps([view(http, code, uuid) for uuid in uuids])

    for uuid in uuids:
        assert token_for(uuid) not in sent


@pytest.mark.unit
def test_a_view_is_only_given_for_the_players_own_token(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)

    assert view(http, code, uuids[1])['uuid'] == uuids[1]

    response = http.get(f"/game/{code}/player")
    assert response.status_code == 404
    assert response.get_json()['error'] == 'player_not_found'


@pytest.mark.unit
def test_a_uuid_in_the_url_no_longer_opens_anyones_hand(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)
    sock.emit('start_game', {'game_code': code, 'player_uuid': uuids[0]})

    response = http.get(f"/game/{code}/player/{uuids[1]}")

    assert b'player_hand' not in response.data


@pytest.mark.unit
def test_a_token_is_only_good_at_its_own_table(clients):
    http, sock = clients
    _, uuids = _lobby(http, sock)
    other = http.get("/create").get_json()['game_code']
    join_over_http(http, other, 'Zed')

    response = http.get(f"/game/{other}/player", headers={'X-Player-Token': token_for(uuids[0])})

    assert response.status_code == 404


@pytest.mark.unit
def test_naming_the_host_does_not_make_you_the_host(clients):
    """Bob's socket says it is Ann. It is still Bob's socket."""
    http, sock = clients
    code, uuids = _lobby(http, sock)
    bob = sock.socket_of(uuids[1])
    bob.get_received()

    bob.emit('start_game', {'game_code': code, 'player_uuid': uuids[0]})

    errors = [error['message'] for error in _named(bob.get_received(), 'error')]
    assert errors == ['Only the host can start the game']
    assert view(http, code, uuids[0])['game_event_state'] == 'waiting-for-player-to-join'


@pytest.mark.unit
def test_an_action_lands_on_the_seat_the_socket_joined_as(clients):
    from Game.Modules.Avatars import ANIMAL_AVATARS

    http, sock = clients
    code, uuids = _lobby(http, sock, names=('Ann', 'Bob'))
    taken = {player['avatar'] for player in view(http, code, uuids[0])['player_list']}
    free = next(avatar for avatar in ANIMAL_AVATARS if avatar not in taken)
    bobs_before = view(http, code, uuids[1])['avatar']

    sock.socket_of(uuids[0]).emit('choose_avatar', {
        'game_code': code, 'player_uuid': uuids[1], 'avatar': free,
    })

    assert view(http, code, uuids[0])['avatar'] == free
    assert view(http, code, uuids[1])['avatar'] == bobs_before


@pytest.mark.unit
def test_a_socket_that_never_joined_cannot_act(clients):
    """Refused without being sent home: after a reconnect an action can reach
    the server before the join sent ahead of it."""
    http, sock = clients
    code, uuids = _lobby(http, sock)
    stranger = _stranger()

    stranger.emit('start_game', {'game_code': code, 'player_uuid': uuids[0]})

    received = stranger.get_received()
    assert _named(received, 'error')
    assert _named(received, 'session_invalid') == []
    assert view(http, code, uuids[0])['game_event_state'] == 'waiting-for-player-to-join'
    stranger.disconnect()


@pytest.mark.unit
def test_a_socket_joined_at_one_table_cannot_act_at_another(clients):
    http, sock = clients
    _, uuids = _lobby(http, sock)
    other_code, other_uuids = _lobby(http, sock)

    sock.socket_of(uuids[0]).emit('start_game', {
        'game_code': other_code, 'player_uuid': other_uuids[0],
    })

    assert view(http, other_code, other_uuids[0])['game_event_state'] == 'waiting-for-player-to-join'


@pytest.mark.unit
def test_leaving_the_lobby_retires_the_token(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)
    token = token_for(uuids[1])

    sock.emit('leave_lobby', {'game_code': code, 'player_uuid': uuids[1]})

    response = http.get(f"/game/{code}/player", headers={'X-Player-Token': token})
    assert response.status_code == 404


@pytest.mark.unit
def test_a_fresh_token_retires_the_old_one():
    """What a seat changing hands will rely on: whoever held the old token can
    no longer act for the seat."""
    from Game.Components.GameState import GameState
    from Game.Systems.GameStateSystem import add_player, generate_player, issue_token, seat_for_token

    gs = GameState()
    ann = generate_player(name='Ann')
    add_player(gs, ann)

    old = issue_token(gs, str(ann.uuid))
    new = issue_token(gs, str(ann.uuid))

    assert seat_for_token(gs, old) == ''
    assert seat_for_token(gs, new) == str(ann.uuid)
