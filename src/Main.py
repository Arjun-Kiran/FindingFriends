from uuid import uuid4
from Game.Components.GameState import GameState, game_state_str, player_view_state_str
from Game.Components.GameState import number_of_players
from Game.Components.Player import Player
from Game.Systems.GameStateSystem import add_player, add_deck_to_game, deal_to_players



if __name__ == '__main__':
    gs = GameState()
    player_1 = Player(name='Arjuku', uuid=str(uuid4()))
    add_player(gs, player_1)
    player_2 = Player(name='Johnny', uuid=str(uuid4()))
    add_player(gs, player_2)
    add_deck_to_game(gs, number_of_decks=5)
    print(game_state_str(gs))
    print(player_view_state_str(gs, player_1.uuid))
    deal_to_players(gs, 2)
    print(player_view_state_str(gs, player_2.uuid))


