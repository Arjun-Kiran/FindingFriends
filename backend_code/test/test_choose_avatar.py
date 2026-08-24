"""End-to-end cover for the choose_avatar socket handler."""
import pytest

from Database import database
from Game.Modules.Avatars import ANIMAL_AVATARS, is_valid_avatar


@pytest.fixture
def app_clients(tmp_path, monkeypatch):
    """An HTTP client and a Socket.IO client over one throwaway database."""
    import Main

    db_file = str(tmp_path / "test_game_state.db")
    monkeypatch.setattr(database, "get_database", lambda: db_file)
    database.build_game_state_table()
    Main.app.config['TESTING'] = True

    with Main.app.test_client() as http_client:
        socket_client = Main.socketio.test_client(Main.app)
        yield http_client, socket_client
        if socket_client.is_connected():
            socket_client.disconnect()


def _joined_game(http_client, names=('Ann', 'Bob')):
    game_code = http_client.get("/create").get_json()['game_code']
    uuids = [
        http_client.get(f"/join/{game_code}?nick_name={name}").get_json()['new_player_uuid']
        for name in names
    ]
    return game_code, uuids


def _view(http_client, game_code, player_uuid):
    return http_client.get(f"/game/{game_code}/player/{player_uuid}").get_json()


def _error(socket_client):
    for message in socket_client.get_received():
        if message['name'] == 'error':
            return message['args'][0]
    return None


@pytest.mark.unit
def test_joining_over_http_assigns_an_avatar(app_clients):
    http_client, _ = app_clients
    game_code, uuids = _joined_game(http_client)

    view = _view(http_client, game_code, uuids[0])
    assert is_valid_avatar(view['avatar'])
    assert view['avatar_choices'] == ANIMAL_AVATARS


@pytest.mark.unit
def test_two_players_never_share_an_avatar(app_clients):
    http_client, _ = app_clients
    game_code, uuids = _joined_game(http_client, names=('Ann', 'Bob', 'Cal', 'Dee', 'Eve'))

    view = _view(http_client, game_code, uuids[0])
    avatars = [player['avatar'] for player in view['player_list']]
    assert len(set(avatars)) == len(avatars)


@pytest.mark.unit
def test_choosing_an_avatar_sticks(app_clients):
    http_client, socket_client = app_clients
    game_code, uuids = _joined_game(http_client)

    taken = {player['avatar'] for player in _view(http_client, game_code, uuids[0])['player_list']}
    wanted = next(avatar for avatar in ANIMAL_AVATARS if avatar not in taken)

    socket_client.emit('choose_avatar', {
        'game_code': game_code, 'player_uuid': uuids[0], 'avatar': wanted,
    })

    assert _error(socket_client) is None
    assert _view(http_client, game_code, uuids[0])['avatar'] == wanted


@pytest.mark.unit
def test_the_choice_shows_up_in_everyone_elses_player_list(app_clients):
    """The write has to reach player_order, not just player_dict — the handler
    works on a state freshly reloaded from the database, where the two no longer
    share Player objects."""
    http_client, socket_client = app_clients
    game_code, uuids = _joined_game(http_client)

    taken = {player['avatar'] for player in _view(http_client, game_code, uuids[0])['player_list']}
    wanted = next(avatar for avatar in ANIMAL_AVATARS if avatar not in taken)

    socket_client.emit('choose_avatar', {
        'game_code': game_code, 'player_uuid': uuids[0], 'avatar': wanted,
    })

    bobs_view = _view(http_client, game_code, uuids[1])
    ann = next(p for p in bobs_view['player_list'] if p['uuid'] == uuids[0])
    assert ann['avatar'] == wanted


@pytest.mark.unit
def test_cannot_take_an_avatar_another_player_holds(app_clients):
    http_client, socket_client = app_clients
    game_code, uuids = _joined_game(http_client)

    bobs_avatar = _view(http_client, game_code, uuids[1])['avatar']
    anns_avatar = _view(http_client, game_code, uuids[0])['avatar']

    socket_client.emit('choose_avatar', {
        'game_code': game_code, 'player_uuid': uuids[0], 'avatar': bobs_avatar,
    })

    assert _error(socket_client)['message'] == 'That avatar is not available'
    assert _view(http_client, game_code, uuids[0])['avatar'] == anns_avatar


@pytest.mark.unit
def test_rejects_an_avatar_that_is_not_on_offer(app_clients):
    http_client, socket_client = app_clients
    game_code, uuids = _joined_game(http_client)
    before = _view(http_client, game_code, uuids[0])['avatar']

    socket_client.emit('choose_avatar', {
        'game_code': game_code, 'player_uuid': uuids[0], 'avatar': '<img onerror=alert(1)>',
    })

    assert _error(socket_client)['message'] == 'That avatar is not available'
    assert _view(http_client, game_code, uuids[0])['avatar'] == before


@pytest.mark.unit
def test_avatars_are_locked_once_the_game_starts(app_clients):
    http_client, socket_client = app_clients
    game_code, uuids = _joined_game(http_client, names=('Ann', 'Bob', 'Cal', 'Dee', 'Eve'))

    socket_client.emit('join', {'game_code': game_code, 'player_uuid': uuids[0]})
    socket_client.emit('start_game', {'game_code': game_code, 'player_uuid': uuids[0]})
    socket_client.get_received()

    taken = {p['avatar'] for p in _view(http_client, game_code, uuids[0])['player_list']}
    free = next(avatar for avatar in ANIMAL_AVATARS if avatar not in taken)
    before = _view(http_client, game_code, uuids[0])['avatar']

    socket_client.emit('choose_avatar', {
        'game_code': game_code, 'player_uuid': uuids[0], 'avatar': free,
    })

    assert _error(socket_client)['message'] == 'Avatars can only be changed in the lobby'
    assert _view(http_client, game_code, uuids[0])['avatar'] == before
