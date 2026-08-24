"""Drives a real game to a card play and checks the trick attribution the UI reads.

The unit tests cover the helpers; this covers the wiring in the play_cards
handler, which is where the pile actually grows during a game.
"""
import pytest

from Database import database


@pytest.fixture
def clients(tmp_path, monkeypatch):
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


def _view(http, code, uuid):
    return http.get(f"/game/{code}/player/{uuid}").get_json()


def _errors(sock):
    return [m['args'][0]['message'] for m in sock.get_received() if m['name'] == 'error']


def _started_game(http, sock):
    """A game driven as far as the first trick, ready for a card to be played."""
    code = http.get("/create").get_json()['game_code']
    uuids = [
        http.get(f"/join/{code}?nick_name={name}").get_json()['new_player_uuid']
        for name in ('Ann', 'Bob', 'Cal', 'Dee', 'Eve')
    ]
    host = uuids[0]

    sock.emit('join', {'game_code': code, 'player_uuid': host})
    sock.emit('start_game', {'game_code': code, 'player_uuid': host})

    alpha = _view(http, code, host)['alpha_uuid']
    alpha_view = _view(http, code, alpha)
    sock.emit('declare_trump', {
        'game_code': code, 'player_uuid': alpha,
        'suit': 'HEART', 'rank': alpha_view['player_hand'][0]['rank'],
    })

    alpha_view = _view(http, code, alpha)
    calls = [
        {'suit': 'SPADE', 'rank': 'ACE', 'order': order + 1}
        for order in range(alpha_view['num_friends_to_call'])
    ]
    sock.emit('call_friends', {'game_code': code, 'player_uuid': alpha, 'calling_cards': calls})

    alpha_view = _view(http, code, alpha)
    kitty_size = alpha_view['kitty_size']
    discards = [
        {'suit': c['suit'], 'rank': c['rank']}
        for c in alpha_view['player_hand'][:kitty_size]
    ]
    sock.emit('kitty_exchange', {
        'game_code': code, 'player_uuid': alpha, 'discarded_cards': discards,
    })

    sock.get_received()
    return code, uuids


@pytest.mark.unit
def test_the_pile_starts_empty(clients):
    http, sock = clients
    code, uuids = _started_game(http, sock)

    view = _view(http, code, uuids[0])
    assert view['game_event_state'] == 'round-started'
    assert view['cards_in_active_pile'] == []
    assert view['active_pile_player_uuids'] == []


@pytest.mark.unit
def test_a_played_card_is_attributed_to_the_player_who_played_it(clients):
    http, sock = clients
    code, uuids = _started_game(http, sock)

    leader = _view(http, code, uuids[0])['current_player']['uuid']
    played = _view(http, code, leader)['player_hand'][0]

    sock.emit('play_cards', {
        'game_code': code, 'player_uuid': leader,
        'cards': [{'suit': played['suit'], 'rank': played['rank']}],
    })
    assert _errors(sock) == []

    view = _view(http, code, uuids[0])
    assert len(view['cards_in_active_pile']) == 1
    assert view['active_pile_player_uuids'] == [leader]


@pytest.mark.unit
def test_each_player_in_the_trick_keeps_their_own_cards(clients):
    """The order of the attribution has to track the order of the pile, or the
    avatars end up under the wrong cards."""
    http, sock = clients
    code, uuids = _started_game(http, sock)

    played_by = []
    lead_suit = None
    for _ in range(3):
        current = _view(http, code, uuids[0])['current_player']['uuid']
        hand = _view(http, code, current)['player_hand']
        # Following players must follow suit when they can, so this picks a
        # legal card rather than whatever is first in hand.
        if lead_suit is None:
            card = hand[0]
        else:
            card = next((c for c in hand if c['suit'] == lead_suit), hand[0])

        sock.emit('play_cards', {
            'game_code': code, 'player_uuid': current,
            'cards': [{'suit': card['suit'], 'rank': card['rank']}],
        })
        assert _errors(sock) == []
        played_by.append(current)
        if lead_suit is None:
            lead_suit = card['suit']

    view = _view(http, code, uuids[0])
    assert view['active_pile_player_uuids'] == played_by
    assert len(view['active_pile_player_uuids']) == len(view['cards_in_active_pile'])


@pytest.mark.unit
def test_every_player_sees_the_same_attribution(clients):
    http, sock = clients
    code, uuids = _started_game(http, sock)

    leader = _view(http, code, uuids[0])['current_player']['uuid']
    card = _view(http, code, leader)['player_hand'][0]
    sock.emit('play_cards', {
        'game_code': code, 'player_uuid': leader,
        'cards': [{'suit': card['suit'], 'rank': card['rank']}],
    })

    views = [_view(http, code, uuid)['active_pile_player_uuids'] for uuid in uuids]
    assert all(v == [leader] for v in views)
