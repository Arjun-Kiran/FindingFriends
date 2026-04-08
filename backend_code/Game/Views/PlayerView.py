import json
from enum import Enum
from pydantic import BaseModel
from typing import Dict, List, Optional
from Game.Components.GameState import GameState, DeclareTrump, DeclareCallingCard
from Game.Components.Card import Card
from Game.Components.Player import Player
from Game.Views.CardView import card_list_to_emoji_str_list
from Game.Systems.GameStateSystem import find_player, is_player_an_alpha
from Game.Systems.TeamSystem import number_of_cards_to_call_friends
from Game.Modules.EventEnum import GameEventState
from Game.Modules.CardConstants import Suit, Rank


def _serialize_for_json(obj):
    """Recursively convert a Pydantic .dict() output to JSON-safe types.
    Enum objects are converted to their .name (string) so the frontend
    sees 'HEART' instead of 48.
    """
    if isinstance(obj, Enum):
        return obj.name if not isinstance(obj, str) else obj.value
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(v) for v in obj]
    return obj


class PlayerView(BaseModel):
    name: str = ''
    uuid: str = ''
    can_start_game: bool = False
    my_turn: bool = False
    hosting: bool = False
    is_alpha: bool = False
    on_alpha_team: bool = False
    number_of_players: int = 0
    current_player: Optional[Player] = None
    leading_player: Optional[Player] = None
    winning_player_of_round: Optional[Player] = None
    player_list: List[Player] = list()
    player_hand: List[Card] = list()
    players_round_score: Dict[str, int] = dict()
    players_overall_score: Dict[str, int] = dict()
    game_event_state: GameEventState = GameEventState.NOT_AVAILABLE
    game_code: str = ''
    declare_trump: DeclareTrump = DeclareTrump(rank=None, suit=None)
    cards_in_active_pile: List[Card] = list()
    leading_hand_of_subround: List[Card] = list()
    kitty_size: int = 0
    my_level: int = 0
    player_levels: Dict[str, int] = dict()
    friend_calling_cards: List[DeclareCallingCard] = list()
    num_friends_to_call: int = 0
    revealed_friends: List[str] = list()
    round_winner_side: str = ''
    round_defender_points: int = 0
    round_promotion_levels: int = 0
    round_promoted_players: List[str] = list()
    game_winner: str = ''

    def to_json_dict(self) -> dict:
        """Return a dict safe for JSON serialization (enums as name strings)."""
        return _serialize_for_json(self.dict())


def sort_hand(cards: list, trump_suit, trump_rank) -> list:
    """Sort a hand of cards: non-trump cards grouped by suit then rank,
    trump-suit cards next, then trump-rank cards of other suits, then jokers.
    Within each group, cards are sorted by rank ascending."""
    SUIT_ORDER = {Suit.CLUB: 0, Suit.SPADE: 1, Suit.HEART: 2, Suit.DIAMOND: 3}

    def card_sort_key(card):
        is_joker = card.rank == Rank.JOKER
        is_trump_rank = trump_rank and card.rank == trump_rank and not is_joker
        is_trump_suit = trump_suit and card.suit == trump_suit and not is_joker

        if is_joker:
            # Big joker after small joker, both at the very end
            return (4, 0, card.suit.value)
        if is_trump_rank and is_trump_suit:
            # Trump rank in trump suit — highest trump card
            return (3, 1, 0)
        if is_trump_rank:
            # Trump rank in other suits — grouped with trumps
            return (3, 0, SUIT_ORDER.get(card.suit, 5))
        if is_trump_suit:
            # Trump suit (non-trump-rank) — sorted by rank
            return (2, card.rank.value, 0)
        # Non-trump: sort by suit then rank
        return (SUIT_ORDER.get(card.suit, 5), card.rank.value, 0)

    return sorted(cards, key=card_sort_key)


def player_view_state(current_game_state: GameState, player_uuid: str) -> PlayerView:
    player_object = current_game_state.player_dict[player_uuid]
    player_view = PlayerView()
    player_view.uuid = str(player_object.uuid)
    player_view.name = str(player_object.name)
    player_view.game_event_state = current_game_state.game_event_state
    player_view.game_code = current_game_state.game_code
    player_view.hosting = str(current_game_state.hosting_player.uuid) == str(player_object.uuid)
    player_view.is_alpha = is_player_an_alpha(current_game_state, player_object.uuid)
    player_view.number_of_players = len(current_game_state.player_order)
    player_view.players_round_score = current_game_state.players_round_score
    player_view.players_overall_score = current_game_state.players_overall_score
    player_view.can_start_game = current_game_state.can_start_game
    player_view.player_list = current_game_state.player_order
    raw_hand = current_game_state.players_and_hand.get(player_uuid, [])
    trump = current_game_state.declare_trump
    player_view.player_hand = sort_hand(raw_hand, trump.suit, trump.rank)
    player_view.declare_trump = current_game_state.declare_trump
    player_view.cards_in_active_pile = current_game_state.cards_in_active_pile
    player_view.leading_hand_of_subround = current_game_state.leading_hand_of_subround
    player_view.kitty_size = len(current_game_state.cards_in_deck)
    player_view.player_levels = current_game_state.player_levels
    player_view.my_level = current_game_state.player_levels.get(player_uuid, 0)
    player_view.friend_calling_cards = current_game_state.friend_calling_cards
    player_view.revealed_friends = current_game_state.current_friends_of_alpha
    alpha_uuid = current_game_state.current_alpha_player.player_uuid
    alpha_team = {alpha_uuid} | set(current_game_state.current_friends_of_alpha)
    player_view.on_alpha_team = player_uuid in alpha_team
    num_players = len(current_game_state.player_order)
    player_view.num_friends_to_call = number_of_cards_to_call_friends(num_players) if num_players >= 5 else 0

    # Round result info
    player_view.round_winner_side = current_game_state.round_winner_side
    player_view.round_defender_points = current_game_state.round_defender_points
    player_view.round_promotion_levels = current_game_state.round_promotion_levels
    player_view.round_promoted_players = current_game_state.round_promoted_players
    player_view.game_winner = current_game_state.game_winner

    # Current player / turn info
    current_player_uuid = current_game_state.current_player.player_uuid
    if current_player_uuid and current_player_uuid in current_game_state.player_dict:
        player_view.current_player = current_game_state.player_dict[current_player_uuid]
        player_view.my_turn = current_player_uuid == player_uuid

    leading_uuid = current_game_state.leading_player.player_uuid
    if leading_uuid and leading_uuid in current_game_state.player_dict:
        player_view.leading_player = current_game_state.player_dict[leading_uuid]

    winning_uuid = current_game_state.winning_player_of_round.player_uuid
    if winning_uuid and winning_uuid in current_game_state.player_dict:
        player_view.winning_player_of_round = current_game_state.player_dict[winning_uuid]

    return player_view
