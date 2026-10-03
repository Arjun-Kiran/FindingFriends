"""HR-6: the attackers' captured points decide the round, against the bands.

Only their points — the alpha team's total is never consulted, because the two
always sum to the points in play. The bands are fifths of that total, a win is
worth up to three levels either way, and there is exactly one value where
nobody moves.

The tables here are the spec's own required cases, extended to the 5 and 6 deck
counts this game deals (HR-1) by the same `U = 20 x packs` rule. If the formula
and these tables ever disagree, the tables win.
"""
import pytest

from Database import database
from Game.Components.GameState import GameState, GameSettings
from Game.Components.Card import Card
from Game.Modules.CardConstants import Rank, Suit
from Game.Modules.EventEnum import GameEventState
from Game.Systems.GameStateSystem import add_player, generate_player, set_player_as_alpha
from Game.Systems.PointSystem import ScoringError, promotion_for_round, score_round, scoring_bands


ALPHA = 'trump_maker'
ATTACK = 'attacker'


# --- the band edges, every one of them ---

@pytest.mark.unit
@pytest.mark.parametrize('packs, points, winner, levels', [
    # 2 packs (T=200, U=40, N=80)
    (2, 0, ALPHA, 3), (2, 5, ALPHA, 2), (2, 35, ALPHA, 2),
    (2, 40, ALPHA, 1), (2, 75, ALPHA, 1),
    (2, 80, 'none', 0),
    (2, 85, ATTACK, 1), (2, 120, ATTACK, 1),
    (2, 125, ATTACK, 2), (2, 160, ATTACK, 2),
    (2, 165, ATTACK, 3), (2, 200, ATTACK, 3),
    # 3 packs (T=300, U=60, N=120) — 5 and 6 players
    (3, 0, ALPHA, 3), (3, 5, ALPHA, 2), (3, 55, ALPHA, 2),
    (3, 60, ALPHA, 1), (3, 115, ALPHA, 1),
    (3, 120, 'none', 0),
    (3, 125, ATTACK, 1), (3, 180, ATTACK, 1),
    (3, 185, ATTACK, 2), (3, 240, ATTACK, 2),
    (3, 245, ATTACK, 3), (3, 300, ATTACK, 3),
    # 4 packs (T=400, U=80, N=160) — 7 and 8 players
    (4, 0, ALPHA, 3), (4, 5, ALPHA, 2), (4, 75, ALPHA, 2),
    (4, 80, ALPHA, 1), (4, 155, ALPHA, 1),
    (4, 160, 'none', 0),
    (4, 165, ATTACK, 1), (4, 240, ATTACK, 1),
    (4, 245, ATTACK, 2), (4, 320, ATTACK, 2),
    (4, 325, ATTACK, 3), (4, 400, ATTACK, 3),
    # 5 packs (T=500, U=100, N=200) — 9 and 10 players, HR-4
    (5, 0, ALPHA, 3), (5, 5, ALPHA, 2), (5, 95, ALPHA, 2),
    (5, 100, ALPHA, 1), (5, 195, ALPHA, 1),
    (5, 200, 'none', 0),
    (5, 205, ATTACK, 1), (5, 300, ATTACK, 1),
    (5, 305, ATTACK, 2), (5, 400, ATTACK, 2),
    (5, 405, ATTACK, 3), (5, 500, ATTACK, 3),
    # 6 packs (T=600, U=120, N=240) — 11 and 12 players, HR-4
    (6, 0, ALPHA, 3), (6, 5, ALPHA, 2), (6, 115, ALPHA, 2),
    (6, 120, ALPHA, 1), (6, 235, ALPHA, 1),
    (6, 240, 'none', 0),
    (6, 245, ATTACK, 1), (6, 360, ATTACK, 1),
    (6, 365, ATTACK, 2), (6, 480, ATTACK, 2),
    (6, 485, ATTACK, 3), (6, 600, ATTACK, 3),
])
def test_every_band_edge(packs, points, winner, levels):
    assert score_round(packs, points) == (winner, levels)


@pytest.mark.unit
@pytest.mark.parametrize('packs', [2, 3, 4, 5, 6])
def test_every_scorable_total_agrees_with_the_bands(packs):
    """Exhaustive: every multiple of five from a shutout to the whole table.

    Checked against bands built independently of the function under test, so a
    formula that drifts cannot take the test with it."""
    unit, neutral = 20 * packs, 40 * packs
    for points in range(0, 100 * packs + 1, 5):
        if points == 0:
            expected = (ALPHA, 3)
        elif points < unit:
            expected = (ALPHA, 2)
        elif points < neutral:
            expected = (ALPHA, 1)
        elif points == neutral:
            expected = ('none', 0)
        else:
            over = points - neutral
            expected = (ATTACK, min(3, (over + unit - 1) // unit))
        assert score_round(packs, points) == expected, f'{packs} packs, {points} pts'


@pytest.mark.unit
def test_a_level_is_gained_for_going_past_a_fifth_not_for_landing_on_it():
    """The edge the spec calls out as easy to get wrong, from both sides.

    Alpha bands close at the bottom, attacker bands close at the top."""
    assert score_round(3, 60) == (ALPHA, 1)       # exactly U, not +2
    assert score_round(3, 55) == (ALPHA, 2)
    assert score_round(3, 180) == (ATTACK, 1)     # exactly N+U, not +2
    assert score_round(3, 185) == (ATTACK, 2)


@pytest.mark.unit
def test_nobody_moving_is_one_value_not_a_band():
    assert score_round(3, 120) == ('none', 0)
    assert score_round(3, 115) == (ALPHA, 1)
    assert score_round(3, 125) == (ATTACK, 1)


@pytest.mark.unit
def test_three_levels_is_a_shutout_and_only_a_shutout():
    assert score_round(3, 0) == (ALPHA, 3)
    assert score_round(3, 5) == (ALPHA, 2)


@pytest.mark.unit
def test_the_doubled_kitty_may_carry_the_attackers_past_the_table():
    """The top band is open: the kitty counts double for the attackers when
    they take the last trick, which can put them over the raw card total."""
    assert score_round(3, 350) == (ATTACK, 3)
    assert score_round(2, 250) == (ATTACK, 3)


# --- input that is not a round ---

@pytest.mark.unit
@pytest.mark.parametrize('packs, points', [
    (2, -5),        # negative
    (2, 42),        # not a multiple of five
    (1, 50),        # too few decks to have bands
    (7, 50),        # more decks than the game deals
])
def test_what_cannot_be_scored_is_refused(packs, points):
    with pytest.raises(ScoringError):
        score_round(packs, points)


@pytest.mark.unit
def test_a_bool_is_not_a_score():
    """True == 1 in Python, which would otherwise sail through as a score and
    come back as an alpha +2."""
    with pytest.raises(ScoringError):
        score_round(2, True)


# --- the lobby's opt-out ---

@pytest.mark.unit
@pytest.mark.parametrize('alpha_points, attacker_points, expected', [
    (300, 0, (ALPHA, 1)),
    (155, 145, (ALPHA, 1)),
    (145, 155, (ATTACK, 1)),
    (0, 300, (ATTACK, 1)),
])
def test_unscaled_gives_one_level_to_whoever_has_more(alpha_points, attacker_points, expected):
    assert promotion_for_round(3, alpha_points, attacker_points, scaled=False) == expected


@pytest.mark.unit
@pytest.mark.parametrize('points', [0, 150])
def test_unscaled_ties_move_nobody(points):
    assert promotion_for_round(3, points, points, scaled=False) == ('none', 0)


@pytest.mark.unit
def test_the_bands_are_what_a_table_gets_without_asking():
    """Default on. 30 attacker points out of 300 is a rout, not a one-level
    win, and that is the difference the setting makes."""
    assert promotion_for_round(3, 270, 30, scaled=True) == (ALPHA, 2)
    assert promotion_for_round(3, 270, 30) == (ALPHA, 2)
    assert promotion_for_round(3, 270, 30, scaled=False) == (ALPHA, 1)


@pytest.mark.unit
def test_a_new_table_starts_on_the_bands():
    assert GameSettings().scaled_level_promotion is True


# --- at the end of a real round ---

@pytest.fixture
def main(tmp_path, monkeypatch):
    import Main

    db_file = str(tmp_path / "test_game_state.db")
    monkeypatch.setattr(database, "get_database", lambda: db_file)
    database.build_game_state_table()
    return Main


def _finished_round(alpha_points, attacker_points, scaled=True, players=6, friends=1):
    """A round ready to be scored: the first player is alpha, the next `friends`
    have revealed themselves, the alpha holds the alpha team's points and the
    first attacker holds the attackers'. The alpha took the last trick, so the
    kitty counts for nobody."""
    gs = GameState()
    for i in range(players):
        add_player(gs, generate_player(name=f'p{i}'))
    uuids = [p.uuid for p in gs.player_order]
    set_player_as_alpha(gs, uuids[0])
    gs.current_friends_of_alpha = uuids[1:1 + friends]
    gs.players_round_score[uuids[0]] = alpha_points
    gs.players_round_score[uuids[1 + friends]] = attacker_points
    gs.last_trick_winner = uuids[0]
    gs.settings = GameSettings(scaled_level_promotion=scaled)
    return gs, uuids[:1 + friends], uuids[1 + friends:]


@pytest.mark.unit
def test_a_shutout_carries_the_alpha_team_three_levels(main):
    gs, alpha_team, attackers = _finished_round(alpha_points=300, attacker_points=0)

    main.handle_end_of_round(gs)

    assert gs.round_winner_side == 'trump_maker'
    assert gs.round_promotion_levels == 3
    assert sorted(gs.round_promoted_players) == sorted(alpha_team)
    assert all(gs.player_levels[u] == Rank.FIVE.value for u in alpha_team)
    assert all(gs.player_levels[u] == Rank.TWO.value for u in attackers)


@pytest.mark.unit
def test_the_attackers_running_away_with_it_climb_three(main):
    gs, alpha_team, attackers = _finished_round(alpha_points=0, attacker_points=300)

    main.handle_end_of_round(gs)

    assert gs.round_winner_side == 'attacker'
    assert gs.round_promotion_levels == 3
    assert sorted(gs.round_promoted_players) == sorted(attackers)
    assert all(gs.player_levels[u] == Rank.FIVE.value for u in attackers)
    assert all(gs.player_levels[u] == Rank.TWO.value for u in alpha_team)


@pytest.mark.unit
def test_the_neutral_total_moves_nobody(main):
    """Two fifths of 300 exactly. Under the old rule 150 apiece was a tie and
    also moved nobody, but by a different route — this one is about the
    attackers' total alone."""
    gs, alpha_team, attackers = _finished_round(alpha_points=180, attacker_points=120)

    main.handle_end_of_round(gs)

    assert gs.round_winner_side == 'none'
    assert gs.round_promotion_levels == 0
    assert gs.round_promoted_players == []
    assert all(gs.player_levels[u] == Rank.TWO.value for u in alpha_team + attackers)


@pytest.mark.unit
def test_the_doubled_kitty_can_win_it_for_the_attackers(main):
    """Behind on the table at 120, the attackers take the last trick with a
    15-point kitty under it: 120 + 30 = 150 clears the neutral point."""
    gs, _, attackers = _finished_round(alpha_points=180, attacker_points=120)
    gs.last_trick_winner = attackers[0]
    gs.card_out_of_play = [Card(suit=Suit.CLUB, rank=Rank.TEN), Card(suit=Suit.CLUB, rank=Rank.FIVE)]

    main.handle_end_of_round(gs)

    assert gs.round_attacker_points == 150
    assert gs.round_winner_side == 'attacker'
    assert gs.round_promotion_levels == 1


@pytest.mark.unit
def test_a_table_that_turned_the_bands_off_gets_one_level(main):
    gs, alpha_team, _ = _finished_round(alpha_points=300, attacker_points=0, scaled=False)

    main.handle_end_of_round(gs)

    assert gs.round_promotion_levels == 1
    assert all(gs.player_levels[u] == Rank.THREE.value for u in alpha_team)


@pytest.mark.unit
def test_the_alpha_team_being_short_handed_changes_nothing(main):
    """Six players, so the maximum alpha team is three. A team of two used to
    have its promotion doubled; the bands have no such multiplier."""
    short, full = (_finished_round(alpha_points=300, attacker_points=0, friends=n)
                   for n in (1, 2))
    main.handle_end_of_round(short[0])
    main.handle_end_of_round(full[0])

    assert short[0].round_promotion_levels == full[0].round_promotion_levels == 3


@pytest.mark.unit
def test_winning_on_ace_still_wins_the_game(main):
    gs, alpha_team, _ = _finished_round(alpha_points=300, attacker_points=0)
    gs.player_levels[alpha_team[0]] = Rank.ACE.value

    main.handle_end_of_round(gs)

    assert gs.game_event_state == GameEventState.GAME_ENDED
    assert gs.game_winner == alpha_team[0]


@pytest.mark.unit
def test_reaching_ace_is_not_yet_a_win(main):
    """Three levels from Queen overshoots Ace, which stops there rather than
    winning — the win is for going past it."""
    gs, alpha_team, _ = _finished_round(alpha_points=300, attacker_points=0)
    gs.player_levels[alpha_team[0]] = Rank.JACK.value

    main.handle_end_of_round(gs)

    assert gs.game_event_state == GameEventState.ROUND_ENDED
    assert gs.player_levels[alpha_team[0]] == Rank.ACE.value


# --- the ladder as the round summary shows it ---

@pytest.mark.unit
@pytest.mark.parametrize('packs', [2, 3, 4, 5, 6])
def test_the_shown_bands_are_the_bands_that_are_played(packs):
    """Every total inside a row scores what the row says.

    The point of building the table out of score_round: a breakdown on screen
    that disagrees with the engine would be worse than showing none."""
    for low, high, side, levels in scoring_bands(packs):
        top = high if high is not None else low + 500
        for points in range(low, top + 1, 5):
            assert score_round(packs, points) == (side, levels), (
                f'{packs} packs, {points} pts falls in {low}-{high} but scores otherwise')


@pytest.mark.unit
@pytest.mark.parametrize('packs', [2, 3, 4, 5, 6])
def test_the_bands_cover_every_total_without_a_gap(packs):
    rows = scoring_bands(packs)
    assert rows[0][0] == 0
    assert rows[-1][1] is None, 'the last band is open — the kitty can double past the total'
    for (_, high, _, _), (low, _, _, _) in zip(rows, rows[1:]):
        assert low == high + 5, f'gap or overlap between {high} and {low}'


@pytest.mark.unit
def test_the_ladder_has_a_row_for_each_outcome():
    """Seven rows: three to the alpha team, one where nobody moves, three to
    the attackers."""
    rows = scoring_bands(3)
    assert [(side, levels) for _, _, side, levels in rows] == [
        ('trump_maker', 3), ('trump_maker', 2), ('trump_maker', 1),
        ('none', 0),
        ('attacker', 1), ('attacker', 2), ('attacker', 3),
    ]


@pytest.mark.unit
def test_nobody_moving_is_a_row_of_one_value():
    neutral = [row for row in scoring_bands(3) if row[2] == 'none']
    assert neutral == [(120, 120, 'none', 0)]
