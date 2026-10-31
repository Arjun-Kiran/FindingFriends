"""A trump tractor may run up the trump strength order into the trump rank.

With Fours trump and Hearts the trump suit, trumps rank: 4♥, then the off-suit
4s (tied), then A♥, K♥, Q♥ ... So 4♥-4♥-4♣-4♣-A♥-A♥ is three neighbouring sets.
Jokers stay out, ordinary suits are unchanged, and the lead check, HR-5 and the
card highlight must all agree.
"""
from Game.Components.Card import Card
from Game.Components.GameState import GameState, DeclareTrump
from Game.Components.Player import Player
from Game.Modules.CardConstants import Rank, Suit
from Game.Systems.DecisionSystem import (
    PlayShape, determine_leading_play, is_check_identical_set_sequence,
    playable_cards, validate_multi_card_play,
)

TRUMP = {'rank': Rank.FOUR, 'suit': Suit.HEART}


def c(rank, suit):
    return Card(rank=rank, suit=suit)


def pair(rank, suit):
    return [c(rank, suit), c(rank, suit)]


def table(hand, lead):
    gs = GameState()
    gs.declare_trump = DeclareTrump(rank=Rank.FOUR, suit=Suit.HEART)
    gs.leading_hand_of_subround = lead
    gs.cards_in_active_pile = list(lead)
    player = Player(name='P')
    gs.players_and_hand[str(player.uuid)] = hand
    gs.player_dict[str(player.uuid)] = player
    return gs, player


USER_EXAMPLE = pair(Rank.FOUR, Suit.HEART) + pair(Rank.FOUR, Suit.CLUB) + pair(Rank.ACE, Suit.HEART)


def test_user_example_is_a_tractor_and_a_valid_lead():
    assert is_check_identical_set_sequence(USER_EXAMPLE, TRUMP)
    assert determine_leading_play(TRUMP, USER_EXAMPLE) == PlayShape.IDENTICAL_SEQUENCE
    gs, player = table(list(USER_EXAMPLE), [])
    assert validate_multi_card_play(gs, player, USER_EXAMPLE) is True


def test_shorter_runs_through_the_rank():
    assert is_check_identical_set_sequence(pair(Rank.FOUR, Suit.CLUB) + pair(Rank.ACE, Suit.HEART), TRUMP)
    assert is_check_identical_set_sequence(pair(Rank.FOUR, Suit.HEART) + pair(Rank.FOUR, Suit.SPADE), TRUMP)
    assert is_check_identical_set_sequence(pair(Rank.ACE, Suit.HEART) + pair(Rank.KING, Suit.HEART), TRUMP)
    # trump suit skips the trump rank below it: 5♥ and 3♥ are neighbours
    assert is_check_identical_set_sequence(pair(Rank.FIVE, Suit.HEART) + pair(Rank.THREE, Suit.HEART), TRUMP)


def test_nonconsecutive_or_malformed_trump_combinations_refused():
    # A♥ and Q♥ are not neighbours
    assert not is_check_identical_set_sequence(pair(Rank.ACE, Suit.HEART) + pair(Rank.QUEEN, Suit.HEART), TRUMP)
    # 4♥ skipping the off-suit rung
    assert not is_check_identical_set_sequence(pair(Rank.FOUR, Suit.HEART) + pair(Rank.ACE, Suit.HEART), TRUMP)
    # two off-suit 4 sets are tied, not neighbours
    assert not is_check_identical_set_sequence(pair(Rank.FOUR, Suit.CLUB) + pair(Rank.FOUR, Suit.SPADE), TRUMP)
    # different sizes
    assert not is_check_identical_set_sequence(
        pair(Rank.FOUR, Suit.CLUB) + [c(Rank.ACE, Suit.HEART)] * 3, TRUMP)
    # singles are not sets
    assert not is_check_identical_set_sequence([c(Rank.FOUR, Suit.HEART), c(Rank.FOUR, Suit.CLUB),
                                                c(Rank.ACE, Suit.HEART), c(Rank.KING, Suit.HEART)], TRUMP)
    # jokers stay excluded
    assert not is_check_identical_set_sequence(
        pair(Rank.ACE, Suit.HEART) + [c(Rank.JOKER, Suit.SMALL)] * 2, TRUMP)
    assert not is_check_identical_set_sequence(
        pair(Rank.FOUR, Suit.HEART) + [c(Rank.JOKER, Suit.BIG)] * 2, TRUMP)
    # a trump cannot run with a non-trump
    assert not is_check_identical_set_sequence(pair(Rank.ACE, Suit.HEART) + pair(Rank.ACE, Suit.CLUB), TRUMP)


def test_plain_suit_unchanged():
    assert is_check_identical_set_sequence(pair(Rank.SIX, Suit.CLUB) + pair(Rank.FIVE, Suit.CLUB), TRUMP)
    # skipping the trump rank: 5♣ and 3♣ with Fours trump
    assert is_check_identical_set_sequence(pair(Rank.FIVE, Suit.CLUB) + pair(Rank.THREE, Suit.CLUB), TRUMP)
    assert not is_check_identical_set_sequence(pair(Rank.SIX, Suit.CLUB) + pair(Rank.THREE, Suit.CLUB), TRUMP)


def test_hr5_follower_must_keep_trump_run_through_rank():
    lead = pair(Rank.KING, Suit.HEART) + pair(Rank.QUEEN, Suit.HEART)
    hand = (pair(Rank.FOUR, Suit.HEART) + pair(Rank.FOUR, Suit.CLUB) + pair(Rank.TWO, Suit.HEART)
            + pair(Rank.NINE, Suit.HEART))
    gs, player = table(hand, lead)
    # 4♥ beside off-suit 4s is a link: owed over 4♥ + 2♥
    assert validate_multi_card_play(gs, player, pair(Rank.FOUR, Suit.HEART) + pair(Rank.FOUR, Suit.CLUB)) is True
    assert validate_multi_card_play(gs, player, pair(Rank.FOUR, Suit.HEART) + pair(Rank.TWO, Suit.HEART)) is False
    assert validate_multi_card_play(gs, player, pair(Rank.TWO, Suit.HEART) + pair(Rank.NINE, Suit.HEART)) is False


def test_highlight_agrees_with_hr5():
    lead = pair(Rank.KING, Suit.HEART) + pair(Rank.QUEEN, Suit.HEART)
    hand = pair(Rank.FOUR, Suit.CLUB) + pair(Rank.ACE, Suit.HEART) + pair(Rank.NINE, Suit.HEART)
    gs, player = table(hand, lead)
    flags = playable_cards(gs, hand)
    lit = [(card.rank, card.suit) for card, ok in zip(hand, flags) if ok]
    assert sorted(lit, key=lambda t: t[0].value) == sorted(
        [(Rank.FOUR, Suit.CLUB)] * 2 + [(Rank.ACE, Suit.HEART)] * 2, key=lambda t: t[0].value)
    assert validate_multi_card_play(gs, player, pair(Rank.FOUR, Suit.CLUB) + pair(Rank.ACE, Suit.HEART)) is True
    assert validate_multi_card_play(gs, player, pair(Rank.ACE, Suit.HEART) + pair(Rank.NINE, Suit.HEART)) is False
