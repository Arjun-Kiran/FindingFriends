from src.Game.Components.Card import Card
from src.Game.Modules.CardConstants import CARDSUITS, JOKERSUITS, NONJOKERNUMBERS, Rank


def build_deck(number_of_decks=1):
    _deck = list()
    for _ in range(number_of_decks):
        _deck += build_a_deck()
    return _deck


def build_a_deck():
    _deck = [Card(suit=suit, rank=rank) for rank in NONJOKERNUMBERS for suit in CARDSUITS]
    _deck += [Card(suit=suit, rank=Rank.JOKER) for suit in JOKERSUITS]
    return _deck

