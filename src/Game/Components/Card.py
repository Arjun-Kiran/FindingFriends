from src.Game.Components.BaseComponent import BaseComponent
from src.Game.Modules.CardConstants import Suit, Rank


class Card(BaseComponent):
    def __init__(self, suit: Suit, rank: Rank):
        super().__init__()
        self.suit = suit
        self.rank = rank

    def __str__(self):
        return u'{rank} of {suit}'.format(rank=self.rank, suit=self.suit)
