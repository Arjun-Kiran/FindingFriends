import copy
import pytest
from unittest.mock import patch, MagicMock

from src.Game.Systems.DeckSystem import build_a_deck, build_deck, shuffle_deck


def test_deck_system_tc_1():
    assert len(build_a_deck()) == 54


def test_deck_system_tc_2():
    assert len(build_deck(1)) == 54
    assert len(build_deck(2)) == 54*2
    assert len(build_deck(3)) == 54*3
    assert len(build_deck(4)) == 54*4


def test_deck_system_tc_3():
    deck = build_deck(1)
    copy_deck = copy.deepcopy(deck)
    shuffle_deck(deck)
    assert deck[0] != copy_deck[0] \
           or deck[1] != copy_deck[1] \
           or deck[2] != copy_deck[2] \
           or deck[3] != copy_deck[3] \
           or deck[4] != copy_deck[4] \
           or deck[5] != copy_deck[5]


