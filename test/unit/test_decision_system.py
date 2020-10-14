from src.Game.Components.Card import Card
from src.Game.Components.Player import Player
from src.Game.Components.GameState import GameState
from src.Game.Modules.CardConstants import Suit, Rank
from src.Game.Systems.DecisionSystem import compare_hand_spades


def test_compare_spade_hands_1():
    """

    :return:
    """
    test_game_state = GameState()
    hand_1 = [Card(Suit.SPADE, Rank.EIGHT)]
    hand_2 = [Card(Suit.CLUB, Rank.EIGHT)]
    result = compare_hand_spades(game_state=test_game_state, hand_1=hand_1, hand_2=hand_2)
    assert result is True


def test_compare_spade_hands_2():
    """
    :return:
    """
    test_game_state = GameState()
    hand_1 = [Card(Suit.SPADE, Rank.EIGHT)]
    hand_2 = [Card(Suit.SPADE, Rank.KING)]
    result = compare_hand_spades(game_state=test_game_state, hand_1=hand_1, hand_2=hand_2)
    assert result is False


def test_compare_spade_hands_3():
    """
    :return:
    """
    test_game_state = GameState()
    hand_1 = [Card(Suit.HEART, Rank.EIGHT)]
    hand_2 = [Card(Suit.HEART, Rank.THREE)]
    result = compare_hand_spades(game_state=test_game_state, hand_1=hand_1, hand_2=hand_2)
    assert result is True


def test_compare_spade_hands_4():
    """

    :return:
    """
    test_game_state = GameState()
    hand_1 = [Card(Suit.BIG, Rank.JOKER)]
    hand_2 = [Card(Suit.SPADE, Rank.ACE)]
    result = compare_hand_spades(game_state=test_game_state, hand_1=hand_1, hand_2=hand_2)
    assert result is True


def test_compare_spade_hands_5():
    """

    :return:
    """
    test_game_state = GameState()
    hand_1 = [Card(Suit.SPADE, Rank.ACE)]
    hand_2 = [Card(Suit.BIG, Rank.JOKER)]
    result = compare_hand_spades(game_state=test_game_state, hand_1=hand_1, hand_2=hand_2)
    assert result is False


def test_compare_spade_hands_6():
    """

    :return:
    """
    test_game_state = GameState()
    hand_1 = [Card(Suit.SMALL, Rank.JOKER)]
    hand_2 = [Card(Suit.BIG, Rank.JOKER)]
    result = compare_hand_spades(game_state=test_game_state, hand_1=hand_1, hand_2=hand_2)
    assert result is False



