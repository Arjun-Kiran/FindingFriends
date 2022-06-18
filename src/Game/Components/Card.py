from dataclasses import dataclass
from Game.Modules.CardConstants import Suit, Rank


@dataclass
class Card():
    suit: Suit
    rank: Rank

