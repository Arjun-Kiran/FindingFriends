from typing import Dict, List
from Game.Views.CardView import card_list_to_dict_list
from Game.Components.GameState import GameState
from Game.Components.Card import Card
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


def game_state_dictionary(current_game_state: GameState) -> Dict:
    return {
        'session': current_game_state.session,
        'current_alpha_player': current_game_state.current_alpha_player,
        'current_friends_of_alpha': current_game_state.current_friends_of_alpha,
        'player_order': current_game_state.player_order,
        'current_player': current_game_state.current_player,
        'leading_player': current_game_state.leading_player,
        'players_and_hand': current_game_state.players_and_hand,
        'players_round_score': current_game_state.players_round_score,
        'players_overall_score': current_game_state.players_overall_score,
        'cards_in_deck': card_list_to_dict_list(current_game_state.cards_in_deck),
        'cards_in_active_pile': card_list_to_dict_list(current_game_state.cards_in_active_pile),
        'card_in_discard_pile': card_list_to_dict_list(current_game_state.card_in_discard_pile),
        'card_out_of_play': card_list_to_dict_list(current_game_state.card_out_of_play),
        'leading_hand_of_subround': card_list_to_dict_list(current_game_state.leading_hand_of_subround),
        'current_hand_played': card_list_to_dict_list(current_game_state.current_hand_played),
        'declare_trump': None,
        'friend_calling_cards': current_game_state.friend_calling_cards,
        'events': current_game_state.events
    }


def convert_player_and_hand_dict(player_and_hand_obj: Dict[str, List[Card]]) -> Dict[str, List[Dict]]:
    return { player_str: card_list_to_dict_list(card_list)  for player_str, card_list in player_and_hand_obj.items()}


def dictionary_to_game_state_object(dictionary_game_state: Dict) -> GameState:
    pass
