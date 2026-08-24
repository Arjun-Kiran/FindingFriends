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
