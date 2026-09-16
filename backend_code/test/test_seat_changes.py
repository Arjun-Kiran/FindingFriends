"""HR-8: seats changing hands, the host handing over, and a table running short.

Driven through the real handlers on a real started game. Time is Main.now,
swapped for a clock these tests move by hand, and the countdowns are moved on
by calling the sweep the server otherwise runs once a second.
"""
from types import SimpleNamespace

import pytest

from Database import database
from Game.Components.GameState import GameState
from Game.Modules.CardConstants import Rank
from Game.Modules.EventEnum import GameEventState
from Game.Systems.GameStateSystem import add_player, generate_player
from Game.Systems.SeatSystem import add_watcher, approve_request, ask_to_join
from test.seats import Clock, TableSockets, token_for, view
from test.test_trick_attribution_flow import _legal_card, _started_game

# _started_game seats these in this order. Ann hosts and is the first alpha —
# that helper turns the random draw off so she reliably is.
ANN, BOB, CAL, DEE, EVE = range(5)


@pytest.fixture
def table(tmp_path, monkeypatch):
    import Main

    db_file = str(tmp_path / "test_game_state.db")
    monkeypatch.setattr(database, "get_database", lambda: db_file)
    database.build_game_state_table()
    Main.app.config['TESTING'] = True
    clock = Clock()
    monkeypatch.setattr(Main, 'now', clock)

    with Main.app.test_client() as http:
        sock = TableSockets()
        code, uuids = _started_game(http, sock)
        yield SimpleNamespace(http=http, sock=sock, code=code, uuids=uuids, clock=clock)
        sock.disconnect()


def _view(table, uuid):
    return view(table.http, table.code, uuid)


def _as(table, uuid, event, **payload):
    table.sock.emit(event, {'game_code': table.code, 'player_uuid': uuid, **payload})


def _errors(table):
    return [m['args'][0]['message'] for m in table.sock.get_received() if m['name'] == 'error']


def _drop(table, uuid):
    table.sock.socket_of(uuid).disconnect()


def _sweep(table):
    import Main

    Main.sweep_game(table.code)


def _events(table, kind, seen_by):
    return [event for event in _view(table, seen_by)['events'] if event['event'] == kind]


def _watch(table, name='Wes'):
    return table.sock.watch(table.http, table.code, name)


def _take_over(table, seat_uuid, name='Wes', host=None):
    """A watcher volunteers for a free seat and the host approves them."""
    watcher = _watch(table, name)
    _as(table, watcher, 'volunteer_for_seat', seat_uuid=seat_uuid)
    _as(table, host or table.uuids[ANN], 'approve_seat_request', watcher_uuid=watcher)
    return watcher


def _end_round(table):
    import Main

    gs = Main.get_redis_cache(table.code)
    gs.game_event_state = GameEventState.ROUND_ENDED
    Main.update_redis_cache(gs)


def _join_next_round(table, name='Wes', level=Rank.TWO.value):
    watcher = _watch(table, name)
    _as(table, watcher, 'ask_to_join')
    _as(table, table.uuids[ANN], 'approve_seat_request', watcher_uuid=watcher, level=level)
    return watcher


# --- volunteering, and taking a seat over ---

@pytest.mark.unit
def test_nobody_can_volunteer_for_a_seat_whose_player_is_here(table):
    wes = _watch(table)
    table.sock.get_received()

    _as(table, wes, 'volunteer_for_seat', seat_uuid=table.uuids[BOB])

    assert _errors(table) == ['That seat is not free.']


@pytest.mark.unit
def test_a_watcher_can_volunteer_the_moment_a_player_drops(table):
    bob = table.uuids[BOB]
    wes = _watch(table)
    _drop(table, bob)

    _as(table, wes, 'volunteer_for_seat', seat_uuid=bob)

    requests = _view(table, table.uuids[ANN])['seat_requests']
    assert [(r['watcher_uuid'], r['seat_uuid']) for r in requests] == [(wes, bob)]


@pytest.mark.unit
def test_approval_seats_the_volunteer_at_once_hand_and_all(table):
    """Within the minute Bob has to come back: the host's approval stands."""
    bob = table.uuids[BOB]
    hand = _view(table, bob)['player_hand']
    _drop(table, bob)
    table.sock.get_received()

    wes = _take_over(table, bob)

    assert _errors(table) == []
    seated = _view(table, wes)
    assert seated['is_watcher'] is False
    assert seated['uuid'] == bob
    assert seated['name'] == 'Wes'
    assert seated['player_hand'] == hand
    messages = [event['message'] for event in _view(table, table.uuids[ANN])['events']]
    assert "Wes took over Bob's seat" in messages


@pytest.mark.unit
def test_the_player_who_was_replaced_comes_back_as_a_watcher(table):
    bob = table.uuids[BOB]
    bobs_token = token_for(bob)
    _drop(table, bob)
    _take_over(table, bob)

    response = table.http.get(f"/game/{table.code}/player", headers={'X-Player-Token': bobs_token})
    assert response.get_json()['is_watcher'] is True
    assert response.get_json()['name'] == 'Bob'
    assert response.get_json()['player_hand'] == []

    received = table.sock.reconnect(bob, table.code).get_received()
    assert [m for m in received if m['name'] == 'session_invalid'] == []
    stats = [m['args'][0] for m in received if m['name'] == 'game_stats']
    assert stats[-1]['is_watcher'] is True


@pytest.mark.unit
def test_coming_back_before_any_approval_keeps_the_seat(table):
    bob = table.uuids[BOB]
    wes = _watch(table)
    _drop(table, bob)
    _as(table, wes, 'volunteer_for_seat', seat_uuid=bob)
    table.sock.reconnect(bob, table.code)
    table.sock.get_received()

    _as(table, table.uuids[ANN], 'approve_seat_request', watcher_uuid=wes)

    assert _errors(table) == ['That request is no longer open.']
    assert _view(table, bob)['is_watcher'] is False
    assert _view(table, wes)['is_watcher'] is True


@pytest.mark.unit
def test_only_the_host_approves(table):
    bob = table.uuids[BOB]
    wes = _watch(table)
    _drop(table, bob)
    _as(table, wes, 'volunteer_for_seat', seat_uuid=bob)
    table.sock.get_received()

    _as(table, table.uuids[CAL], 'approve_seat_request', watcher_uuid=wes)

    assert _errors(table) == ['Only the host can approve a request to play']
    assert _view(table, wes)['is_watcher'] is True


@pytest.mark.unit
def test_one_seat_one_approval_and_the_other_volunteers_go_back_to_watching(table):
    bob = table.uuids[BOB]
    wes, wil = _watch(table, 'Wes'), _watch(table, 'Wil')
    _drop(table, bob)
    _as(table, wes, 'volunteer_for_seat', seat_uuid=bob)
    _as(table, wil, 'volunteer_for_seat', seat_uuid=bob)

    _as(table, table.uuids[ANN], 'approve_seat_request', watcher_uuid=wil)

    assert _view(table, wil)['uuid'] == bob
    assert _view(table, wes)['is_watcher'] is True
    assert _view(table, table.uuids[ANN])['seat_requests'] == []


@pytest.mark.unit
def test_the_new_player_can_play_the_turn_that_was_waiting(table):
    leader = _view(table, table.uuids[ANN])['current_player']['uuid']
    card = _legal_card(_view(table, leader))
    _as(table, leader, 'play_cards', cards=[{'suit': card['suit'], 'rank': card['rank']}])
    waiting_on = _view(table, table.uuids[ANN])['current_player']['uuid']
    assert waiting_on != table.uuids[ANN]

    _drop(table, waiting_on)
    wes = _take_over(table, waiting_on)
    table.sock.adopt(waiting_on, wes)
    table.sock.get_received()
    card = _legal_card(_view(table, waiting_on))
    _as(table, waiting_on, 'play_cards', cards=[{'suit': card['suit'], 'rank': card['rank']}])

    assert _errors(table) == []
    assert _view(table, table.uuids[ANN])['active_pile_player_uuids'] == [leader, waiting_on]


@pytest.mark.unit
def test_whoever_takes_over_the_alpha_is_the_alpha(table):
    import Main

    cal = table.uuids[CAL]
    gs = Main.get_redis_cache(table.code)
    gs.current_alpha_player.player_uuid = cal
    Main.update_redis_cache(gs)
    _drop(table, cal)

    wes = _take_over(table, cal)

    assert _view(table, wes)['is_alpha'] is True


# --- when a seat is open ---

@pytest.mark.unit
def test_a_dropped_seat_opens_after_60_seconds_and_not_before(table):
    ann, bob = table.uuids[ANN], table.uuids[BOB]
    _drop(table, bob)
    table.clock.advance(59)
    _sweep(table)

    assert _view(table, ann)['open_seats'] == []
    assert _view(table, ann)['round_held_up'] is False

    table.clock.advance(1)
    _sweep(table)
    _sweep(table)

    assert _view(table, ann)['open_seats'] == [bob]
    assert _view(table, ann)['round_held_up'] is True
    assert len(_events(table, 'seat-open', ann)) == 1


@pytest.mark.unit
def test_a_seat_opens_at_once_when_its_player_leaves(table):
    ann, bob = table.uuids[ANN], table.uuids[BOB]

    _as(table, bob, 'leave_game')

    assert _view(table, ann)['open_seats'] == [bob]
    assert _view(table, ann)['round_held_up'] is True


@pytest.mark.unit
def test_the_countdown_beside_a_name_can_be_drawn(table):
    ann, bob = table.uuids[ANN], table.uuids[BOB]

    _drop(table, bob)

    seen = _view(table, ann)
    assert seen['seat_vacancies'][bob]['since'] == table.clock.t
    assert seen['server_time'] == table.clock.t
    assert seen['seat_grace_seconds'] == 60


# --- ending a round as a draw ---

@pytest.mark.unit
def test_the_host_can_end_a_held_up_round_as_a_draw(table):
    ann = table.uuids[ANN]
    levels = _view(table, ann)['player_levels']
    _as(table, table.uuids[BOB], 'leave_game')
    table.sock.get_received()

    _as(table, ann, 'end_round_as_draw')

    assert _errors(table) == []
    seen = _view(table, ann)
    assert seen['game_event_state'] == 'round-ended'
    assert seen['round_winner_side'] == 'none'
    assert seen['round_promotion_levels'] == 0
    assert seen['player_levels'] == levels


@pytest.mark.unit
def test_a_round_nobody_is_missing_from_cannot_be_ended(table):
    ann = table.uuids[ANN]
    table.sock.get_received()

    _as(table, ann, 'end_round_as_draw')

    assert _errors(table) == ['The round can only be ended as a draw while a seat is empty.']
    assert _view(table, ann)['game_event_state'] == 'round-started'


@pytest.mark.unit
def test_a_player_who_lost_connection_gets_their_minute_first(table):
    ann = table.uuids[ANN]
    _drop(table, table.uuids[BOB])
    table.clock.advance(59)
    table.sock.get_received()

    _as(table, ann, 'end_round_as_draw')

    assert _errors(table) == ['The round can only be ended as a draw while a seat is empty.']
    assert _view(table, ann)['game_event_state'] == 'round-started'


@pytest.mark.unit
def test_only_the_host_ends_a_round(table):
    _as(table, table.uuids[BOB], 'leave_game')
    table.sock.get_received()

    _as(table, table.uuids[CAL], 'end_round_as_draw')

    assert _errors(table) == ['Only the host can end the round']


@pytest.mark.unit
def test_five_minutes_away_loses_the_seat_for_good(table):
    ann, bob = table.uuids[ANN], table.uuids[BOB]
    bobs_token = token_for(bob)
    _drop(table, bob)

    table.clock.advance(300)
    _sweep(table)

    response = table.http.get(f"/game/{table.code}/player", headers={'X-Player-Token': bobs_token})
    assert response.get_json()['is_watcher'] is True
    # Still in the round: its hand and its turn are part of it.
    assert bob in [player['uuid'] for player in _view(table, ann)['player_list']]
    assert len(_events(table, 'seat-lost', ann)) == 1


# --- the host ---

@pytest.mark.unit
def test_a_host_who_leaves_hands_over_at_once(table):
    bob = table.uuids[BOB]

    _as(table, table.uuids[ANN], 'leave_game')

    assert _view(table, bob)['host_uuid'] == bob
    assert _view(table, bob)['hosting'] is True


@pytest.mark.unit
def test_a_host_who_drops_hands_over_after_60_seconds(table):
    ann, bob = table.uuids[ANN], table.uuids[BOB]
    _drop(table, ann)

    table.clock.advance(59)
    _sweep(table)
    assert _view(table, bob)['host_uuid'] == ann

    table.clock.advance(1)
    _sweep(table)
    assert _view(table, bob)['host_uuid'] == bob


@pytest.mark.unit
def test_a_host_who_comes_back_is_an_ordinary_player(table):
    ann = table.uuids[ANN]
    _drop(table, ann)
    table.clock.advance(60)
    _sweep(table)

    table.sock.reconnect(ann, table.code)

    assert _view(table, ann)['hosting'] is False


@pytest.mark.unit
def test_taking_a_seat_over_counts_as_joining_when_it_was_taken(table):
    """Wes sits in Bob's seat, but joined after Cal — so Cal hosts next."""
    ann, bob = table.uuids[ANN], table.uuids[BOB]
    _drop(table, bob)
    wes = _take_over(table, bob)
    table.sock.adopt(bob, wes)

    _drop(table, ann)
    table.clock.advance(60)
    _sweep(table)

    assert _view(table, bob)['host_uuid'] == table.uuids[CAL]


@pytest.mark.unit
def test_the_new_host_can_hand_out_seats(table):
    ann, bob = table.uuids[ANN], table.uuids[BOB]
    wes = _watch(table)
    _as(table, ann, 'leave_game')
    _as(table, wes, 'volunteer_for_seat', seat_uuid=ann)
    table.sock.get_received()

    _as(table, bob, 'approve_seat_request', watcher_uuid=wes)

    assert _errors(table) == []
    assert _view(table, wes)['uuid'] == ann


# --- a table running short ---

@pytest.mark.unit
def test_the_table_is_warned_at_once_when_fewer_than_5_are_connected(table):
    ann = table.uuids[ANN]
    _drop(table, table.uuids[BOB])

    _sweep(table)

    warnings = _events(table, 'table-short', ann)
    assert len(warnings) == 1
    assert 'closes in 10 minutes' in warnings[0]['message']
    assert _view(table, ann)['room_closes_at'] == table.clock.t + 600


@pytest.mark.unit
def test_and_warned_again_at_5_minutes(table):
    ann = table.uuids[ANN]
    _drop(table, table.uuids[BOB])
    _sweep(table)

    table.clock.advance(300)
    _sweep(table)

    warnings = _events(table, 'table-short', ann)
    assert len(warnings) == 2
    assert 'closes in 5 minutes' in warnings[1]['message']


@pytest.mark.unit
def test_the_room_closes_at_10_minutes(table):
    import Main

    _drop(table, table.uuids[BOB])
    _sweep(table)
    host = table.sock.socket_of(table.uuids[ANN])
    host.get_received()

    table.clock.advance(600)
    _sweep(table)

    with pytest.raises(Main.GameNotFoundError):
        Main.get_redis_cache(table.code)
    closed = [m['args'][0] for m in host.get_received() if m['name'] == 'session_invalid']
    assert closed and closed[0]['reason'] == 'room_closed'


@pytest.mark.unit
def test_getting_back_to_5_stops_the_countdown(table):
    ann, bob = table.uuids[ANN], table.uuids[BOB]
    _drop(table, bob)
    _sweep(table)

    table.sock.reconnect(bob, table.code)
    _sweep(table)

    assert _view(table, ann)['room_closes_at'] == 0


@pytest.mark.unit
def test_a_seat_nobody_holds_a_socket_for_starts_its_countdown(table):
    """What a server restart leaves behind: seats with no socket, and no
    disconnect ever heard for them."""
    import Main

    eve = table.uuids[EVE]
    for sid, (_, uuid) in list(Main.SID_TO_PLAYER.items()):
        if uuid == eve:
            del Main.SID_TO_PLAYER[sid]

    _sweep(table)

    assert eve in _view(table, table.uuids[ANN])['seat_vacancies']


# --- joining at the next round ---

@pytest.mark.unit
def test_an_approved_watcher_joins_when_the_next_round_starts(table, monkeypatch):
    import Game.Systems.SeatSystem as SeatSystem

    monkeypatch.setattr(SeatSystem, 'random_place', lambda size: 0)
    wes = _join_next_round(table, level=Rank.FIVE.value)
    assert _view(table, wes)['is_watcher'] is True
    assert len(_view(table, table.uuids[ANN])['player_list']) == 5

    _end_round(table)
    table.sock.get_received()
    _as(table, table.uuids[ANN], 'next_round')

    assert _errors(table) == []
    seated = _view(table, wes)
    assert seated['is_watcher'] is False
    assert seated['uuid'] == wes
    assert seated['my_level'] == Rank.FIVE.value
    assert [player['uuid'] for player in seated['player_list']][0] == wes
    assert len(seated['player_list']) == 6
    # HR-1: six players are dealt 26 cards each.
    assert len(seated['player_hand']) == 26


@pytest.mark.unit
def test_a_seat_nobody_took_leaves_at_the_next_round(table):
    dee = table.uuids[DEE]
    _join_next_round(table)
    _as(table, dee, 'leave_game')
    _end_round(table)

    _as(table, table.uuids[ANN], 'next_round')

    at_table = [player['uuid'] for player in _view(table, table.uuids[ANN])['player_list']]
    assert dee not in at_table
    assert len(at_table) == 5


@pytest.mark.unit
def test_the_next_alpha_skips_a_seat_that_is_leaving(table):
    """Ann was alpha, so Bob would be next — but Bob is leaving."""
    _join_next_round(table)
    _as(table, table.uuids[BOB], 'leave_game')
    _end_round(table)

    _as(table, table.uuids[ANN], 'next_round')

    assert _view(table, table.uuids[ANN])['alpha_uuid'] == table.uuids[CAL]


@pytest.mark.unit
def test_the_next_round_deals_after_the_host_and_alpha_leaves_and_the_round_is_drawn(table):
    """Ann hosts, is alpha, and holds the turn — so removing her seat at the
    next round clears every pointer the round keeps. That is the path that
    used to fail, because clearing them had never run outside the lobby."""
    ann, bob = table.uuids[ANN], table.uuids[BOB]
    _join_next_round(table)
    _as(table, ann, 'leave_game')
    _as(table, bob, 'end_round_as_draw')
    table.sock.get_received()

    _as(table, bob, 'next_round')

    assert _errors(table) == []
    seen = _view(table, bob)
    assert seen['game_event_state'] != 'round-ended'
    assert ann not in [player['uuid'] for player in seen['player_list']]
    assert len(seen['player_list']) == 5
    assert seen['alpha_uuid'] == bob
    assert seen['host_uuid'] == bob


@pytest.mark.unit
def test_a_round_is_never_dealt_to_fewer_than_5(table):
    ann = table.uuids[ANN]
    _as(table, table.uuids[DEE], 'leave_game')
    _end_round(table)
    table.sock.get_received()

    _as(table, ann, 'next_round')

    errors = _errors(table)
    assert errors and 'At least 5' in errors[0]
    assert _view(table, ann)['game_event_state'] == 'round-ended'
    assert len(_view(table, ann)['player_list']) == 5


@pytest.mark.unit
def test_a_player_removed_at_the_next_round_can_come_back_to_watch(table):
    dee = table.uuids[DEE]
    dees_token = token_for(dee)
    _join_next_round(table)
    _drop(table, dee)
    table.clock.advance(60)
    _end_round(table)

    _as(table, table.uuids[ANN], 'next_round')

    response = table.http.get(f"/game/{table.code}/player", headers={'X-Player-Token': dees_token})
    assert response.get_json()['is_watcher'] is True


@pytest.mark.unit
def test_the_table_never_grows_past_12():
    gs = GameState()
    for index in range(12):
        add_player(gs, generate_player(name=f'p{index}'))
    gs.game_event_state = GameEventState.ROUND_ENDED
    watcher, _ = add_watcher(gs, 'Wes', 0.0)
    ask_to_join(gs, watcher.uuid)

    problem, _, _ = approve_request(gs, watcher.uuid, 0.0, Rank.TWO.value)

    assert 'cannot grow past 12' in problem


@pytest.mark.unit
def test_joining_waits_for_the_game_to_start():
    gs = GameState()
    add_player(gs, generate_player(name='Ann'))
    gs.game_event_state = GameEventState.WAITING_FOR_PLAYERS_TO_JOIN
    watcher, _ = add_watcher(gs, 'Wes', 0.0)

    assert ask_to_join(gs, watcher.uuid)
