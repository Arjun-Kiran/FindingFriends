import copy
from Game.Systems.DeckSystem import build_a_deck
from Game.Systems.DeckSystem import build_deck
from Game.Systems.DeckSystem import shuffle_deck


def test_build_a_deck():
    deck = build_a_deck()
    no_dup_deck = list()
    assert len(deck) == 54
    for c in deck:
        if c not in no_dup_deck:
            no_dup_deck.append(c)
        else:
            raise Exception("Found duplicate: {}".format(c))


def test_build_deck():
    one_deck = build_deck(1)
    two_decks = build_deck(2)
    three_decks = build_deck(3)
    four_decks = build_deck(4)

    assert len(one_deck) == 54
    assert len(two_decks) == 2*54
    assert len(three_decks) == 3*54
    assert len(four_decks) == 4*54
    

def test_shuffle_deck():
    deck = build_a_deck()
    shuffled_deck = copy.deepcopy(deck)
    shuffled_deck = shuffle_deck(shuffled_deck)

    first_four = (deck[0], deck[1], deck[2], deck[3])
    first_four_unshuffled = (shuffled_deck[0], shuffled_deck[1], shuffled_deck[2], shuffled_deck[3])

    assert first_four != first_four_unshuffled
