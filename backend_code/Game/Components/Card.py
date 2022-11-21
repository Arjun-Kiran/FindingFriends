from pydantic import BaseModel
from Game.Modules.CardConstants import Suit, Rank


class Card(BaseModel):
    suit: Suit
    rank: Rank
