
import pytest
from unittest.mock import patch, MagicMock

from src.Game.Systems.DeckSystem import build_a_deck, build_deck


def test_deck_system_tc_1():
    assert len(build_a_deck()) == 54


def test_deck_system_tc_2():
    assert len(build_deck(1)) == 54
    assert len(build_deck(2)) == 54*2
    assert len(build_deck(3)) == 54*3
    assert len(build_deck(4)) == 54*4
