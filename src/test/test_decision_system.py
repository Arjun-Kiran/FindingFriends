from re import T
import pytest
from Game.Views.CardView import card_str
from Game.Components.Card import Card, Rank, Suit
from Game.Systems.DecisionSystem import is_trump, determine_leading_play
from Game.Systems.DecisionSystem import card_value, card_value_match_bonus
from Game.Systems.DecisionSystem import single_card_lead_decision, is_an_identical_set
from Game.Systems.DecisionSystem import counting_card, is_all_the_same_suit, is_all_trump_cards


@pytest.mark.unit
@pytest.mark.parametrize('testcase', [(Card(Suit.DIAMOND, Rank.FIVE), 4),
                                      (Card(Suit.BIG, Rank.JOKER), 500),
                                      (Card(Suit.SMALL, Rank.JOKER), 400),
                                      (Card(Suit.HEART, Rank.THREE), 300),
                                      (Card(Suit.CLUB, Rank.THREE), 200),
                                      (Card(Suit.HEART, Rank.FIVE), 104)])
def test_card_value(testcase):
    trump = {'rank': Rank.THREE,
            'suit': Suit.HEART}
    v = card_value(trump, testcase[0])
    assert v == testcase[1]


@pytest.mark.unit
@pytest.mark.parametrize('testcase', [(Card(Suit.DIAMOND, Rank.FIVE), 4),
                                      (Card(Suit.BIG, Rank.JOKER), 500),
                                      (Card(Suit.SMALL, Rank.JOKER), 400),
                                      (Card(Suit.HEART, Rank.THREE), 300),
                                      (Card(Suit.CLUB, Rank.THREE), 200),
                                      (Card(Suit.HEART, Rank.FIVE), 104)])
def test_card_value_without_match_bonus(testcase):
    matching_leading_play = False
    trump = {'rank': Rank.THREE,
            'suit': Suit.HEART}
    v = card_value_match_bonus(trump, testcase[0], matching_leading_play)
    assert v == testcase[1]


@pytest.mark.unit
@pytest.mark.parametrize('testcase', [(Card(Suit.DIAMOND, Rank.FIVE), 4),
                                      (Card(Suit.BIG, Rank.JOKER), 500),
                                      (Card(Suit.SMALL, Rank.JOKER), 400),
                                      (Card(Suit.HEART, Rank.THREE), 300),
                                      (Card(Suit.CLUB, Rank.THREE), 200),
                                      (Card(Suit.HEART, Rank.FIVE), 104)])
def test_card_value_with_match_bonus(testcase):
    match_bonus = 600
    matching_leading_play = True
    trump = {'rank': Rank.THREE,
            'suit': Suit.HEART}
    v = card_value_match_bonus(trump, testcase[0], matching_leading_play)
    assert v == testcase[1] + match_bonus



@pytest.mark.unit
@pytest.mark.parametrize('testcase', [
    (Card(Suit.DIAMOND, Rank.FIVE), Card(Suit.DIAMOND, Rank.FIVE), Card(Suit.DIAMOND, Rank.FIVE), False),
    (Card(Suit.DIAMOND, Rank.FIVE), Card(Suit.BIG, Rank.JOKER), Card(Suit.DIAMOND, Rank.FIVE), False),
    (Card(Suit.DIAMOND, Rank.FIVE), Card(Suit.DIAMOND, Rank.FIVE), Card(Suit.BIG, Rank.JOKER), True),
    (Card(Suit.DIAMOND, Rank.FIVE), Card(Suit.HEART, Rank.THREE), Card(Suit.HEART, Rank.FIVE), False),
    (Card(Suit.HEART, Rank.FIVE), Card(Suit.HEART, Rank.FIVE), Card(Suit.CLUB, Rank.FIVE), False),
    (Card(Suit.CLUB, Rank.TEN), Card(Suit.CLUB, Rank.JACK), Card(Suit.CLUB, Rank.KING), True),
    (Card(Suit.CLUB, Rank.TEN), Card(Suit.DIAMOND, Rank.ACE), Card(Suit.CLUB, Rank.FIVE), True),
    (Card(Suit.DIAMOND, Rank.FIVE), Card(Suit.DIAMOND, Rank.ACE), Card(Suit.CLUB, Rank.THREE), True)
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
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(Suit.HEART, Rank.THREE), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(Suit.BIG, Rank.JOKER), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(Suit.SMALL, Rank.JOKER), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(Suit.HEART, Rank.ACE), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(Suit.HEART, Rank.TEN), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(Suit.DIAMOND, Rank.THREE), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(Suit.CLUB, Rank.THREE), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(Suit.SPADE, Rank.THREE), True),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(Suit.SPADE, Rank.TWO), False),
    ({'rank': Rank.THREE, 'suit': Suit.HEART}, Card(Suit.DIAMOND, Rank.NINE), False),
    ({'rank': Rank.NINE, 'suit': Suit.HEART}, Card(Suit.DIAMOND, Rank.NINE), True),
    ({'rank': Rank.NINE, 'suit': Suit.DIAMOND}, Card(Suit.DIAMOND, Rank.ACE), True),
    ({'rank': Rank.NINE, 'suit': Suit.DIAMOND}, Card(Suit.HEART, Rank.ACE), False),
    ({'rank': Rank.NINE, 'suit': Suit.DIAMOND}, Card(Suit.BIG, Rank.JOKER), True),
    ])
def test_is_trump(testcase):
    trump = testcase[0]
    card_played = testcase[1]
    expected_output = testcase[2]
    output = is_trump(trump,card_played)
    assert output is expected_output


@pytest.mark.unit
@pytest.mark.parametrize('testcase', [
    [ [Card(Suit.DIAMOND, Rank.ACE),Card(Suit.DIAMOND, Rank.ACE)], True],
    [ [Card(Suit.DIAMOND, Rank.ACE),Card(Suit.DIAMOND, Rank.TWO)], False],
    [ [Card(Suit.HEART, Rank.ACE),Card(Suit.HEART, Rank.ACE), Card(Suit.HEART, Rank.ACE)], True],
    [ [Card(Suit.HEART, Rank.ACE),Card(Suit.HEART, Rank.ACE), Card(Suit.DIAMOND, Rank.ACE)], False],
    [ [Card(Suit.CLUB, Rank.ACE),Card(Suit.HEART, Rank.ACE), Card(Suit.DIAMOND, Rank.ACE)], False],
    ])
def test_is_an_identical_set(testcase):
    output = is_an_identical_set(testcase[0])
    assert output is testcase[1]


@pytest.mark.unit
@pytest.mark.parametrize('testcase', [
    [ [Card(Suit.DIAMOND, Rank.ACE)], 1],
    [ [Card(Suit.DIAMOND, Rank.ACE),Card(Suit.DIAMOND, Rank.ACE)], 2],
    [ [Card(Suit.HEART, Rank.TWO),Card(Suit.HEART, Rank.TWO), Card(Suit.HEART, Rank.TWO)], 3],
    [ [Card(Suit.CLUB, Rank.ACE),Card(Suit.CLUB, Rank.ACE), Card(Suit.CLUB, Rank.ACE), Card(Suit.CLUB, Rank.ACE)], 4]
    ])
def test_counting_card(testcase):
    hand = testcase[0]
    output = counting_card(hand)
    assert testcase[1] == output[card_str(hand[0])]

