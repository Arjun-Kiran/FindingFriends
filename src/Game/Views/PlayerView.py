from Game.Components.GameState import GameState
from Game.Views.CardView import card_list_to_str_list
from Game.Systems.GameStateSystem import find_player


def player_view_state_str(current_game_state: GameState, player_uuid: str) -> str:
    _ , player_object = find_player(current_game_state, player_uuid)
    hand_list_str = card_list_to_str_list(current_game_state.players_and_hand[player_uuid])

    return '''
    Player View
    ------------------
    Player Name: {player_name}
    Player UUID: {player_uuid}
    Player Overall Score: {player_overall_score}
    Player Round Score: {player_round_score}
    Number Of Cards In Deck: {num_in_deck}
    Player Hand: {player_hand}
    '''.format(player_name=player_object.name,
             player_uuid = player_object.uuid,
             player_overall_score = current_game_state.players_overall_score[player_uuid],
             player_round_score = current_game_state.players_round_score[player_uuid],
             player_hand = hand_list_str,
             num_in_deck = len(current_game_state.cards_in_deck))
