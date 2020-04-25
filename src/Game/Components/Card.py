from src.Game.Modules.CardConstants import Suit, Rank


class Card(object):
    def __init__(self, suit: Suit, rank: Rank):
        self.suit = suit
        self.rank = rank
