
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


def number_of_decks(number_of_players: int) -> int:
    deck_to_build: int = 0
    if number_of_players < 5:
        raise Exception("Not enough players. Need 5 or more")

    if number_of_players > 12:
        raise Exception("Too many players")

    if number_of_players in [5,6,]:
        deck_to_build = 3
    elif number_of_players in [7, 8]:
        deck_to_build = 4
    elif number_of_players in [9, 10]:
        deck_to_build = 5
    elif number_of_players in [11, 12]:
        deck_to_build = 6

    return deck_to_build


def number_of_card_to_deal(number_of_players: int) -> int:
    deal_dictionary = {
        '5' : 30,
        '6' : 26,
        '7' : 29,
        '8' : 26,
        '9' : 29,
        '10' : 26, 
        '11' : 26, 
        '12' : 26 
    }
    if number_of_players < 5:
        raise Exception("Not enough players. Need 5 or more")

    if number_of_players > 12:
        raise Exception("Too many players")

    return deal_dictionary[str(number_of_players)]
    

