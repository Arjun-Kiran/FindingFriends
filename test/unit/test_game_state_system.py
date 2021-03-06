import pytest
from unittest.mock import patch, MagicMock
from src.Game.Components.GameState import GameState
from src.Game.Components.Player import Player
from src.Game.Systems.GameStateSystem import add_player_to_game, add_deck_to_game, deal_to_players


def test_game_state_system_1():
    """
    Testing system function `add_player_to_game`
    I expect the GameState() to add a player to player_map attribute
    :return:
    """
    test_game_state = GameState()
    player_1 = Player(name="Player_1")
    player_2 = Player(name="Player_2")
    add_player_to_game(test_game_state, player_1)
    assert player_1.uuid in test_game_state.player_map.keys()

    add_player_to_game(test_game_state, player_2)
    assert player_1.uuid in test_game_state.player_map.keys()
    assert player_2.uuid in test_game_state.player_map.keys()


def test_game_state_system_2():
    """
    Testing the system function `add_deck_to_game`
    I expect the GameState() should have 54 cards in the deck
    :return:
    """
    test_game_state = GameState()
    add_deck_to_game(test_game_state)
    assert len(test_game_state.deck)/54 == 1


def test_game_state_system_3():
    test_game_state = GameState()
    add_deck_to_game(test_game_state, number_of_decks=4)
    assert len(test_game_state.deck)/54 == 4


def test_game_state_system_4():
    test_game_state = GameState()
    player_1 = Player(name="Player_1")
    player_2 = Player(name="Player_2")
    player_3 = Player(name="Player_3")
    player_4 = Player(name="Player_4")
    add_player_to_game(test_game_state, player_1)
    add_player_to_game(test_game_state, player_2)
    add_player_to_game(test_game_state, player_3)
    add_player_to_game(test_game_state, player_4)
    add_deck_to_game(test_game_state)
    deal_to_players(test_game_state, cards_per_person=5)
    assert len(player_1.hand) == 5 and len(player_2.hand) == 5 and len(player_3.hand) == 5 and len(player_4.hand) == 5
    assert player_1.hand_size == 5 and player_2.hand_size == 5 and player_3.hand_size == 5 and player_4.hand_size == 5


def test_game_state_system_5():
    test_game_state = GameState()
    player_1 = Player(name="Player_1")
    player_2 = Player(name="Player_2")
    player_3 = Player(name="Player_3")
    player_4 = Player(name="Player_4")

    add_player_to_game(test_game_state, player_1)
    add_player_to_game(test_game_state, player_2)
    add_player_to_game(test_game_state, player_3)
    add_player_to_game(test_game_state, player_4)

    add_deck_to_game(test_game_state)
    deal_to_players(test_game_state, cards_per_person=5)
    assert len(test_game_state.deck) == 54 - (5*4)
    assert test_game_state.deck_size == 54 - (5*4)


def test_game_state_system_6():
    test_game_state = GameState()
    add_deck_to_game(test_game_state)
    assert test_game_state.deck_size == len(test_game_state.deck)


def test_game_state_system_7():
    test_game_state = GameState()
    add_deck_to_game(test_game_state, number_of_decks=5)
    assert test_game_state.deck_size == len(test_game_state.deck)




