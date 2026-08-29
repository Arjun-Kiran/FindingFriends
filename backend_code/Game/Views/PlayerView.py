import json
from enum import Enum
from pydantic import BaseModel
from typing import Dict, List, Optional, Set
from Game.Components.GameState import GameState, DeclareTrump, DeclareCallingCard
from Game.Components.Card import Card
from Game.Components.Player import Player
from Game.Views.CardView import card_list_to_emoji_str_list
from Game.Systems.GameStateSystem import find_player, is_player_an_alpha
from Game.Systems.DecisionSystem import playable_cards
from Game.Systems.TeamSystem import number_of_cards_to_call_friends
from Game.Systems.PointSystem import alpha_team_uuids, team_round_points
from Game.Modules.EventEnum import EventItem, GameEventState
from Game.Modules.Avatars import ANIMAL_AVATARS


def _serialize_for_json(obj):
    """Recursively convert a Pydantic .model_dump() output to JSON-safe types.
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
    # This player's own avatar. Everyone else's rides along on player_list.
    avatar: str = ''
    # The whole catalog, so the lobby picker and the server agree on what is
    # offered. Which ones are taken is derivable from player_list.
    avatar_choices: List[str] = list()
    can_start_game: bool = False
    # Who the alpha and the host are, for everyone — not just "is it me".
    # Both are public knowledge at the table, and the players bar needs them
    # to put the crown on the right player.
    alpha_uuid: str = ''
    host_uuid: str = ''
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
    # One flag per card in player_hand: could that card be part of a legal play
    # right now? A hint for the player's own hand, sent only on their turn —
    # the server still refuses an illegal play either way. Empty off-turn.
    playable_hand_cards: List[bool] = list()
    players_round_score: Dict[str, int] = dict()
    players_overall_score: Dict[str, int] = dict()
    # Round points belong to a team, not a player — teammates share one total.
    alpha_team_points: int = 0
    defender_team_points: int = 0
    my_team_points: int = 0
    game_event_state: GameEventState = GameEventState.NOT_AVAILABLE
    game_code: str = ''
    declare_trump: DeclareTrump = DeclareTrump(rank=None, suit=None)
    cards_in_active_pile: List[Card] = list()
    # Who played each card above, one uuid per card in the same order, so the
    # table can see whose card is whose during a trick.
    active_pile_player_uuids: List[str] = list()
    leading_hand_of_subround: List[Card] = list()
    kitty_size: int = 0
    my_level: int = 0
    player_levels: Dict[str, int] = dict()
    friend_calling_cards: List[DeclareCallingCard] = list()
    num_friends_to_call: int = 0
    revealed_friends: List[str] = list()
    # Team totals give away hidden partnerships, so they stay hidden until
    # every friend has revealed themselves by playing a called card.
    all_friends_found: bool = False
    round_winner_side: str = ''
    round_defender_points: int = 0
    round_promotion_levels: int = 0
    round_promoted_players: List[str] = list()
    game_winner: str = ''
    # Uuids of players in this game with no live socket right now. Their seats
    # are held — hands are dealt and turn order depends on them — so this is
    # what lets the table see who they are waiting on.
    disconnected_players: List[str] = list()
    events: List[EventItem] = list()

    def to_json_dict(self) -> dict:
        """Return a dict safe for JSON serialization (enums as name strings)."""
        return _serialize_for_json(self.model_dump())


def player_view_state(current_game_state: GameState, player_uuid: str,
                      connected_uuids: Optional[Set[str]] = None) -> PlayerView:
    """Build one player's view of the game.

    `connected_uuids` is who currently holds a live socket. Pass None when
    connection state isn't known (tests, tooling) and everyone is treated as
    present."""
    player_object = current_game_state.player_dict[player_uuid]
    player_view = PlayerView()
    player_view.uuid = str(player_object.uuid)
    player_view.name = str(player_object.name)
    player_view.avatar = str(player_object.avatar)
    player_view.avatar_choices = list(ANIMAL_AVATARS)
    player_view.game_event_state = current_game_state.game_event_state
    player_view.game_code = current_game_state.game_code
    player_view.hosting = str(current_game_state.hosting_player.uuid) == str(player_object.uuid)
    player_view.is_alpha = is_player_an_alpha(current_game_state, player_object.uuid)
    player_view.alpha_uuid = str(current_game_state.current_alpha_player.player_uuid or '')
    player_view.host_uuid = (str(current_game_state.hosting_player.uuid)
                             if current_game_state.hosting_player else '')
    player_view.number_of_players = len(current_game_state.player_order)
    player_view.players_round_score = current_game_state.players_round_score
    player_view.players_overall_score = current_game_state.players_overall_score
    player_view.can_start_game = current_game_state.can_start_game
    player_view.player_list = current_game_state.player_order
    raw_hand = list(current_game_state.players_and_hand.get(player_uuid, []))
    # During kitty sort, show the alpha player the kitty cards added to their hand
    if (current_game_state.game_event_state == GameEventState.WAITING_ON_ALPHA_KITTY_SORT
            and player_view.is_alpha):
        raw_hand.extend(current_game_state.cards_in_deck)
    # Sent in the order the engine holds it. How a hand is laid out is the
    # player's own business and lives in the client, which lets them drag cards
    # around and keep that arrangement — see frontend utils/handOrder.js. A
    # server-side sort would fight it on every push.
    player_view.player_hand = raw_hand
    player_view.declare_trump = current_game_state.declare_trump
    player_view.cards_in_active_pile = current_game_state.cards_in_active_pile
    player_view.active_pile_player_uuids = current_game_state.active_pile_player_uuids
    player_view.leading_hand_of_subround = current_game_state.leading_hand_of_subround
    player_view.kitty_size = len(current_game_state.cards_in_deck)
    player_view.player_levels = current_game_state.player_levels
    player_view.my_level = current_game_state.player_levels.get(player_uuid, 0)
    player_view.friend_calling_cards = current_game_state.friend_calling_cards
    player_view.revealed_friends = current_game_state.current_friends_of_alpha
    player_view.all_friends_found = current_game_state.all_friends_found
    player_view.events = current_game_state.events
    if connected_uuids is not None:
        player_view.disconnected_players = [
            uuid for uuid in current_game_state.player_dict
            if uuid not in connected_uuids
        ]
    player_view.on_alpha_team = player_uuid in alpha_team_uuids(current_game_state)
    num_players = len(current_game_state.player_order)
    player_view.num_friends_to_call = number_of_cards_to_call_friends(num_players) if num_players >= 5 else 0

    # Team point totals — teammates see the same number
    alpha_points, defender_points = team_round_points(current_game_state)
    player_view.alpha_team_points = alpha_points
    player_view.defender_team_points = defender_points
    player_view.my_team_points = alpha_points if player_view.on_alpha_team else defender_points

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

    # Only worth working out on this player's turn, and only once the turn is
    # known — which is here. Flags line up with the SORTED hand above, because
    # that is the one the player is looking at.
    if player_view.my_turn and current_game_state.game_event_state == GameEventState.ROUND_STARTED:
        player_view.playable_hand_cards = playable_cards(current_game_state, player_view.player_hand)

    leading_uuid = current_game_state.leading_player.player_uuid
    if leading_uuid and leading_uuid in current_game_state.player_dict:
        player_view.leading_player = current_game_state.player_dict[leading_uuid]

    winning_uuid = current_game_state.winning_player_of_round.player_uuid
    if winning_uuid and winning_uuid in current_game_state.player_dict:
        player_view.winning_player_of_round = current_game_state.player_dict[winning_uuid]

    return player_view
