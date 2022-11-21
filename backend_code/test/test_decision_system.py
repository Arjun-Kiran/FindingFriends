from re import T
import pytest
from Game.Views.CardView import card_str
from Game.Components.Card import Card, Rank, Suit
from Game.Systems.DecisionSystem import is_trump, determine_leading_play
from Game.Systems.DecisionSystem import card_value, card_value_match_bonus
from Game.Systems.DecisionSystem import single_card_lead_decision, is_an_identical_set
from Game.Systems.DecisionSystem import counting_card, is_all_the_same_suit, is_all_trump_cards


@pytest.mark.unit
@pytest.mark.parametrize('testcase', [(Card(suit=Suit.DIAMOND, rank=Rank.FIVE), 4),
                                      (Card(suit=Suit.BIG, rank=Rank.JOKER), 500),
                                      (Card(suit=Suit.SMALL, rank=Rank.JOKER), 400),
                                      (Card(suit=Suit.HEART, rank=Rank.THREE), 300),
                                      (Card(suit=Suit.CLUB, rank=Rank.THREE), 200),
                                      (Card(suit=Suit.HEART, rank=Rank.FIVE), 104)])
def test_card_value(testcase):
    trump = {'rank': Rank.THREE,
            'suit': Suit.HEART}
    v = card_value(trump, testcase[0])
    assert v == testcase[1]


@pytest.mark.unit
@pytest.mark.parametrize('testcase', [(Card(suit=Suit.DIAMOND, rank=Rank.FIVE), 4),
                                      (Card(suit=Suit.BIG, rank=Rank.JOKER), 500),
                                      (Card(suit=Suit.SMALL, rank=Rank.JOKER), 400),
                                      (Card(suit=Suit.HEART, rank=Rank.THREE), 300),
                                      (Card(suit=Suit.CLUB, rank=Rank.THREE), 200),
                                      (Card(suit=Suit.HEART, rank=Rank.FIVE), 104)])
def test_card_value_without_match_bonus(testcase):
    matching_leading_play = False
    trump = {'rank': Rank.THREE,
            'suit': Suit.HEART}
    v = card_value_match_bonus(trump, testcase[0], matching_leading_play)
    assert v == testcase[1]


@pytest.mark.unit
@pytest.mark.parametrize('testcase', [(Card(suit=Suit.DIAMOND, rank=Rank.FIVE), 4),
                                      (Card(suit=Suit.BIG, rank=Rank.JOKER), 500),
                                      (Card(suit=Suit.SMALL, rank=Rank.JOKER), 400),
                                      (Card(suit=Suit.HEART, rank=Rank.THREE), 300),
                                      (Card(suit=Suit.CLUB, rank=Rank.THREE), 200),
                                      (Card(suit=Suit.HEART, rank=Rank.FIVE), 104)])
def test_card_value_with_match_bonus(testcase):
    match_bonus = 600
    matching_leading_play = True
    trump = {'rank': Rank.THREE,
            'suit': Suit.HEART}
    v = card_value_match_bonus(trump, testcase[0], matching_leading_play)
    assert v == testcase[1] + match_bonus



@pytest.mark.unit
@pytest.mark.parametrize('testcase', [
    (Card(suit=Suit.DIAMOND, rank=Rank.FIVE), Card(suit=Suit.DIAMOND, rank=Rank.FIVE), Card(suit=Suit.DIAMOND, rank=Rank.FIVE), False),
    (Card(suit=Suit.DIAMOND, rank=Rank.FIVE), Card(suit=Suit.BIG, rank=Rank.JOKER), Card(suit=Suit.DIAMOND, rank=Rank.FIVE), False),
    (Card(suit=Suit.DIAMOND, rank=Rank.FIVE), Card(suit=Suit.DIAMOND, rank=Rank.FIVE), Card(suit=Suit.BIG, rank=Rank.JOKER), True),
    (Card(suit=Suit.DIAMOND, rank=Rank.FIVE), Card(suit=Suit.HEART, rank=Rank.THREE), Card(suit=Suit.HEART, rank=Rank.FIVE), False),
    (Card(suit=Suit.HEART, rank=Rank.FIVE), Card(suit=Suit.HEART, rank=Rank.FIVE), Card(suit=Suit.CLUB, rank=Rank.FIVE), False),
    (Card(suit=Suit.CLUB, rank=Rank.TEN), Card(suit=Suit.CLUB, rank=Rank.JACK), Card(suit=Suit.CLUB, rank=Rank.KING), True),
    (Card(suit=Suit.CLUB, rank=Rank.TEN), Card(suit=Suit.DIAMOND, rank=Rank.ACE), Card(suit=Suit.CLUB, rank=Rank.FIVE), True),
    (Card(suit=Suit.DIAMOND, rank=Rank.FIVE), Card(suit=Suit.DIAMOND, rank=Rank.ACE), Card(suit=Suit.CLUB, rank=Rank.THREE), True)
])
def test_single_card_lead_decision(testcase):
    trump = {'rank': Rank.THREE,
        'suit': Suit.HEART}
    leading_play = testcase[0]
    winning_play = testcase[1]
    contesting_play = testcase[2]
    output = single_card_lead_decision(trump, leading_play, winning_play, contesting_play)

    assert output is testcase[3]


@pytest.mark.unit
@pytest.mark.parametrize('testcase', [
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(suit=Suit.HEART, rank=Rank.THREE), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(suit=Suit.BIG, rank=Rank.JOKER), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(suit=Suit.SMALL, rank=Rank.JOKER), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(suit=Suit.HEART, rank=Rank.ACE), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(suit=Suit.HEART, rank=Rank.TEN), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(suit=Suit.DIAMOND, rank=Rank.THREE), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(suit=Suit.CLUB, rank=Rank.THREE), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(suit=Suit.SPADE, rank=Rank.THREE), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(suit=Suit.SPADE, rank=Rank.TWO), False),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(suit=Suit.DIAMOND, rank=Rank.NINE), False),
    ({'rank': Rank.NINE, 'suit': Suit.HEART}, Card(suit=Suit.DIAMOND, rank=Rank.NINE), True),
    ({'rank': Rank.NINE, 'suit': Suit.DIAMOND}, Card(suit=Suit.DIAMOND, rank=Rank.ACE), True),
    ({'rank': Rank.NINE, 'suit': Suit.DIAMOND}, Card(suit=Suit.HEART, rank=Rank.ACE), False),
    ({'rank': Rank.NINE, 'suit': Suit.DIAMOND}, Card(suit=Suit.BIG, rank=Rank.JOKER), True),
    ])
def test_is_trump(testcase):
    trump = testcase[0]
    card_played = testcase[1]
    expected_output = testcase[2]
    output = is_trump(trump,card_played)
    assert output is expected_output


@pytest.mark.unit
@pytest.mark.parametrize('testcase', [
    [ [Card(suit=Suit.DIAMOND, rank=Rank.ACE),Card(suit=Suit.DIAMOND, rank=Rank.ACE)], True],
    [ [Card(suit=Suit.DIAMOND, rank=Rank.ACE),Card(suit=Suit.DIAMOND, rank=Rank.TWO)], False],
    [ [Card(suit=Suit.HEART, rank=Rank.ACE),Card(suit=Suit.HEART, rank=Rank.ACE), Card(suit=Suit.HEART, rank=Rank.ACE)], True],
    [ [Card(suit=Suit.HEART, rank=Rank.ACE),Card(suit=Suit.HEART, rank=Rank.ACE), Card(suit=Suit.DIAMOND, rank=Rank.ACE)], False],
    [ [Card(suit=Suit.CLUB, rank=Rank.ACE),Card(suit=Suit.HEART, rank=Rank.ACE), Card(suit=Suit.DIAMOND, rank=Rank.ACE)], False],
    ])
def test_is_an_identical_set(testcase):
    output = is_an_identical_set(testcase[0])
    assert output is testcase[1]


@pytest.mark.unit
@pytest.mark.parametrize('testcase', [
    [ [Card(suit=Suit.DIAMOND, rank=Rank.ACE)], 1],
    [ [Card(suit=Suit.DIAMOND, rank=Rank.ACE),Card(suit=Suit.DIAMOND, rank=Rank.ACE)], 2],
    [ [Card(suit=Suit.HEART, rank=Rank.TWO),Card(suit=Suit.HEART, rank=Rank.TWO), Card(suit=Suit.HEART, rank=Rank.TWO)], 3],
    [ [Card(suit=Suit.CLUB, rank=Rank.ACE),Card(suit=Suit.CLUB, rank=Rank.ACE), Card(suit=Suit.CLUB, rank=Rank.ACE), Card(suit=Suit.CLUB, rank=Rank.ACE)], 4]
    ])
def test_counting_card(testcase):
    hand = testcase[0]
    output = counting_card(hand)
    assert testcase[1] == output[card_str(hand[0])]

