
from Game.Components.GameState import GameState
from Game.Components.Player import Player
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
