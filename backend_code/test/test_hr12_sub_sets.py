"""HR-12: a set you cannot match is answered with the biggest sets you hold.

Against a led triple, a player with no triple but a pair in the suit plays the
pair and fills the rest; against a set of four, failing a triple, as many
pairs as fit; and the same against a tractor of triples. The traditional rules
only owe matching sets, so all of these were free choices before.

Hearts trump, Twos the trump rank, throughout.
"""
from collections import Counter
from itertools import combinations

import pytest

from Game.Components.Card import Card
from Game.Components.GameState import DeclareTrump, GameState
from Game.Modules.CardConstants import Rank, Suit
from Game.Systems.DecisionSystem import (explain_illegal_play, playable_cards,
                                         validate_multi_card_play)
from Game.Systems.GameStateSystem import add_player, generate_player


def c(rank, suit):
    return Card(rank=rank, suit=suit)


def clubs(*ranks):
    return [c(rank, Suit.CLUB) for rank in ranks]


R = Rank
TRIPLE = clubs(R.TEN, R.TEN, R.TEN)
FOUR = clubs(R.TEN, R.TEN, R.TEN, R.TEN)
TRIPLE_TRACTOR = clubs(R.TEN, R.TEN, R.TEN, R.NINE, R.NINE, R.NINE)


def _table(hand, leading):
    gs = GameState()
    players = [generate_player(f'p{i}') for i in range(5)]
    for player in players:
        add_player(gs, player)
    me = players[1]
    gs.declare_trump = DeclareTrump(rank=Rank.TWO, suit=Suit.HEART)
    gs.players_and_hand[str(me.uuid)] = list(hand)
    gs.leading_hand_of_subround = list(leading)
    return gs, me


def _why(hand, leading, played):
    gs, me = _table(hand, leading)
    reason = explain_illegal_play(gs, me, played)
    # The older validator must never disagree with the one that refuses plays.
    assert validate_multi_card_play(gs, me, played) == (reason is None), reason
    return reason


def _legal(hand, leading, played):
    return _why(hand, leading, played) is None


# --- the scenarios ---

@pytest.mark.unit
def test_failing_a_triple_the_pair_goes_in():
    """The rule as asked for: no triple, so ♣8♣8 plus one more club."""
    hand = clubs(R.EIGHT, R.EIGHT, R.FIVE, R.KING) + [c(R.ACE, Suit.SPADE)]

    assert _legal(hand, TRIPLE, clubs(R.EIGHT, R.EIGHT, R.FIVE))
    assert _legal(hand, TRIPLE, clubs(R.EIGHT, R.EIGHT, R.KING))
    reason = _why(hand, TRIPLE, clubs(R.KING, R.FIVE, R.EIGHT))
    assert reason is not None
    assert 'A triple was led' in reason and 'a pair' in reason


@pytest.mark.unit
def test_with_two_pairs_either_will_do():
    hand = clubs(R.EIGHT, R.EIGHT, R.FIVE, R.FIVE, R.THREE)

    assert _legal(hand, TRIPLE, clubs(R.EIGHT, R.EIGHT, R.THREE))
    assert _legal(hand, TRIPLE, clubs(R.FIVE, R.FIVE, R.EIGHT))
    reason = _why(hand, TRIPLE, clubs(R.EIGHT, R.FIVE, R.THREE))
    assert ' or ' in reason, 'both pairs are named as the choice'


@pytest.mark.unit
def test_a_pair_and_nothing_else_in_the_suit_fills_from_anywhere():
    hand = clubs(R.EIGHT, R.EIGHT) + [c(R.ACE, Suit.SPADE), c(R.KING, Suit.SPADE)]

    assert _legal(hand, TRIPLE, clubs(R.EIGHT, R.EIGHT) + [c(R.ACE, Suit.SPADE)])


@pytest.mark.unit
def test_no_pairs_leaves_the_choice_free():
    hand = clubs(R.KING, R.FIVE, R.THREE, R.FOUR)

    assert _legal(hand, TRIPLE, clubs(R.KING, R.FIVE, R.THREE))
    assert _legal(hand, TRIPLE, clubs(R.FOUR, R.FIVE, R.THREE))


@pytest.mark.unit
def test_a_matching_triple_is_still_owed_first():
    hand = clubs(R.EIGHT, R.EIGHT, R.EIGHT, R.FIVE)

    assert _legal(hand, TRIPLE, clubs(R.EIGHT, R.EIGHT, R.EIGHT))
    assert not _legal(hand, TRIPLE, clubs(R.EIGHT, R.EIGHT, R.FIVE))


@pytest.mark.unit
def test_a_pair_of_the_trump_rank_is_a_pair_of_trumps():
    """♠2 is a trump with Twos trump, so ♠2♠2 is the pair owed to a trump triple."""
    lead = [c(R.SEVEN, Suit.HEART)] * 3
    hand = [c(R.TWO, Suit.SPADE), c(R.TWO, Suit.SPADE),
            c(R.FOUR, Suit.HEART), c(R.NINE, Suit.HEART)]

    assert _legal(hand, lead, [c(R.TWO, Suit.SPADE), c(R.TWO, Suit.SPADE), c(R.FOUR, Suit.HEART)])
    assert not _legal(hand, lead, [c(R.FOUR, Suit.HEART), c(R.NINE, Suit.HEART), c(R.TWO, Suit.SPADE)])


@pytest.mark.unit
def test_a_pair_of_jokers_is_owed_like_any_other_pair():
    lead = [c(R.SEVEN, Suit.HEART)] * 3
    hand = [c(R.JOKER, Suit.BIG), c(R.JOKER, Suit.BIG),
            c(R.NINE, Suit.HEART), c(R.FOUR, Suit.HEART)]

    assert _legal(hand, lead, [c(R.JOKER, Suit.BIG), c(R.JOKER, Suit.BIG), c(R.FOUR, Suit.HEART)])
    assert not _legal(hand, lead, [c(R.JOKER, Suit.BIG), c(R.NINE, Suit.HEART), c(R.FOUR, Suit.HEART)])


@pytest.mark.unit
def test_against_four_a_triple_then_a_single():
    """The pair does not fit in the one slot the triple leaves."""
    hand = clubs(R.EIGHT, R.EIGHT, R.EIGHT, R.FIVE, R.FIVE)

    assert _legal(hand, FOUR, clubs(R.EIGHT, R.EIGHT, R.EIGHT, R.FIVE))
    reason = _why(hand, FOUR, clubs(R.EIGHT, R.EIGHT, R.FIVE, R.FIVE))
    assert 'a triple' in reason


@pytest.mark.unit
def test_against_four_two_pairs_both_go_in():
    hand = clubs(R.EIGHT, R.EIGHT, R.FIVE, R.FIVE, R.THREE)

    assert _legal(hand, FOUR, clubs(R.EIGHT, R.EIGHT, R.FIVE, R.FIVE))
    reason = _why(hand, FOUR, clubs(R.EIGHT, R.EIGHT, R.FIVE, R.THREE))
    assert 'two pairs' in reason


@pytest.mark.unit
def test_against_four_one_pair_and_any_two_more():
    hand = clubs(R.EIGHT, R.EIGHT, R.FIVE, R.THREE, R.KING)

    assert _legal(hand, FOUR, clubs(R.EIGHT, R.EIGHT, R.FIVE, R.KING))
    assert not _legal(hand, FOUR, clubs(R.EIGHT, R.FIVE, R.THREE, R.KING))


@pytest.mark.unit
def test_a_tractor_of_triples_is_answered_with_the_pairs_held():
    hand = clubs(R.EIGHT, R.EIGHT, R.SEVEN, R.SEVEN, R.THREE, R.KING, R.FOUR)

    assert _legal(hand, TRIPLE_TRACTOR, clubs(R.EIGHT, R.EIGHT, R.SEVEN, R.SEVEN, R.THREE, R.KING))
    reason = _why(hand, TRIPLE_TRACTOR, clubs(R.EIGHT, R.EIGHT, R.SEVEN, R.THREE, R.KING, R.FOUR))
    assert reason.startswith('A tractor was led')


@pytest.mark.unit
def test_a_tractor_of_triples_takes_the_triple_then_the_pair():
    hand = clubs(R.EIGHT, R.EIGHT, R.EIGHT, R.FIVE, R.FIVE, R.THREE, R.FOUR)

    assert _legal(hand, TRIPLE_TRACTOR, clubs(R.EIGHT, R.EIGHT, R.EIGHT, R.FIVE, R.FIVE, R.THREE))
    assert not _legal(hand, TRIPLE_TRACTOR, clubs(R.EIGHT, R.EIGHT, R.EIGHT, R.FIVE, R.THREE, R.FOUR))


@pytest.mark.unit
def test_a_led_pair_is_untouched():
    """Nothing smaller than a pair but single cards, which are only filler."""
    hand = clubs(R.EIGHT, R.FIVE, R.THREE)

    assert _legal(hand, clubs(R.TEN, R.TEN), clubs(R.FIVE, R.THREE))


@pytest.mark.unit
def test_short_of_the_suit_every_club_goes_in_as_before():
    hand = clubs(R.EIGHT, R.EIGHT) + [c(R.ACE, Suit.SPADE), c(R.KING, Suit.DIAMOND)]

    assert _legal(hand, FOUR, clubs(R.EIGHT, R.EIGHT) + [c(R.ACE, Suit.SPADE), c(R.KING, Suit.DIAMOND)])


# --- the hand highlighting agrees with the rule ---

def _kind(card):
    return card.rank.value, card.suit.value


HANDS = [
    (TRIPLE, clubs(R.EIGHT, R.EIGHT, R.FIVE, R.KING) + [c(R.ACE, Suit.SPADE)]),
    (TRIPLE, clubs(R.EIGHT, R.EIGHT, R.FIVE, R.FIVE, R.THREE)),
    (FOUR, clubs(R.EIGHT, R.EIGHT, R.EIGHT, R.FIVE, R.FIVE)),
    (FOUR, clubs(R.EIGHT, R.EIGHT, R.FIVE, R.FIVE, R.THREE)),
    (FOUR, clubs(R.EIGHT, R.EIGHT, R.FIVE, R.THREE, R.KING)),
    (TRIPLE_TRACTOR, clubs(R.EIGHT, R.EIGHT, R.SEVEN, R.SEVEN, R.THREE, R.KING, R.FOUR)),
    (TRIPLE_TRACTOR, clubs(R.EIGHT, R.EIGHT, R.EIGHT, R.FIVE, R.FIVE, R.THREE, R.FOUR)),
]


@pytest.mark.unit
@pytest.mark.parametrize('lead, hand', HANDS)
def test_a_card_is_lit_exactly_when_some_legal_play_uses_it(lead, hand):
    """Every play is tried. Of each kind of card, as many copies are lit as
    the most any one legal play uses — never a play the server refuses, nor a
    card it would take hidden. Identical cards are interchangeable, so one of
    a pair lit means "one of these", as everywhere else in the hint."""
    gs, me = _table(hand, lead)
    most = Counter()
    for chosen in combinations(range(len(hand)), len(lead)):
        played = [hand[i] for i in chosen]
        if explain_illegal_play(gs, me, played) is None:
            for kind, n in Counter(_kind(card) for card in played).items():
                most[kind] = max(most[kind], n)

    lit = Counter(_kind(card) for card, on in zip(hand, playable_cards(gs, hand)) if on)

    assert lit == most


@pytest.mark.unit
def test_two_pairs_against_four_leave_the_loose_club_dark():
    hand = clubs(R.EIGHT, R.EIGHT, R.FIVE, R.FIVE, R.THREE)
    gs, _ = _table(hand, FOUR)

    assert playable_cards(gs, hand) == [True, True, True, True, False]
