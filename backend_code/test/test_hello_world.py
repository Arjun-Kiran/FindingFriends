from Game.Components.Card import Card
from Game.Modules.CardConstants import Suit, Rank


def test_hello_world():
    assert 1 == 1

def test_card_init():
    c1 = Card(suit=Suit.DIAMOND, rank=Rank.ACE)
    c2 = Card(suit=Suit.DIAMOND, rank=Rank.ACE)
    assert c1 == c2
