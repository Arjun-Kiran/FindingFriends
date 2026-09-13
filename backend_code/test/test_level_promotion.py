"""HR-6: the side with more points wins the round, and a win is one level.

No bands, no margin, no undersized-team multiplier; an exact tie moves nobody.
GameSettings.scaled_level_promotion brings the traditional scoring back whole.
"""
import pytest

from Database import database
from Game.Components.GameState import GameState, GameSettings
from Game.Components.Card import Card
from Game.Modules.CardConstants import Rank, Suit
from Game.Modules.EventEnum import GameEventState
from Game.Systems.GameStateSystem import add_player, generate_player, set_player_as_alpha
from Game.Systems.PointSystem import promotion_for_round, calculate_level_promotion


# --- the promotion itself ---

@pytest.mark.unit
@pytest.mark.parametrize('alpha_points, defender_points, expected', [
    (300, 0, ('trump_maker', 1)),
    (155, 145, ('trump_maker', 1)),   # traditionally a draw
    (145, 155, ('defender', 1)),      # traditionally a draw
    (0, 300, ('defender', 1)),
])
def test_more_points_wins_by_one_level(alpha_points, defender_points, expected):
    assert promotion_for_round(3, alpha_points, defender_points, 3, 3) == expected


@pytest.mark.unit
@pytest.mark.parametrize('points', [0, 150])
def test_a_tie_moves_nobody(points):
    assert promotion_for_round(3, points, points, 3, 3) == ('none', 0)


@pytest.mark.unit
def test_a_short_handed_alpha_team_is_not_multiplied():
    """Traditionally 3 × 6 = 18 levels: an alpha alone at twelve, shutting out."""
    assert calculate_level_promotion(6, 0, 1, 6) == ('trump_maker', 18)

    assert promotion_for_round(6, 600, 0, 1, 6) == ('trump_maker', 1)


@pytest.mark.unit
def test_the_bands_no_longer_decide_anything():
    """30 defender points is a traditional T+2, however many the alpha team has.
    Under HR-6 it only matters how it compares."""
    assert promotion_for_round(3, 20, 30, 3, 3) == ('defender', 1)


@pytest.mark.unit
@pytest.mark.parametrize('num_packs, alpha_points, defender_points, actual, maximum', [
    (3, 300, 0, 3, 3),
    (3, 270, 30, 2, 3),
    (3, 155, 145, 3, 3),   # a traditional draw stays a draw
    (4, 0, 400, 4, 4),
    (6, 600, 0, 1, 6),
])
def test_the_scaled_setting_brings_back_the_traditional_scoring(
        num_packs, alpha_points, defender_points, actual, maximum):
    assert (promotion_for_round(num_packs, alpha_points, defender_points, actual, maximum, scaled=True)
            == calculate_level_promotion(num_packs, defender_points, actual, maximum))


# --- at the end of a real round ---

@pytest.fixture
def main(tmp_path, monkeypatch):
    import Main

    db_file = str(tmp_path / "test_game_state.db")
    monkeypatch.setattr(database, "get_database", lambda: db_file)
    database.build_game_state_table()
    return Main


def _finished_round(alpha_points, defender_points, scaled=False, players=6, friends=1):
    """A round ready to be scored: the first player is alpha, the next `friends`
    have revealed themselves, the alpha holds the alpha team's points and the
    first defender holds the defenders'. The alpha took the last trick, so the
    kitty counts for nobody."""
    gs = GameState()
    for i in range(players):
        add_player(gs, generate_player(name=f'p{i}'))
    uuids = [p.uuid for p in gs.player_order]
    set_player_as_alpha(gs, uuids[0])
    gs.current_friends_of_alpha = uuids[1:1 + friends]
    gs.players_round_score[uuids[0]] = alpha_points
    gs.players_round_score[uuids[1 + friends]] = defender_points
    gs.last_trick_winner = uuids[0]
    gs.settings = GameSettings(scaled_level_promotion=scaled)
    return gs, uuids[:1 + friends], uuids[1 + friends:]


@pytest.mark.unit
def test_the_alpha_team_ahead_on_points_moves_up_one(main):
    gs, alpha_team, defenders = _finished_round(alpha_points=155, defender_points=145)

    main.handle_end_of_round(gs)

    assert gs.round_winner_side == 'trump_maker'
    assert gs.round_promotion_levels == 1
    assert sorted(gs.round_promoted_players) == sorted(alpha_team)
    assert all(gs.player_levels[u] == Rank.THREE.value for u in alpha_team)
    assert all(gs.player_levels[u] == Rank.TWO.value for u in defenders)


@pytest.mark.unit
def test_the_defenders_ahead_on_points_move_up_one(main):
    gs, alpha_team, defenders = _finished_round(alpha_points=0, defender_points=300)

    main.handle_end_of_round(gs)

    assert gs.round_winner_side == 'defender'
    assert gs.round_promotion_levels == 1
    assert sorted(gs.round_promoted_players) == sorted(defenders)
    assert all(gs.player_levels[u] == Rank.THREE.value for u in defenders)
    assert all(gs.player_levels[u] == Rank.TWO.value for u in alpha_team)


@pytest.mark.unit
def test_a_tied_round_moves_nobody(main):
    gs, alpha_team, defenders = _finished_round(alpha_points=150, defender_points=150)

    main.handle_end_of_round(gs)

    assert gs.round_winner_side == 'none'
    assert gs.round_promotion_levels == 0
    assert gs.round_promoted_players == []
    assert all(gs.player_levels[u] == Rank.TWO.value for u in alpha_team + defenders)


@pytest.mark.unit
def test_the_doubled_kitty_can_win_it_for_the_defenders(main):
    """Behind 160 to 140 on the table, the defenders take the last trick with
    a 15-point kitty under it: 140 + 30 = 170 beats 160."""
    gs, _, defenders = _finished_round(alpha_points=160, defender_points=140)
    gs.last_trick_winner = defenders[0]
    gs.card_out_of_play = [Card(suit=Suit.CLUB, rank=Rank.TEN), Card(suit=Suit.CLUB, rank=Rank.FIVE)]

    main.handle_end_of_round(gs)

    assert gs.round_defender_points == 170
    assert gs.round_winner_side == 'defender'
    assert gs.round_promotion_levels == 1


@pytest.mark.unit
def test_a_table_that_chose_the_scaled_ladder_gets_it(main):
    """Six players, a team of two against a maximum of three, a shutout: 3 × 2 = 6."""
    gs, alpha_team, _ = _finished_round(alpha_points=300, defender_points=0, scaled=True)

    main.handle_end_of_round(gs)

    assert gs.round_promotion_levels == 6
    assert all(gs.player_levels[u] == Rank.EIGHT.value for u in alpha_team)


@pytest.mark.unit
def test_winning_on_ace_still_wins_the_game(main):
    gs, alpha_team, _ = _finished_round(alpha_points=300, defender_points=0)
    gs.player_levels[alpha_team[0]] = Rank.ACE.value

    main.handle_end_of_round(gs)

    assert gs.game_event_state == GameEventState.GAME_ENDED
    assert gs.game_winner == alpha_team[0]


@pytest.mark.unit
def test_reaching_ace_is_not_yet_a_win(main):
    gs, alpha_team, _ = _finished_round(alpha_points=300, defender_points=0)
    gs.player_levels[alpha_team[0]] = Rank.KING.value

    main.handle_end_of_round(gs)

    assert gs.game_event_state == GameEventState.ROUND_ENDED
    assert gs.player_levels[alpha_team[0]] == Rank.ACE.value
