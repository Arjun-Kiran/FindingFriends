
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

    if number_of_players in [5,6,7]:
        deck_to_build = 2
    elif number_of_decks in [8, 9, 10, 11]:
        deck_to_build = 3
    elif number_of_decks == 12:
        deck_to_build = 4

    return deck_to_build


def number_of_card_to_deal(number_of_players: int) -> int:
    deal_dictionary = {
        '5' : 20,
        '6' : 17,
        '7' : 14,
        '8' : 19,
        '9' : 17,
        '10' : 15, 
        '11' : 14, 
        '12' : 17 
    }
    if number_of_players < 5:
        raise Exception("Not enough players. Need 5 or more")

    if number_of_players > 12:
        raise Exception("Too many players")

    return deal_dictionary[str(number_of_players)]
    

