
import random
from typing import List
from Game.Components.Card import Card
from Game.Modules.CardConstants import CARDSUITS, JOKERSUITS, NONJOKERNUMBERS, Rank


def build_deck(number_of_decks: int = 1) -> List[Card]:
    _deck = list()
    for _ in range(number_of_decks):
        _deck += build_a_deck()
    return _deck


def build_a_deck() -> List[Card]:
    _deck = [Card(suit=suit, rank=rank) for rank in NONJOKERNUMBERS for suit in CARDSUITS]
    _deck += [Card(suit=suit, rank=Rank.JOKER) for suit in JOKERSUITS]
    return _deck


def shuffle_deck(deck_of_cards: List[Card]):
    random.shuffle(deck_of_cards)
    random.shuffle(deck_of_cards)
    random.shuffle(deck_of_cards)
    return deck_of_cards
