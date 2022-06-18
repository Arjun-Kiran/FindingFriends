
from typing import Tuple
from Game.Components.GameState import GameState
from Game.Components.Player import Player
from Game.Modules.CardConstants import Suit, Rank
from Game.Systems.DeckSystem import build_deck, shuffle_deck


def add_player(current_game_state: GameState, joining_player: Player):
    print(f'Adding user: {joining_player.name}')
    current_game_state.player_order.append(joining_player)
    current_game_state.players_round_score[joining_player.uuid] = 0
    current_game_state.players_overall_score[joining_player.uuid] = 0
    current_game_state.players_and_hand[joining_player.uuid] = list()


def add_deck_to_game(game_state: GameState, number_of_decks: int = 1):
    clear_deck(game_state)
    game_state.cards_in_deck.extend(build_deck(number_of_decks=number_of_decks))
    shuffle_deck(game_state.cards_in_deck)


def clear_deck(game_state: GameState):
    game_state.cards_in_deck = list()


def clear_players_hand(game_state: GameState):
    for player_uuid in game_state.players_and_hand:
        game_state.players_and_hand[player_uuid] = list()


def deal_to_players(game_state: GameState, cards_per_person: int = 5):
    for _ in range(cards_per_person):
        for player_uuid in game_state.players_and_hand:
            game_state.players_and_hand[player_uuid].append(game_state.cards_in_deck.pop())


def find_player(current_game_state: GameState, player_uuid: str) -> Tuple[int, Player]:
    for idx, p in enumerate(current_game_state.player_order):
        if p.uuid == player_uuid:
            return idx, p
    else:
        raise Exception("Can't fine Player with UUID: {}".format(player_uuid))


def set_player_as_alpha(current_game_state: GameState, player_uuid: str):
    _ , check_player = find_player(current_game_state, player_uuid)
    current_game_state.current_alpha_player = check_player.uuid


def set_player_as_leading_player(current_game_state: GameState, player_uuid: str):
    player_idx, check_player = find_player(current_game_state, player_uuid)
    current_game_state.leading_player['player_uuid'] = check_player.uuid
    current_game_state.leading_player['index'] = current_game_state.current_player['index'] = player_idx


def set_game_state_trump(current_gs: GameState, new_trump_suit: Suit, new_trump_rank: Rank):
    current_gs.declare_trump_rank = new_trump_rank
    current_gs.declare_trump_suite = new_trump_suit


def next_person_turn(current_gs: GameState) -> Tuple[bool, Player]:
    number_of_players = len(current_gs.player_order)
    current_gs.current_player['index'] += 1
    if number_of_players == current_gs.current_player['index']:
        current_gs.current_player['index'] = 0
    continue_round = current_gs.leading_player['index'] != current_gs.current_player['index']
    return continue_round, current_gs.player_order[current_gs.current_player['index']]
