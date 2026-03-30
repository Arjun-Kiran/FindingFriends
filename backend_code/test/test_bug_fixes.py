import pytest
from uuid import uuid4
from Game.Systems.DeckSystem import number_of_decks
from Game.Components.Player import PlayerPointer


@pytest.mark.unit
def test_number_of_decks_5_players():
    assert number_of_decks(5) == 2


@pytest.mark.unit
def test_number_of_decks_8_players():
    assert number_of_decks(8) == 3


@pytest.mark.unit
def test_number_of_decks_11_players():
    assert number_of_decks(11) == 3


@pytest.mark.unit
def test_number_of_decks_12_players():
    assert number_of_decks(12) == 4


@pytest.mark.unit
def test_number_of_decks_too_few():
    with pytest.raises(Exception):
        number_of_decks(4)


@pytest.mark.unit
def test_number_of_decks_too_many():
    with pytest.raises(Exception):
        number_of_decks(13)


@pytest.mark.unit
def test_player_pointer_valid_uuid():
    test_uuid = str(uuid4())
    pp = PlayerPointer(index=0, player_uuid=test_uuid)
    assert pp.player_uuid == test_uuid


@pytest.mark.unit
def test_player_pointer_empty_uuid():
    pp = PlayerPointer(index=0, player_uuid='')
    assert pp.player_uuid == ''
