from pydantic import BaseModel
from typing import Dict, List, Optional
from Game.Components.GameState import GameState
from Game.Components.Card import Card
from Game.Components.Player import Player
from Game.Views.CardView import card_list_to_emoji_str_list
from Game.Systems.GameStateSystem import find_player, is_player_an_alpha
from Game.Modules.EventEnum import GameEventState


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



def player_view_state(current_game_state: GameState, player_uuid: str) -> PlayerView:
    player_object = current_game_state.player_dict[player_uuid]
    player_view = PlayerView()
    player_view.uuid = str(player_object.uuid)
    player_view.name = str(player_object.name)
    player_view.game_event_state = current_game_state.game_event_state
    player_view.hosting = str(current_game_state.hosting_player.uuid) == str(player_object.uuid)
    player_view.is_alpha = is_player_an_alpha(current_game_state, player_object.uuid)
    player_view.number_of_players = len(current_game_state.player_order)
    player_view.players_round_score = current_game_state.players_round_score
    player_view.players_overall_score = current_game_state.players_overall_score
    player_view.can_start_game = current_game_state.can_start_game
    return player_view
