from dataclasses import dataclass
from typing import Dict, List
from uuid import uuid4
from Game.Components.Card import Card, card_list_to_str_list
from Game.Modules.CardConstants import Rank, Suit
from Game.Components.Player import Player

class GameState():
    def __init__(self) -> None:
        self.session: str = str(uuid4())

        # Players
        self.current_alpha_player: str = ''
        self.current_friends_of_alpha: List[str] = list()
        self.player_order: List[Player] = list()
        self.current_player_idx: int = 0
        self.players_and_hand: Dict[str, List[Card]] = dict()
        self.players_round_score: Dict[str, int] = dict()
        self.players_overall_score: Dict[str, int] = dict()

        # Cards in and out of play
        self.cards_in_deck: List[Card] = list()
        self.cards_in_active_pile: List[Card] = list()
        self.card_in_discard_pile: List[Card] = list()
        self.card_out_of_play: List[Card] = list()
        self.leading_hand_of_subround: List[Card] = list()
        self.current_hand_played: List[Card] = list()
        self.declare_trump_rank: Rank = None
        self.declare_trump_suite: Suit = None

        self.friend_calling_cards: str = ''
