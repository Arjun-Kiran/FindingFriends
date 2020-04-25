from typing import List
from src.Game.Components.BaseComponent import BaseComponent
from src.Game.Components.Card import Card


class Player(BaseComponent):
    def __init__(self, name):
        super().__init__()
        self.name: str = name
        self.hand: List[Card] = list()
        self.team = None
