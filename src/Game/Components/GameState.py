from pydantic import BaseModel
from typing import Dict, List, Optional
from uuid import uuid4
from Game.Components.Card import Card
from Game.Modules.CardConstants import Rank, Suit
from Game.Components.Player import Player, PlayerPointer


class DeclareTrump(BaseModel):
    rank: Optional[Rank]
    suit: Optional[Suit]

class DeclareCallingCard(BaseModel):
    suit: Suit
    order: int


class GameState(BaseModel):
    session: str = str(uuid4())
    current_alpha_player: PlayerPointer = PlayerPointer(index=0, player_uuid='')
    # Players
    current_friends_of_alpha: List[str] = list()
    player_order: List[Player] = list()

    current_player: PlayerPointer = PlayerPointer(index=0, player_uuid='')
    leading_player: PlayerPointer = PlayerPointer(index=0, player_uuid='')
    winning_player_of_round: PlayerPointer = PlayerPointer(index=0, player_uuid='')

    players_and_hand: Dict[str, List[Card]] = dict()
    players_round_score: Dict[str, int] = dict()
    players_overall_score: Dict[str, int] = dict()

    # Cards in and out of play
    cards_in_deck: List[Card] = list()
    cards_in_active_pile: List[Card] = list()
    card_in_discard_pile: List[Card] = list()
    card_out_of_play: List[Card] = list()
    leading_hand_of_subround: List[Card] = list()
    current_hand_played: List[Card] = list()
    declare_trump: DeclareTrump = DeclareTrump(rank=None, suit=None)

    friend_calling_cards: List[DeclareCallingCard] = list()
    all_friends_found: bool = False
    events: List = list()
