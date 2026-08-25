"""The events the in-game notification feed is built from.

These run a real game through the socket handlers, because what matters is that
the events are recorded at the right moments during play — not that the
recording helper works.
"""
import pytest

from Database import database
from Game.Modules.EventEnum import Event


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


def _events(http, code, uuid, of_type=None):
    events = _view(http, code, uuid)['events']
    if of_type is None:
        return events
    return [e for e in events if e['event'] == of_type.value]


def _play_one_trick(http, sock, code, uuids, turns=5):
    """Play `turns` legal single-card plays, returning who played what."""
    played = []
    lead_suit = None
    for _ in range(turns):
        current = _view(http, code, uuids[0])['current_player']['uuid']
        hand = _view(http, code, current)['player_hand']
        if lead_suit is None:
            card = hand[0]
        else:
            card = next((c for c in hand if c['suit'] == lead_suit), hand[0])
        sock.emit('play_cards', {
            'game_code': code, 'player_uuid': current,
            'cards': [{'suit': card['suit'], 'rank': card['rank']}],
        })
        played.append((current, card))
        lead_suit = lead_suit or card['suit']
    return played


@pytest.fixture
def started(clients):
    import sys
    sys.path.insert(0, 'test')
    from test_trick_attribution_flow import _started_game
    http, sock = clients
    code, uuids = _started_game(http, sock)
    return http, sock, code, uuids


@pytest.mark.unit
def test_every_event_carries_what_the_feed_needs(started):
    http, sock, code, uuids = started
    _play_one_trick(http, sock, code, uuids, turns=1)

    for event in _events(http, code, uuids[0]):
        assert event['message']
        assert event['uuid']
        # Epoch seconds as a string — the frontend parses it as such.
        assert float(event['time_stamp']) > 0


@pytest.mark.unit
def test_a_play_is_announced_with_the_player_and_the_cards(started):
    http, sock, code, uuids = started
    (player_uuid, card), = _play_one_trick(http, sock, code, uuids, turns=1)

    name = next(p['name'] for p in _view(http, code, uuids[0])['player_list']
                if p['uuid'] == player_uuid)
    plays = _events(http, code, uuids[0], Event.HAND_PLAY)

    assert len(plays) == 1
    assert plays[0]['message'].startswith(f'{name} played ')


@pytest.mark.unit
def test_one_play_event_per_play(started):
    http, sock, code, uuids = started
    _play_one_trick(http, sock, code, uuids, turns=3)

    assert len(_events(http, code, uuids[0], Event.HAND_PLAY)) == 3


@pytest.mark.unit
def test_taking_the_trick_is_announced_once(started):
    http, sock, code, uuids = started
    _play_one_trick(http, sock, code, uuids, turns=5)

    won = _events(http, code, uuids[0], Event.TRICK_WON)
    assert len(won) == 1
    assert won[0]['message'].endswith('won the trick')


@pytest.mark.unit
def test_the_trick_is_credited_to_the_player_who_took_it(started):
    http, sock, code, uuids = started
    _play_one_trick(http, sock, code, uuids, turns=5)

    view = _view(http, code, uuids[0])
    # The winner leads the next trick.
    winner = view['current_player']['name']
    won = _events(http, code, uuids[0], Event.TRICK_WON)

    assert won[0]['message'] == f'{winner} won the trick'


@pytest.mark.unit
def test_no_trick_event_until_the_trick_is_complete(started):
    http, sock, code, uuids = started
    _play_one_trick(http, sock, code, uuids, turns=4)

    assert _events(http, code, uuids[0], Event.TRICK_WON) == []


@pytest.mark.unit
def test_everyone_at_the_table_sees_the_same_events(started):
    http, sock, code, uuids = started
    _play_one_trick(http, sock, code, uuids, turns=2)

    feeds = [[e['uuid'] for e in _view(http, code, uuid)['events']] for uuid in uuids]
    assert all(feed == feeds[0] for feed in feeds)


@pytest.mark.unit
def test_joining_and_leaving_are_still_announced(started):
    http, sock, code, uuids = started

    joined = _events(http, code, uuids[0], Event.PLAYER_JOINED)
    assert len(joined) == 5
    assert joined[0]['message'].endswith('joined the game')


# --- the player an event is about ---
# The notification feed puts that player's avatar in front of the message, so
# the uuid has to be there and has to be the right one.

@pytest.mark.unit
def test_a_play_names_the_player_who_made_it(started):
    http, sock, code, uuids = started
    (player_uuid, _), = _play_one_trick(http, sock, code, uuids, turns=1)

    play, = _events(http, code, uuids[0], Event.HAND_PLAY)
    assert play['player_uuid'] == player_uuid


@pytest.mark.unit
def test_the_trick_event_names_the_winner(started):
    http, sock, code, uuids = started
    _play_one_trick(http, sock, code, uuids, turns=5)

    won, = _events(http, code, uuids[0], Event.TRICK_WON)
    winner = _view(http, code, uuids[0])['current_player']
    assert won['player_uuid'] == winner['uuid']


@pytest.mark.unit
def test_joining_names_the_player_who_joined(started):
    http, sock, code, uuids = started

    joined = _events(http, code, uuids[0], Event.PLAYER_JOINED)
    assert [e['player_uuid'] for e in joined] == uuids


@pytest.mark.unit
def test_every_named_player_can_be_found_at_the_table(started):
    """A uuid the frontend cannot match renders without an avatar, so a wrong
    one fails quietly. This is what catches it."""
    http, sock, code, uuids = started
    _play_one_trick(http, sock, code, uuids, turns=5)

    at_the_table = {p['uuid'] for p in _view(http, code, uuids[0])['player_list']}
    for event in _events(http, code, uuids[0]):
        if event['player_uuid']:
            assert event['player_uuid'] in at_the_table


@pytest.mark.unit
def test_events_saved_before_they_named_players_still_load():
    """Old rows in the database have events with no player_uuid at all."""
    from Game.Modules.EventEnum import EventItem

    event = EventItem(event=Event.PLAYER_JOINED, message='Ann joined the game',
                      time_stamp='1756000000.0', uuid='7d3f1e0a-1c2b-4d5e-8f9a-0b1c2d3e4f50')

    assert event.player_uuid == ''


# --- the alpha's set-up phases ---
# Each phase both announces who everyone is waiting on, and announces the
# decision once it is made.

def _lobby(http):
    code = http.get("/create").get_json()['game_code']
    uuids = [
        http.get(f"/join/{code}?nick_name={name}").get_json()['new_player_uuid']
        for name in ('Ann', 'Bob', 'Cal', 'Dee', 'Eve')
    ]
    return code, uuids


def _messages(http, code, uuid, of_type):
    return [e['message'] for e in _events(http, code, uuid, of_type)]


@pytest.fixture
def at_trump(clients):
    """A game started and waiting on the alpha to choose trump."""
    http, sock = clients
    code, uuids = _lobby(http)
    sock.emit('join', {'game_code': code, 'player_uuid': uuids[0]})
    sock.emit('start_game', {'game_code': code, 'player_uuid': uuids[0]})
    alpha = _view(http, code, uuids[0])['alpha_uuid']
    return http, sock, code, uuids, alpha


def _declare_trump(http, sock, code, alpha):
    hand = _view(http, code, alpha)['player_hand']
    sock.emit('declare_trump', {'game_code': code, 'player_uuid': alpha,
                                'suit': 'HEART', 'rank': hand[0]['rank']})


def _call_friends(http, sock, code, alpha):
    count = _view(http, code, alpha)['num_friends_to_call']
    sock.emit('call_friends', {
        'game_code': code, 'player_uuid': alpha,
        'calling_cards': [{'suit': 'SPADE', 'rank': 'ACE', 'order': i + 1} for i in range(count)],
    })


def _exchange_kitty(http, sock, code, alpha):
    view = _view(http, code, alpha)
    discards = [{'suit': c['suit'], 'rank': c['rank']}
                for c in view['player_hand'][:view['kitty_size']]]
    sock.emit('kitty_exchange', {'game_code': code, 'player_uuid': alpha,
                                 'discarded_cards': discards})
    return len(discards)


@pytest.mark.unit
def test_starting_the_game_says_who_everyone_is_waiting_on(at_trump):
    http, sock, code, uuids, alpha = at_trump

    waiting = _events(http, code, uuids[0], Event.WAITING_ON_ALPHA_CHOOSE_TRUMP)
    assert len(waiting) == 1
    assert waiting[0]['player_uuid'] == alpha
    assert 'trump' in waiting[0]['message']


@pytest.mark.unit
def test_declaring_trump_is_announced_with_the_suit(at_trump):
    http, sock, code, uuids, alpha = at_trump
    _declare_trump(http, sock, code, alpha)

    declared = _events(http, code, uuids[0], Event.TRUMP_DECLARED)
    assert len(declared) == 1
    assert declared[0]['player_uuid'] == alpha
    assert '♥️' in declared[0]['message']


@pytest.mark.unit
def test_declaring_trump_moves_the_wait_on_to_friend_cards(at_trump):
    http, sock, code, uuids, alpha = at_trump
    _declare_trump(http, sock, code, alpha)

    waiting = _events(http, code, uuids[0], Event.WAITING_ON_ALPHA_FRIEND_CARD_CHOICE)
    assert len(waiting) == 1
    assert waiting[0]['player_uuid'] == alpha


@pytest.mark.unit
def test_the_called_cards_are_named(at_trump):
    http, sock, code, uuids, alpha = at_trump
    _declare_trump(http, sock, code, alpha)
    _call_friends(http, sock, code, alpha)

    called = _events(http, code, uuids[0], Event.FRIENDS_CALLED)
    assert len(called) == 1
    assert 'A♠️' in called[0]['message']
    assert '1st' in called[0]['message']


@pytest.mark.unit
def test_calling_friends_moves_the_wait_on_to_the_kitty(at_trump):
    http, sock, code, uuids, alpha = at_trump
    _declare_trump(http, sock, code, alpha)
    _call_friends(http, sock, code, alpha)

    assert len(_events(http, code, uuids[0], Event.WAITING_ON_ALPHA_KITTY_SORT)) == 1


@pytest.mark.unit
def test_the_kitty_discard_is_announced_as_a_count(at_trump):
    http, sock, code, uuids, alpha = at_trump
    _declare_trump(http, sock, code, alpha)
    _call_friends(http, sock, code, alpha)
    buried = _exchange_kitty(http, sock, code, alpha)

    discarded = _events(http, code, uuids[0], Event.KITTY_DISCARDED)
    assert len(discarded) == 1
    assert discarded[0]['message'].endswith(f'put {buried} cards in the kitty')


@pytest.mark.unit
def test_the_kitty_discard_never_names_the_cards(at_trump):
    """What the alpha buried is private. Naming it in a notification every
    player can read would hand the defenders the round."""
    http, sock, code, uuids, alpha = at_trump
    _declare_trump(http, sock, code, alpha)
    _call_friends(http, sock, code, alpha)

    hand_before = _view(http, code, alpha)['player_hand']
    kitty_size = _view(http, code, alpha)['kitty_size']
    buried = hand_before[:kitty_size]
    _exchange_kitty(http, sock, code, alpha)

    message = _messages(http, code, uuids[0], Event.KITTY_DISCARDED)[0]
    for card in buried:
        assert card['rank'] not in message
    assert '♠️' not in message and '♥️' not in message
    assert '♦️' not in message and '♣️' not in message


@pytest.mark.unit
def test_the_whole_set_up_reads_in_order(at_trump):
    http, sock, code, uuids, alpha = at_trump
    _declare_trump(http, sock, code, alpha)
    _call_friends(http, sock, code, alpha)
    _exchange_kitty(http, sock, code, alpha)

    interesting = [
        e['event'] for e in _events(http, code, uuids[0])
        if e['event'] != Event.PLAYER_JOINED.value
    ]
    assert interesting == [
        Event.WAITING_ON_ALPHA_CHOOSE_TRUMP.value,
        Event.TRUMP_DECLARED.value,
        Event.WAITING_ON_ALPHA_FRIEND_CARD_CHOICE.value,
        Event.FRIENDS_CALLED.value,
        Event.WAITING_ON_ALPHA_KITTY_SORT.value,
        Event.KITTY_DISCARDED.value,
    ]


@pytest.mark.unit
def test_a_rejected_decision_announces_nothing(at_trump):
    """The announcement has to sit after the validation, not before it."""
    http, sock, code, uuids, alpha = at_trump
    not_the_alpha = next(uuid for uuid in uuids if uuid != alpha)

    sock.emit('declare_trump', {'game_code': code, 'player_uuid': not_the_alpha,
                                'suit': 'HEART', 'rank': 'ACE'})

    assert _events(http, code, uuids[0], Event.TRUMP_DECLARED) == []


# --- leaving ---
# A player who leaves is not coming back; one who dropped might be. The table
# is told which happened.

@pytest.mark.unit
def test_leaving_mid_game_is_announced_as_leaving(at_trump):
    http, sock, code, uuids, alpha = at_trump
    leaver = next(uuid for uuid in uuids if uuid != alpha)
    sock.emit('join', {'game_code': code, 'player_uuid': leaver})

    sock.emit('leave_game', {'game_code': code, 'player_uuid': leaver})

    left = _events(http, code, uuids[0], Event.PLAYER_LEFT)
    assert len(left) == 1
    assert left[0]['player_uuid'] == leaver
    assert left[0]['message'].endswith('left the game')


@pytest.mark.unit
def test_leaving_mid_game_is_not_also_announced_as_a_disconnect(at_trump):
    """The socket drops right after the player leaves. Without forgetting the
    sid first, the table would be told twice, and the second one would be
    wrong."""
    http, sock, code, uuids, alpha = at_trump
    leaver = next(uuid for uuid in uuids if uuid != alpha)
    sock.emit('join', {'game_code': code, 'player_uuid': leaver})

    sock.emit('leave_game', {'game_code': code, 'player_uuid': leaver})
    sock.disconnect()

    assert _events(http, code, uuids[0], Event.PLAYER_DISCONNECTED) == []


@pytest.mark.unit
def test_a_seat_is_held_when_someone_leaves_mid_game(at_trump):
    """Dropping the player would break a round whose hands are already dealt."""
    http, sock, code, uuids, alpha = at_trump
    leaver = next(uuid for uuid in uuids if uuid != alpha)
    sock.emit('join', {'game_code': code, 'player_uuid': leaver})

    sock.emit('leave_game', {'game_code': code, 'player_uuid': leaver})

    view = _view(http, code, uuids[0])
    assert leaver in [p['uuid'] for p in view['player_list']]
    assert view['number_of_players'] == 5


@pytest.mark.unit
def test_leaving_the_lobby_gives_the_seat_up(clients):
    """Before the deal there is nothing to break, so the player really goes."""
    http, sock = clients
    code, uuids = _lobby(http)
    sock.emit('join', {'game_code': code, 'player_uuid': uuids[1]})

    sock.emit('leave_game', {'game_code': code, 'player_uuid': uuids[1]})

    view = _view(http, code, uuids[0])
    assert uuids[1] not in [p['uuid'] for p in view['player_list']]
    assert view['number_of_players'] == 4
    assert _events(http, code, uuids[0], Event.PLAYER_LEFT)[0]['player_uuid'] == uuids[1]


@pytest.mark.unit
def test_everyone_left_at_the_table_sees_the_departure(at_trump):
    http, sock, code, uuids, alpha = at_trump
    leaver = next(uuid for uuid in uuids if uuid != alpha)
    sock.emit('join', {'game_code': code, 'player_uuid': leaver})

    sock.emit('leave_game', {'game_code': code, 'player_uuid': leaver})

    for uuid in uuids:
        assert len(_events(http, code, uuid, Event.PLAYER_LEFT)) == 1


@pytest.mark.unit
def test_leaving_a_game_that_is_gone_does_not_blow_up(clients):
    http, sock = clients

    sock.emit('leave_game', {'game_code': 'no-such-game', 'player_uuid': 'nobody'})

    assert any(m['name'] == 'session_invalid' for m in sock.get_received())
