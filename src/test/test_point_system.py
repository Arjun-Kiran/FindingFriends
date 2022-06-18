from uuid import uuid4
import pytest
from faker import Faker
from Game.Components.GameState import GameState
from Game.Components.Player import Player
from Game.Components.Card import Card, Rank, Suit
from Game.Systems.GameStateSystem import add_player, set_winning_player_of_round
from Game.Systems.PointSystem import point_card_pile, calculate_rounds_points



@pytest.mark.unit
def test_point_card_pile():
    list_1 = [
        Card(Suit.BIG, Rank.JOKER),
        Card(Suit.DIAMOND, Rank.NINE),
        Card(Suit.DIAMOND, Rank.KING),
        Card(Suit.DIAMOND, Rank.FIVE)
    ]

    list_2 = [
        Card(Suit.SMALL, Rank.JOKER),
        Card(Suit.HEART, Rank.NINE),
        Card(Suit.HEART, Rank.EIGHT),
        Card(Suit.HEART, Rank.FIVE)
    ]

    list_3 = [
        Card(Suit.SPADE, Rank.KING),
        Card(Suit.SPADE, Rank.NINE),
        Card(Suit.SPADE, Rank.EIGHT),
        Card(Suit.SPADE, Rank.TEN)
    ]


    list_4 = [
        Card(Suit.CLUB, Rank.ACE),
        Card(Suit.CLUB, Rank.QUEEN),
        Card(Suit.CLUB, Rank.JACK),
        Card(Suit.CLUB, Rank.NINE)
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
        Card(Suit.BIG, Rank.JOKER),
        Card(Suit.DIAMOND, Rank.NINE),
        Card(Suit.DIAMOND, Rank.KING),
        Card(Suit.DIAMOND, Rank.FIVE)
    ]
    calculate_rounds_points(gs)
    assert gs.players_round_score[player_1.uuid] == 15

    # Player 1 won the round again. 
    # Points should add up from the previous one.
    set_winning_player_of_round(gs, player_1.uuid)
    gs.cards_in_active_pile = [
        Card(Suit.SMALL, Rank.JOKER),
        Card(Suit.HEART, Rank.NINE),
        Card(Suit.HEART, Rank.EIGHT),
        Card(Suit.HEART, Rank.FIVE)
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
        Card(Suit.SPADE, Rank.KING),
        Card(Suit.SPADE, Rank.NINE),
        Card(Suit.SPADE, Rank.EIGHT),
        Card(Suit.SPADE, Rank.TEN)
    ]
    calculate_rounds_points(gs)
    assert gs.players_round_score[player_1.uuid] == 20
    assert gs.players_round_score[player_2.uuid] == 20
    assert gs.players_round_score[player_3.uuid] == 0
    assert gs.players_round_score[player_4.uuid] == 0

    # Player 3 won the round but got no points this round
    set_winning_player_of_round(gs, player_3.uuid)
    gs.cards_in_active_pile = [
        Card(Suit.CLUB, Rank.QUEEN),
        Card(Suit.CLUB, Rank.NINE),
        Card(Suit.CLUB, Rank.EIGHT),
        Card(Suit.CLUB, Rank.TWO)
    ]
    calculate_rounds_points(gs)
    assert gs.players_round_score[player_1.uuid] == 20
    assert gs.players_round_score[player_2.uuid] == 20
    assert gs.players_round_score[player_3.uuid] == 0
    assert gs.players_round_score[player_4.uuid] == 0
