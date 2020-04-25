from typing import Dict, List
from src.Game.Modules.CardConstants import Suit, Rank
from src.Game.Components.BaseComponent import BaseComponent
from src.Game.Components.Player import Player
from src.Game.Components.Card import Card


class GameState(BaseComponent):
    def __init__(self):
        super().__init__()
        self.trump_suit: Suit = Suit.SPADE
        self.trump_rank: Rank = Rank.TWO
        self.player_map: Dict[str, Player] = dict()
        self.deck: List[Card] = list()
