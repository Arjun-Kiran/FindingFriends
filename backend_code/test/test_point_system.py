from uuid import uuid4
import pytest
from faker import Faker
from Game.Components.GameState import GameState
from Game.Components.Player import Player
from Game.Components.Card import Card, Rank, Suit
from Game.Systems.GameStateSystem import add_player, set_winning_player_of_round
from Game.Systems.PointSystem import point_card_pile, calculate_rounds_points, score_round, advance_level, rank_from_value, max_alpha_team_size



@pytest.mark.unit
def test_point_card_pile():
    list_1 = [
        Card(suit=Suit.BIG, rank=Rank.JOKER),
        Card(suit=Suit.DIAMOND, rank=Rank.NINE),
        Card(suit=Suit.DIAMOND, rank=Rank.KING),
        Card(suit=Suit.DIAMOND, rank=Rank.FIVE)
    ]

    list_2 = [
        Card(suit=Suit.SMALL, rank=Rank.JOKER),
        Card(suit=Suit.HEART, rank=Rank.NINE),
        Card(suit=Suit.HEART, rank=Rank.EIGHT),
        Card(suit=Suit.HEART, rank=Rank.FIVE)
    ]

    list_3 = [
        Card(suit=Suit.SPADE, rank=Rank.KING),
        Card(suit=Suit.SPADE, rank=Rank.NINE),
        Card(suit=Suit.SPADE, rank=Rank.EIGHT),
        Card(suit=Suit.SPADE, rank=Rank.TEN)
    ]


    list_4 = [
        Card(suit=Suit.CLUB, rank=Rank.ACE),
        Card(suit=Suit.CLUB, rank=Rank.QUEEN),
        Card(suit=Suit.CLUB, rank=Rank.JACK),
        Card(suit=Suit.CLUB, rank=Rank.NINE)
    ]

    assert point_card_pile(list_1) == 15
    assert point_card_pile(list_2) == 5
    assert point_card_pile(list_3) == 20
    assert point_card_pile(list_4) == 0  


@pytest.mark.unit
def test_calculate_rounds_points():
    # Setup
    f = Faker()
    player_1 = Player(name=f.first_name(), uuid=uuid4())
    player_2 = Player(name=f.first_name(), uuid=uuid4())
    player_3 = Player(name=f.first_name(), uuid=uuid4())
    player_4 = Player(name=f.first_name(), uuid=uuid4())
    gs = GameState()
    add_player(gs, player_1)
    add_player(gs, player_2)
    add_player(gs, player_3)
    add_player(gs, player_4)

    # Player 1 won the round
    set_winning_player_of_round(gs, player_1.uuid)
    gs.cards_in_active_pile = [
        Card(suit=Suit.BIG, rank=Rank.JOKER),
        Card(suit=Suit.DIAMOND, rank=Rank.NINE),
        Card(suit=Suit.DIAMOND, rank=Rank.KING),
        Card(suit=Suit.DIAMOND, rank=Rank.FIVE)
    ]
    calculate_rounds_points(gs)
    assert gs.players_round_score[player_1.uuid] == 15

    # Player 1 won the round again. 
    # Points should add up from the previous one.
    set_winning_player_of_round(gs, player_1.uuid)
    gs.cards_in_active_pile = [
        Card(suit=Suit.SMALL, rank=Rank.JOKER),
        Card(suit=Suit.HEART, rank=Rank.NINE),
        Card(suit=Suit.HEART, rank=Rank.EIGHT),
        Card(suit=Suit.HEART, rank=Rank.FIVE)
    ]
    calculate_rounds_points(gs)
    assert gs.players_round_score[player_1.uuid] == 20
    assert gs.players_round_score[player_2.uuid] == 0
    assert gs.players_round_score[player_3.uuid] == 0
    assert gs.players_round_score[player_4.uuid] == 0

    # Player 2 won the round. 
    # Player 1 should have same point and player 2 should get more points
    set_winning_player_of_round(gs, player_2.uuid)
    gs.cards_in_active_pile = [
        Card(suit=Suit.SPADE, rank=Rank.KING),
        Card(suit=Suit.SPADE, rank=Rank.NINE),
        Card(suit=Suit.SPADE, rank=Rank.EIGHT),
        Card(suit=Suit.SPADE, rank=Rank.TEN)
    ]
    calculate_rounds_points(gs)
    assert gs.players_round_score[player_1.uuid] == 20
    assert gs.players_round_score[player_2.uuid] == 20
    assert gs.players_round_score[player_3.uuid] == 0
    assert gs.players_round_score[player_4.uuid] == 0

    # Player 3 won the round but got no points this round
    set_winning_player_of_round(gs, player_3.uuid)
    gs.cards_in_active_pile = [
        Card(suit=Suit.CLUB, rank=Rank.QUEEN),
        Card(suit=Suit.CLUB, rank=Rank.NINE),
        Card(suit=Suit.CLUB, rank=Rank.EIGHT),
        Card(suit=Suit.CLUB, rank=Rank.TWO)
    ]
    calculate_rounds_points(gs)
    assert gs.players_round_score[player_1.uuid] == 20
    assert gs.players_round_score[player_2.uuid] == 20
    assert gs.players_round_score[player_3.uuid] == 0
    assert gs.players_round_score[player_4.uuid] == 0


# --- Level promotion tests ---

class TestScoreRound:
    """Spot checks at 2 packs. The band edges live in test_level_promotion.py,
    which walks the spec's table in full."""

    def test_a_shutout_is_three_levels(self):
        assert score_round(2, 0) == ('trump_maker', 3)

    def test_a_scrap_of_a_score_is_two(self):
        assert score_round(2, 20) == ('trump_maker', 2)

    def test_a_fifth_of_the_points_is_one(self):
        assert score_round(2, 50) == ('trump_maker', 1)

    def test_two_fifths_exactly_moves_nobody(self):
        assert score_round(2, 80) == ('none', 0)

    def test_past_two_fifths_the_attackers_take_it(self):
        assert score_round(2, 90) == ('attacker', 1)

    def test_attackers_plus_2(self):
        assert score_round(2, 130) == ('attacker', 2)

    def test_attackers_plus_3(self):
        assert score_round(2, 200) == ('attacker', 3)

    def test_the_alpha_team_size_does_not_enter_into_it(self):
        """The undersized-team multiplier went with the old ladder: the
        function takes the deck count and the attackers' points, and nothing
        else can change the answer."""
        assert score_round(2, 0) == ('trump_maker', 3)

    def test_3_packs_attackers_win(self):
        assert score_round(3, 200) == ('attacker', 2)

    def test_3_packs_trump_makers_win(self):
        assert score_round(3, 30) == ('trump_maker', 2)


class TestAdvanceLevel:
    def test_normal_advance(self):
        new_val, passed = advance_level(Rank.TWO.value, 1)
        assert new_val == Rank.THREE.value
        assert passed is False

    def test_advance_to_ace(self):
        new_val, passed = advance_level(Rank.KING.value, 1)
        assert new_val == Rank.ACE.value
        assert passed is False

    def test_advance_past_ace(self):
        new_val, passed = advance_level(Rank.ACE.value, 1)
        assert new_val == Rank.ACE.value
        assert passed is True

    def test_advance_multiple(self):
        new_val, passed = advance_level(Rank.TWO.value, 3)
        assert new_val == Rank.FIVE.value
        assert passed is False

    def test_advance_from_king_by_3(self):
        new_val, passed = advance_level(Rank.KING.value, 3)
        assert new_val == Rank.ACE.value
        assert passed is True


class TestRankFromValue:
    def test_two(self):
        assert rank_from_value(Rank.TWO.value) == Rank.TWO

    def test_ace(self):
        assert rank_from_value(Rank.ACE.value) == Rank.ACE

    def test_ten(self):
        assert rank_from_value(Rank.TEN.value) == Rank.TEN


class TestMaxAlphaTeamSize:
    def test_5_players(self):
        assert max_alpha_team_size(5) == 2

    def test_8_players(self):
        assert max_alpha_team_size(8) == 4

    def test_12_players(self):
        assert max_alpha_team_size(12) == 6
