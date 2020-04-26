
from src.Game.Components.GameState import GameState
from src.Game.Components.Player import Player
from src.Game.Systems.DeckSystem import build_deck, shuffle_deck


def add_player_to_game(game_state: GameState, new_player: Player):
    game_state.player_map[new_player.uuid] = new_player
    game_state.score_map.update({new_player.uuid: 0})
    game_state.player_cards_played.update({new_player.uuid: list()})
    game_state.player_order.append(new_player.uuid)


def add_deck_to_game(game_state: GameState, number_of_decks: int = 1):
    game_state.deck.extend(build_deck(number_of_decks=number_of_decks))
    shuffle_deck(game_state.deck)


def deal_to_players(game_state: GameState, cards_per_person: int = 5):
    for _ in range(cards_per_person):
        for uuid, player in game_state.player_map.items():
            player.hand.append(game_state.deck.pop())
