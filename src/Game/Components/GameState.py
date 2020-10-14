from typing import Dict, List
from src.Game.Modules.GameType import GameType
from src.Game.Modules.CardConstants import Suit, Rank
from src.Game.Components.BaseComponent import BaseComponent
from src.Game.Components.Player import Player
from src.Game.Components.Card import Card


class GameState(BaseComponent):
    def __init__(self):
        super().__init__()
        self.game_type: GameType = GameType.NO_GAME
        # Player
        self.score_map: Dict[str, int] = dict()
        self.player_map: Dict[str, Player] = dict()

        # Deck
        self.deck: List[Card] = list()
        self.discard_pile: List[Card] = list()

        # Starting Rules
        self.trump_suit: Suit = Suit.SPADE
        self.trump_rank: Rank = Rank.TWO

        # Round action
        self.leading_suit: Suit = Suit.NONE
        self.player_order: List[str] = list()
        self.player_cards_played: Dict[str, List[Card]] = dict()
        self.starting_player_idx: int = 0
        self.current_player_turn_idx: int = 0

    @property
    def deck_size(self) -> int:
        return len(self.deck)

    @property
    def number_of_players(self) -> int:
        return len(self.player_map.keys())

    @property
    def players_turn(self) -> str:
        try:
            return self.player_order[self.current_player_turn_idx]
        except IndexError:
            return ''

    @property
    def starting_player(self) -> str:
        try:
            return self.player_order[self.starting_player_idx]
        except IndexError:
            return ''
