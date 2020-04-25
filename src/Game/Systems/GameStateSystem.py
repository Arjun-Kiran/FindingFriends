from src.Game.Components import Card, GameState, Player
from src.Game.Modules import CardConstants


def add_player_to_game(game_state: GameState, new_player: Player):
    game_state.player_map[new_player.name] = new_player