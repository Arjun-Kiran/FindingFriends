"""HR-10: a finished trick stays face-up until its winner clears it.

Driven through the real handlers on a real started game. Time is Main.now,
swapped for a clock these tests move by hand, and the 30 seconds are run out by
calling the sweep the server otherwise runs once a second.
"""
from types import SimpleNamespace

import pytest

from Database import database
from Game.Modules.EventEnum import GameEventState
from Game.Systems.GameStateSystem import TRICK_CLEAR_SECONDS
from test.seats import Clock, TableSockets, view
from test.test_trick_attribution_flow import _legal_card, _started_game


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


def _sweep(table):
    import Main

    Main.sweep_game(table.code)


def _play_one_card(table):
    """Whoever is on turn plays a legal single card. Returns their uuid."""
    current = _view(table, table.uuids[0])['current_player']['uuid']
    card = _legal_card(_view(table, current))
    _as(table, current, 'play_cards',
        cards=[{'suit': card['suit'], 'rank': card['rank']}])
    return current


def _finish_a_trick(table):
    """Every seat plays one card. Returns the winner's uuid."""
    for _ in range(len(table.uuids)):
        _play_one_card(table)
    return _view(table, table.uuids[0])['winning_player_of_round']['uuid']


def _someone_else(table, uuid):
    return next(other for other in table.uuids if other != uuid)


def _hands_left(table) -> bool:
    """Has anyone still got cards? Read per player, because only your own hand
    is ever in your own view."""
    return any(_view(table, uuid)['player_hand'] for uuid in table.uuids)


# --- the cards stay put ---

@pytest.mark.unit
def test_the_cards_stay_on_the_table_after_the_trick_is_won(table):
    _finish_a_trick(table)

    seen = _view(table, table.uuids[0])
    assert len(seen['cards_in_active_pile']) == len(table.uuids)
    assert seen['trick_complete_since'] == table.clock.t


@pytest.mark.unit
def test_nothing_is_waiting_part_way_through_a_trick(table):
    _play_one_card(table)

    assert _view(table, table.uuids[0])['trick_complete_since'] == 0


@pytest.mark.unit
def test_the_table_is_told_how_long_the_winner_has(table):
    _finish_a_trick(table)

    assert _view(table, table.uuids[0])['trick_clear_seconds'] == TRICK_CLEAR_SECONDS


# --- nobody plays into a trick that is still there ---

@pytest.mark.unit
def test_nobody_is_on_turn_while_the_trick_waits(table):
    _finish_a_trick(table)

    assert not any(_view(table, uuid)['my_turn'] for uuid in table.uuids)


@pytest.mark.unit
def test_a_play_into_a_waiting_trick_is_refused(table):
    winner = _finish_a_trick(table)
    card = _legal_card(_view(table, winner))
    table.sock.get_received()

    _as(table, winner, 'play_cards',
        cards=[{'suit': card['suit'], 'rank': card['rank']}])

    assert 'The last trick is still on the table' in _errors(table)
    assert len(_view(table, table.uuids[0])['cards_in_active_pile']) == len(table.uuids)


# --- clearing it ---

@pytest.mark.unit
def test_the_winner_clears_the_trick(table):
    winner = _finish_a_trick(table)

    _as(table, winner, 'clear_trick')

    seen = _view(table, table.uuids[0])
    assert seen['cards_in_active_pile'] == []
    assert seen['trick_complete_since'] == 0


@pytest.mark.unit
def test_clearing_passes_the_lead_to_the_winner(table):
    winner = _finish_a_trick(table)

    _as(table, winner, 'clear_trick')

    assert _view(table, table.uuids[0])['current_player']['uuid'] == winner
    assert _view(table, winner)['my_turn']


@pytest.mark.unit
def test_nobody_else_may_clear_it(table):
    winner = _finish_a_trick(table)
    other = _someone_else(table, winner)
    table.sock.get_received()

    _as(table, other, 'clear_trick')

    assert 'Only the winner of the trick can clear it' in _errors(table)
    assert len(_view(table, table.uuids[0])['cards_in_active_pile']) == len(table.uuids)


@pytest.mark.unit
def test_pressing_clear_twice_is_not_an_error(table):
    winner = _finish_a_trick(table)
    _as(table, winner, 'clear_trick')
    table.sock.get_received()

    # A second press racing the sweep, or a double click. There is nothing left
    # to clear and nothing worth telling anyone about.
    _as(table, winner, 'clear_trick')

    assert _errors(table) == []


# --- the 30 seconds running out ---

@pytest.mark.unit
def test_the_trick_survives_a_sweep_before_the_time_is_up(table):
    _finish_a_trick(table)

    table.clock.advance(TRICK_CLEAR_SECONDS - 1)
    _sweep(table)

    assert len(_view(table, table.uuids[0])['cards_in_active_pile']) == len(table.uuids)


@pytest.mark.unit
def test_the_table_clears_the_trick_when_the_time_is_up(table):
    winner = _finish_a_trick(table)

    table.clock.advance(TRICK_CLEAR_SECONDS)
    _sweep(table)

    seen = _view(table, table.uuids[0])
    assert seen['cards_in_active_pile'] == []
    assert seen['trick_complete_since'] == 0
    # Expiring it puts the table exactly where clearing it would have.
    assert seen['current_player']['uuid'] == winner


@pytest.mark.unit
def test_a_winner_who_never_comes_back_does_not_stall_the_game(table):
    """The point of the countdown: a dropped winner costs 30 seconds, not the
    rest of the round."""
    winner = _finish_a_trick(table)
    table.sock.socket_of(winner).disconnect()

    table.clock.advance(TRICK_CLEAR_SECONDS)
    _sweep(table)

    assert _view(table, table.uuids[0])['cards_in_active_pile'] == []


# --- the last trick of the round ---

@pytest.mark.unit
def test_the_last_trick_waits_like_any_other(table):
    """One rule for every trick. The round does not end until the trick that
    ended it has been cleared — and it is the trick that decides the doubled
    kitty, so it is the one most worth a moment to look at."""
    winner = ''
    while _view(table, table.uuids[0])['game_event_state'] == GameEventState.ROUND_STARTED.value:
        winner = _finish_a_trick(table)
        if not _hands_left(table):
            break
        _as(table, winner, 'clear_trick')

    seen = _view(table, table.uuids[0])
    assert seen['game_event_state'] == GameEventState.ROUND_STARTED.value
    assert seen['trick_complete_since'] != 0
    assert len(seen['cards_in_active_pile']) == len(table.uuids)

    _as(table, winner, 'clear_trick')

    assert _view(table, table.uuids[0])['game_event_state'] == GameEventState.ROUND_ENDED.value


@pytest.mark.unit
def test_the_last_trick_expiring_ends_the_round_too(table):
    while True:
        winner = _finish_a_trick(table)
        if not _hands_left(table):
            break
        _as(table, winner, 'clear_trick')

    table.clock.advance(TRICK_CLEAR_SECONDS)
    _sweep(table)

    assert _view(table, table.uuids[0])['game_event_state'] == GameEventState.ROUND_ENDED.value
