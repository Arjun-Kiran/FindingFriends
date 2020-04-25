from typing import List
from src.Game.Components.Card import Card


class Player(object):
    def __init__(self, name):
        self.name = name
        self.hand: List[Card] = list()
        self.team = None
