from uuid import uuid4
import pytest
from faker import Faker

from Game.Components.GameState import GameState
from Game.Components.Player import Player
from Game.Systems.GameStateSystem import add_player, add_deck_to_game, clear_players_hand
from Game.Systems.GameStateSystem import deal_to_players


def test_add_player_player_order():
    f = Faker()
    player_1 = Player(name=f.first_name())
    player_2 = Player(name=f.first_name())
    gs = GameState()
    assert len(gs.player_order) == 0
    
    add_player(gs, player_1)
    assert len(gs.player_order) == 1

    add_player(gs, player_2)
    assert len(gs.player_order) == 2


def test_add_player_game_score():
    f = Faker()
    player_1 = Player(name=f.first_name(), uuid=uuid4())
    player_2 = Player(name=f.first_name(), uuid=uuid4())
    gs = GameState()
    add_player(gs, player_1)
    add_player(gs, player_2)
    assert player_1.uuid in gs.players_overall_score
    assert player_2.uuid in gs.players_overall_score

    assert gs.players_overall_score[player_1.uuid] == 0
    assert gs.players_overall_score[player_2.uuid] == 0

    assert player_1.uuid in gs.players_round_score
    assert player_2.uuid in gs.players_round_score

    assert gs.players_round_score[player_1.uuid] == 0
    assert gs.players_round_score[player_2.uuid] == 0


def test_add_player_player_hand():
    f = Faker()
    player_1 = Player(name=f.first_name(), uuid=uuid4())
    player_2 = Player(name=f.first_name(), uuid=uuid4())
    gs = GameState()
    add_player(gs, player_1)
    add_player(gs, player_2)

    assert len(gs.players_and_hand[player_1.uuid]) == 0
    assert len(gs.players_and_hand[player_2.uuid]) == 0     


def test_add_deck_to_game():
    gs = GameState()
    add_deck_to_game(gs, number_of_decks=1)

    assert len(gs.cards_in_deck) == 54

    add_deck_to_game(gs, number_of_decks=5)
    
    assert len(gs.cards_in_deck) == 54*5


def test_deal_to_players():
    number_of_card_in_hand = 5
    f = Faker()
    player_1 = Player(name=f.first_name(), uuid=uuid4())
    player_2 = Player(name=f.first_name(), uuid=uuid4())
    player_3 = Player(name=f.first_name(), uuid=uuid4())
    player_4 = Player(name=f.first_name(), uuid=uuid4())
    gs = GameState()
    add_player(gs, player_1)
    add_player(gs, player_2)
    add_player(gs, player_3)
    add_player(gs, player_4)
    add_deck_to_game(gs)
    deal_to_players(gs,number_of_card_in_hand)

    assert len(gs.players_and_hand[player_1.uuid]) == number_of_card_in_hand
    assert len(gs.players_and_hand[player_2.uuid]) == number_of_card_in_hand
    assert len(gs.players_and_hand[player_3.uuid]) == number_of_card_in_hand
    assert len(gs.players_and_hand[player_4.uuid]) == number_of_card_in_hand


def test_clear_player_hand():
    number_of_card_in_hand = 5
    f = Faker()
    player_1 = Player(name=f.first_name(), uuid=uuid4())
    player_2 = Player(name=f.first_name(), uuid=uuid4())
    gs = GameState()
    add_player(gs, player_1)
    add_player(gs, player_2)
    add_deck_to_game(gs)
    deal_to_players(gs,number_of_card_in_hand)

    assert len(gs.players_and_hand[player_1.uuid]) == number_of_card_in_hand
    assert len(gs.players_and_hand[player_2.uuid]) == number_of_card_in_hand

    clear_players_hand(gs)

    assert len(gs.players_and_hand[player_1.uuid]) == 0
    assert len(gs.players_and_hand[player_2.uuid]) == 0    