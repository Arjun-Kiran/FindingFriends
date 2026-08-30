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


def _legal_card(view):
    """A card this player is actually allowed to play right now.

    Asks the server rather than working it out here. Picking by printed suit
    looks equivalent and is not: with hearts trump a plain spade does not
    follow a heart lead, and with fives trump the 5 of spades is a trump and
    not a spade at all. These tests are about attribution, so the card they
    play only has to be legal — never a re-implementation of the rules.
    """
    playable = [card for card, ok
                in zip(view['player_hand'], view['playable_hand_cards']) if ok]
    assert playable, (
        f"no playable card: state={view['game_event_state']}, my_turn={view['my_turn']}"
    )
    return playable[0]


def _started_game(http, sock):
    """A game driven as far as the first trick, ready for a card to be played."""
    code = http.get("/create").get_json()['game_code']
    uuids = [
        http.get(f"/join/{code}?nick_name={name}").get_json()['new_player_uuid']
        for name in ('Ann', 'Bob', 'Cal', 'Dee', 'Eve')
    ]
    host = uuids[0]

    sock.emit('join', {'game_code': code, 'player_uuid': host})
    # These tests are about attribution, not about who may declare what: free trump
    # choice lets the fixture name a known suit instead of hunting the alpha's
    # hand for a legal one. Lobby only, so it goes before the game starts.
    sock.emit('update_settings', {
        'game_code': code, 'player_uuid': host,
        'settings': {'free_trump_choice': True},
    })
    sock.emit('start_game', {'game_code': code, 'player_uuid': host})

    alpha = _view(http, code, host)['alpha_uuid']
    alpha_view = _view(http, code, alpha)
    # Not a joker, which has no rank to declare, and not an ace, which the
    # friend call below asks for as A of spades — a called card may not be a
    # trump (Main.handle_call_friends), so an ace trump rank sticks the game in
    # friend calling. Nothing else about the rank matters here.
    trump_rank = next(card['rank'] for card in alpha_view['player_hand']
                      if card['rank'] not in ('JOKER', 'ACE'))
    sock.emit('declare_trump', {
        'game_code': code, 'player_uuid': alpha,
        'suit': 'HEART', 'rank': trump_rank,
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
    played = _legal_card(_view(http, code, leader))

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
    for _ in range(3):
        current = _view(http, code, uuids[0])['current_player']['uuid']
        # Following players must follow suit when they can, so this picks a
        # card the server has already said is legal.
        card = _legal_card(_view(http, code, current))

        sock.emit('play_cards', {
            'game_code': code, 'player_uuid': current,
            'cards': [{'suit': card['suit'], 'rank': card['rank']}],
        })
        assert _errors(sock) == []
        played_by.append(current)

    view = _view(http, code, uuids[0])
    assert view['active_pile_player_uuids'] == played_by
    assert len(view['active_pile_player_uuids']) == len(view['cards_in_active_pile'])


@pytest.mark.unit
def test_every_player_sees_the_same_attribution(clients):
    http, sock = clients
    code, uuids = _started_game(http, sock)

    leader = _view(http, code, uuids[0])['current_player']['uuid']
    card = _legal_card(_view(http, code, leader))
    sock.emit('play_cards', {
        'game_code': code, 'player_uuid': leader,
        'cards': [{'suit': card['suit'], 'rank': card['rank']}],
    })

    views = [_view(http, code, uuid)['active_pile_player_uuids'] for uuid in uuids]
    assert all(v == [leader] for v in views)
