from src.Game.Components.Card import Card
from src.Game.Components.GameState import GameState
from src.Game.Components.Player import Player
from src.Game.Systems.DeckSystem import build_deck, shuffle_deck
from src.Game.Modules import CardConstants


def add_player_to_game(game_state: GameState, new_player: Player):
    game_state.player_map[new_player.name] = new_player


def add_deck_to_game(game_state: GameState, number_of_decks: int = 1):
    game_state.deck.extend(build_deck(number_of_decks=number_of_decks))
    shuffle_deck(game_state.deck)


def deal_to_players(game_state: GameState, cards_per_person: int = 5):
    for _ in range(cards_per_person):
        for idx, name, player in enumerate(game_state.player_map):
            player.hand.append(game_state.deck.pop())
