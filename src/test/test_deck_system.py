import copy
import pytest
from typing import Dict, List
from Game.Components.Card import Card
from Game.Systems.DeckSystem import build_a_deck
from Game.Systems.DeckSystem import build_deck
from Game.Systems.DeckSystem import shuffle_deck
from Game.Modules.CardConstants import Rank, Suit

def count_suit(deck : List[Card]) -> dict:
    count_dict = dict()
    for c in deck:
        if c.suit in count_dict:
            count_dict[c.suit] += 1
        else:
            count_dict[c.suit] = 1
    
    return count_dict


def count_rank(deck : List[Card]) -> dict:
    count_dict = dict()
    for c in deck:
        if c.rank in count_dict:
            count_dict[c.rank] += 1
        else:
            count_dict[c.rank] = 1    
    
    return count_dict


@pytest.mark.unit
def test_build_a_deck():
    deck = build_a_deck()
    no_dup_deck = list()
    assert len(deck) == 54
    for c in deck:
        if c not in no_dup_deck:
            no_dup_deck.append(c)
        else:
            raise Exception("Found duplicate: {}".format(c))


@pytest.mark.unit
def test_build_a_deck_rank():
    deck = build_a_deck()
    count_rank_result = count_rank(deck)

    assert count_rank_result[Rank.ACE] == 4
    assert count_rank_result[Rank.TWO] == 4
    assert count_rank_result[Rank.THREE] == 4
    assert count_rank_result[Rank.FOUR] == 4
    assert count_rank_result[Rank.FIVE] == 4
    assert count_rank_result[Rank.SIX] == 4
    assert count_rank_result[Rank.SEVEN] == 4
    assert count_rank_result[Rank.EIGHT] == 4
    assert count_rank_result[Rank.NINE] == 4
    assert count_rank_result[Rank.TEN] == 4
    assert count_rank_result[Rank.JACK] == 4
    assert count_rank_result[Rank.QUEEN] == 4
    assert count_rank_result[Rank.KING] == 4
    assert count_rank_result[Rank.JOKER] == 2


@pytest.mark.unit
def test_build_a_deck_suit():
    deck = build_a_deck()
    count_suit_result = count_suit(deck)

    assert count_suit_result[Suit.CLUB] == 13
    assert count_suit_result[Suit.HEART] == 13
    assert count_suit_result[Suit.DIAMOND] == 13
    assert count_suit_result[Suit.SPADE] == 13
    assert count_suit_result[Suit.SMALL] == 1
    assert count_suit_result[Suit.BIG] == 1


@pytest.mark.unit
def test_build_deck_suit():
    deck = build_deck(1)
    count_suit_result = count_suit(deck)

    assert count_suit_result[Suit.CLUB] == 13
    assert count_suit_result[Suit.HEART] == 13
    assert count_suit_result[Suit.DIAMOND] == 13
    assert count_suit_result[Suit.SPADE] == 13
    assert count_suit_result[Suit.SMALL] == 1
    assert count_suit_result[Suit.BIG] == 1

    two_deck = build_deck(2)
    count_suit_result = count_suit(two_deck)

    assert count_suit_result[Suit.CLUB] == 26
    assert count_suit_result[Suit.HEART] == 26
    assert count_suit_result[Suit.DIAMOND] == 26
    assert count_suit_result[Suit.SPADE] == 26
    assert count_suit_result[Suit.SMALL] == 2
    assert count_suit_result[Suit.BIG] == 2     


@pytest.mark.unit
def test_build_deck_rank():
    deck = build_deck(1)
    count_rank_result = count_rank(deck)

    assert count_rank_result[Rank.ACE] == 4
    assert count_rank_result[Rank.TWO] == 4
    assert count_rank_result[Rank.THREE] == 4
    assert count_rank_result[Rank.FOUR] == 4
    assert count_rank_result[Rank.FIVE] == 4
    assert count_rank_result[Rank.SIX] == 4
    assert count_rank_result[Rank.SEVEN] == 4
    assert count_rank_result[Rank.EIGHT] == 4
    assert count_rank_result[Rank.NINE] == 4
    assert count_rank_result[Rank.TEN] == 4
    assert count_rank_result[Rank.JACK] == 4
    assert count_rank_result[Rank.QUEEN] == 4
    assert count_rank_result[Rank.KING] == 4
    assert count_rank_result[Rank.JOKER] == 2

    two_deck = build_deck(2)
    count_rank_result = count_rank(two_deck)

    assert count_rank_result[Rank.ACE] == 8
    assert count_rank_result[Rank.TWO] == 8
    assert count_rank_result[Rank.THREE] == 8
    assert count_rank_result[Rank.FOUR] == 8
    assert count_rank_result[Rank.FIVE] == 8
    assert count_rank_result[Rank.SIX] == 8
    assert count_rank_result[Rank.SEVEN] == 8
    assert count_rank_result[Rank.EIGHT] == 8
    assert count_rank_result[Rank.NINE] == 8
    assert count_rank_result[Rank.TEN] == 8
    assert count_rank_result[Rank.JACK] == 8
    assert count_rank_result[Rank.QUEEN] == 8
    assert count_rank_result[Rank.KING] == 8
    assert count_rank_result[Rank.JOKER] == 4


@pytest.mark.unit
def test_build_deck():
    one_deck = build_deck(1)
    two_decks = build_deck(2)
    three_decks = build_deck(3)
    four_decks = build_deck(4)

    assert len(one_deck) == 54
    assert len(two_decks) == 2*54
    assert len(three_decks) == 3*54
    assert len(four_decks) == 4*54
    

@pytest.mark.unit
def test_shuffle_deck():
    deck = build_a_deck()
    shuffled_deck = copy.deepcopy(deck)
    shuffled_deck = shuffle_deck(shuffled_deck)

    first_four = (deck[0], deck[1], deck[2], deck[3])
    first_four_unshuffled = (shuffled_deck[0], shuffled_deck[1], shuffled_deck[2], shuffled_deck[3])

    assert first_four != first_four_unshuffled
