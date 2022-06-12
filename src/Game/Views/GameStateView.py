from Game.Components.GameState import GameState
from Game.Components.Card import Card, card_list_to_str_list
from Game.Components.Player import Player


def game_state_str(current_game_state: GameState) -> str:
    output = '''
    Session Id: {session_id}
    Current Alpha: {current_alpha}
    Player List: {player_list}
    Player Score: {player_score}
    Player Overall Score: {player_overall_score}
    Number Of Cards In Deck: {num_in_deck}
    '''.format(session_id = current_game_state.session,
               current_alpha = current_game_state.current_alpha_player,
               player_list = current_game_state.player_order,
               player_score = current_game_state.players_round_score,
               player_overall_score = current_game_state.players_overall_score,
               num_in_deck = len(current_game_state.cards_in_deck)
               )

    return output
