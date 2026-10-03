"""HR-11: the next alpha comes from the side that won the round.

Going round the table from the last alpha, the first player who was on the
winning side; after a draw, simply the next seat. The walk ends on the last
alpha, so an alpha who won alone keeps the seat.

The table here is the example the rule was written from: five seats, P4 the
alpha and P2 the friend they found.
"""
import pytest

from Game.Components.GameState import GameSettings, GameState, Vacancy
from Game.Modules.EventEnum import GameEventState
from Game.Systems.GameStateSystem import add_player, generate_player, set_player_as_alpha
from Game.Systems.SeatSystem import next_alpha, prepare_next_round
from Game.Views.PlayerView import player_view_state


NOW = 1_000_000.0
P1, P2, P3, P4, P5 = range(5)


def _ended_round(winner, alpha=P4, friends=(P2,), **settings):
    gs = GameState()
    for i in range(5):
        add_player(gs, generate_player(name=f'P{i + 1}'))
    seats = [str(player.uuid) for player in gs.player_order]
    set_player_as_alpha(gs, seats[alpha])
    gs.current_friends_of_alpha = [seats[friend] for friend in friends]
    gs.round_winner_side = winner
    gs.game_event_state = GameEventState.ROUND_ENDED
    gs.settings = GameSettings(**settings)
    return gs, seats


def _leaving(gs, seat_uuid):
    gs.vacancies[seat_uuid] = Vacancy(since=NOW, left=True)


# --- the example ---

@pytest.mark.unit
@pytest.mark.parametrize('winner, expected', [
    ('attacker', P5),      # P5 attacked, and is next round the table anyway
    ('trump_maker', P2),   # P5 and P1 attacked; P2 was the friend
    ('none', P5),          # a draw is simply the next seat
])
def test_the_example_the_rule_was_written_from(winner, expected):
    gs, seats = _ended_round(winner)

    assert next_alpha(gs, NOW) == seats[expected]


@pytest.mark.unit
def test_the_walk_wraps_round_the_table():
    """P2 alpha with P1: past P3, P4 and P5, round to P1."""
    gs, seats = _ended_round('trump_maker', alpha=P2, friends=(P1,))

    assert next_alpha(gs, NOW) == seats[P1]


@pytest.mark.unit
def test_an_alpha_who_won_alone_stays_alpha():
    gs, seats = _ended_round('trump_maker', friends=())

    assert next_alpha(gs, NOW) == seats[P4]


# --- seats leaving at the next round ---

@pytest.mark.unit
def test_a_winner_whose_seat_is_leaving_is_passed_over():
    gs, seats = _ended_round('attacker')
    _leaving(gs, seats[P5])

    assert next_alpha(gs, NOW) == seats[P1]


@pytest.mark.unit
def test_with_no_winner_left_the_next_seat_that_stays_is_alpha():
    """The alpha won alone and is leaving: nobody from the winning side is
    left, so it falls to the next seat as it would after a draw."""
    gs, seats = _ended_round('trump_maker', friends=())
    _leaving(gs, seats[P4])

    assert next_alpha(gs, NOW) == seats[P5]


@pytest.mark.unit
def test_starting_the_next_round_uses_the_same_choice():
    gs, seats = _ended_round('trump_maker')

    alpha, problem = prepare_next_round(gs, NOW)

    assert problem == ''
    assert alpha == seats[P2]


# --- the setting ---

@pytest.mark.unit
def test_it_is_on_for_a_table_nobody_configured():
    assert GameSettings().next_alpha_from_winners is True


@pytest.mark.unit
@pytest.mark.parametrize('winner', ['attacker', 'trump_maker', 'none'])
def test_turned_off_the_alpha_passes_seat_by_seat(winner):
    gs, seats = _ended_round(winner, next_alpha_from_winners=False)

    assert next_alpha(gs, NOW) == seats[P5]


# --- the round summary ---

@pytest.mark.unit
def test_the_round_summary_names_the_next_alpha():
    gs, seats = _ended_round('trump_maker')

    assert player_view_state(gs, seats[P1], now=NOW).next_alpha_uuid == seats[P2]


@pytest.mark.unit
def test_nobody_is_named_while_a_round_is_played():
    gs, seats = _ended_round('trump_maker')
    gs.game_event_state = GameEventState.ROUND_STARTED

    assert player_view_state(gs, seats[P1], now=NOW).next_alpha_uuid == ''
