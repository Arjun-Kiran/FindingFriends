from typing import Dict, List
from src.Game.Modules.CardConstants import Suit, Rank
from src.Game.Components.Player import Player
from src.Game.Components.Card import Card


class GameState(object):
    def __init__(self):
        self.trump_suit: Suit = Suit.SPADE
        self.trump_rank: Rank = Rank.TWO
        self.player_map: Dict[str, Player] = dict()
        self.deck: List[Card] = list()
