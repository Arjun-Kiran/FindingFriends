import pytest
from Game.Components.Card import Card, Rank, Suit
from Game.Systems.DecisionSystem import (
    identical_set_lead_decision,
    sequence_identical_set_lead_decision,
    leading_group_of_top_decision,
    is_check_identical_set_sequence,
    is_an_identical_sequence_set,
    determine_leading_play,
    validate_multi_card_play,
)
from Game.Components.GameState import GameState, DeclareTrump
from Game.Components.Player import Player
from Game.Systems.GameStateSystem import add_player, generate_player


TRUMP = {'rank': Rank.THREE, 'suit': Suit.HEART}


# --- identical_set_lead_decision ---

class TestIdenticalSetDecision:
    def test_higher_pair_wins(self):
        lead = [Card(suit=Suit.CLUB, rank=Rank.JACK), Card(suit=Suit.CLUB, rank=Rank.JACK)]
        winning = lead
        contesting = [Card(suit=Suit.CLUB, rank=Rank.KING), Card(suit=Suit.CLUB, rank=Rank.KING)]
        assert identical_set_lead_decision(TRUMP, lead, winning, contesting) is True

    def test_lower_pair_loses(self):
        lead = [Card(suit=Suit.CLUB, rank=Rank.KING), Card(suit=Suit.CLUB, rank=Rank.KING)]
        winning = lead
        contesting = [Card(suit=Suit.CLUB, rank=Rank.JACK), Card(suit=Suit.CLUB, rank=Rank.JACK)]
        assert identical_set_lead_decision(TRUMP, lead, winning, contesting) is False

    def test_trump_pair_beats_suit_pair(self):
        lead = [Card(suit=Suit.CLUB, rank=Rank.ACE), Card(suit=Suit.CLUB, rank=Rank.ACE)]
        winning = lead
        contesting = [Card(suit=Suit.HEART, rank=Rank.FIVE), Card(suit=Suit.HEART, rank=Rank.FIVE)]
        assert identical_set_lead_decision(TRUMP, lead, winning, contesting) is True

    def test_non_identical_set_cannot_win(self):
        lead = [Card(suit=Suit.CLUB, rank=Rank.JACK), Card(suit=Suit.CLUB, rank=Rank.JACK)]
        winning = lead
        contesting = [Card(suit=Suit.CLUB, rank=Rank.ACE), Card(suit=Suit.CLUB, rank=Rank.KING)]
        assert identical_set_lead_decision(TRUMP, lead, winning, contesting) is False

    def test_wrong_size_cannot_win(self):
        lead = [Card(suit=Suit.CLUB, rank=Rank.JACK), Card(suit=Suit.CLUB, rank=Rank.JACK)]
        winning = lead
        contesting = [Card(suit=Suit.CLUB, rank=Rank.ACE)]
        assert identical_set_lead_decision(TRUMP, lead, winning, contesting) is False


# --- is_check_identical_set_sequence (tractor validation) ---

class TestTractorValidation:
    def test_valid_pair_tractor(self):
        cards = [
            Card(suit=Suit.CLUB, rank=Rank.EIGHT), Card(suit=Suit.CLUB, rank=Rank.EIGHT),
            Card(suit=Suit.CLUB, rank=Rank.SEVEN), Card(suit=Suit.CLUB, rank=Rank.SEVEN),
        ]
        assert is_check_identical_set_sequence(cards, TRUMP) is True

    def test_valid_triple_tractor(self):
        cards = [
            Card(suit=Suit.DIAMOND, rank=Rank.KING), Card(suit=Suit.DIAMOND, rank=Rank.KING), Card(suit=Suit.DIAMOND, rank=Rank.KING),
            Card(suit=Suit.DIAMOND, rank=Rank.QUEEN), Card(suit=Suit.DIAMOND, rank=Rank.QUEEN), Card(suit=Suit.DIAMOND, rank=Rank.QUEEN),
        ]
        assert is_check_identical_set_sequence(cards, TRUMP) is True

    def test_different_suits_invalid(self):
        cards = [
            Card(suit=Suit.CLUB, rank=Rank.EIGHT), Card(suit=Suit.CLUB, rank=Rank.EIGHT),
            Card(suit=Suit.SPADE, rank=Rank.SEVEN), Card(suit=Suit.SPADE, rank=Rank.SEVEN),
        ]
        assert is_check_identical_set_sequence(cards, TRUMP) is False

    def test_non_adjacent_ranks_invalid(self):
        cards = [
            Card(suit=Suit.CLUB, rank=Rank.NINE), Card(suit=Suit.CLUB, rank=Rank.NINE),
            Card(suit=Suit.CLUB, rank=Rank.SEVEN), Card(suit=Suit.CLUB, rank=Rank.SEVEN),
        ]
        assert is_check_identical_set_sequence(cards, TRUMP) is False

    def test_unequal_set_sizes_invalid(self):
        cards = [
            Card(suit=Suit.CLUB, rank=Rank.NINE), Card(suit=Suit.CLUB, rank=Rank.NINE), Card(suit=Suit.CLUB, rank=Rank.NINE),
            Card(suit=Suit.CLUB, rank=Rank.EIGHT), Card(suit=Suit.CLUB, rank=Rank.EIGHT),
        ]
        assert is_check_identical_set_sequence(cards, TRUMP) is False

    def test_trump_rank_in_tractor_invalid(self):
        # Trump rank is THREE, so FOUR-FOUR-THREE-THREE is invalid
        trump = {'rank': Rank.THREE, 'suit': Suit.HEART}
        cards = [
            Card(suit=Suit.CLUB, rank=Rank.FOUR), Card(suit=Suit.CLUB, rank=Rank.FOUR),
            Card(suit=Suit.CLUB, rank=Rank.THREE), Card(suit=Suit.CLUB, rank=Rank.THREE),
        ]
        assert is_check_identical_set_sequence(cards, trump) is False

    def test_skips_trump_rank_for_adjacency(self):
        # Trump rank is FIVE, so SIX-SIX-FOUR-FOUR should be valid (6 and 4 are adjacent)
        trump = {'rank': Rank.FIVE, 'suit': Suit.HEART}
        cards = [
            Card(suit=Suit.SPADE, rank=Rank.SIX), Card(suit=Suit.SPADE, rank=Rank.SIX),
            Card(suit=Suit.SPADE, rank=Rank.FOUR), Card(suit=Suit.SPADE, rank=Rank.FOUR),
        ]
        assert is_check_identical_set_sequence(cards, trump) is True

    def test_alias_works(self):
        cards = [
            Card(suit=Suit.CLUB, rank=Rank.EIGHT), Card(suit=Suit.CLUB, rank=Rank.EIGHT),
            Card(suit=Suit.CLUB, rank=Rank.SEVEN), Card(suit=Suit.CLUB, rank=Rank.SEVEN),
        ]
        assert is_an_identical_sequence_set(cards, TRUMP) is True

    def test_too_few_cards(self):
        cards = [
            Card(suit=Suit.CLUB, rank=Rank.EIGHT), Card(suit=Suit.CLUB, rank=Rank.EIGHT),
        ]
        assert is_check_identical_set_sequence(cards, TRUMP) is False


# --- determine_leading_play ---

class TestDetermineLeadingPlay:
    def test_single_card(self):
        cards = [Card(suit=Suit.CLUB, rank=Rank.ACE)]
        assert determine_leading_play(TRUMP, cards) == 'single'

    def test_identical_set(self):
        cards = [Card(suit=Suit.CLUB, rank=Rank.ACE), Card(suit=Suit.CLUB, rank=Rank.ACE)]
        assert determine_leading_play(TRUMP, cards) == 'identical_set'

    def test_tractor(self):
        cards = [
            Card(suit=Suit.CLUB, rank=Rank.EIGHT), Card(suit=Suit.CLUB, rank=Rank.EIGHT),
            Card(suit=Suit.CLUB, rank=Rank.SEVEN), Card(suit=Suit.CLUB, rank=Rank.SEVEN),
        ]
        assert determine_leading_play(TRUMP, cards) == 'identical_sequence'

    def test_group_of_top(self):
        # A+K of clubs — not identical set, not tractor, but same suit
        cards = [Card(suit=Suit.CLUB, rank=Rank.ACE), Card(suit=Suit.CLUB, rank=Rank.KING)]
        assert determine_leading_play(TRUMP, cards) == 'group_of_top'

    def test_mixed_suits_invalid(self):
        cards = [Card(suit=Suit.CLUB, rank=Rank.ACE), Card(suit=Suit.DIAMOND, rank=Rank.KING)]
        assert determine_leading_play(TRUMP, cards) == 'invalid'


# --- sequence_identical_set_lead_decision ---

class TestSequenceDecision:
    def test_higher_tractor_wins(self):
        lead = [
            Card(suit=Suit.CLUB, rank=Rank.SEVEN), Card(suit=Suit.CLUB, rank=Rank.SEVEN),
            Card(suit=Suit.CLUB, rank=Rank.SIX), Card(suit=Suit.CLUB, rank=Rank.SIX),
        ]
        winning = lead
        contesting = [
            Card(suit=Suit.CLUB, rank=Rank.NINE), Card(suit=Suit.CLUB, rank=Rank.NINE),
            Card(suit=Suit.CLUB, rank=Rank.EIGHT), Card(suit=Suit.CLUB, rank=Rank.EIGHT),
        ]
        assert sequence_identical_set_lead_decision(TRUMP, lead, winning, contesting) is True

    def test_lower_tractor_loses(self):
        lead = [
            Card(suit=Suit.CLUB, rank=Rank.NINE), Card(suit=Suit.CLUB, rank=Rank.NINE),
            Card(suit=Suit.CLUB, rank=Rank.EIGHT), Card(suit=Suit.CLUB, rank=Rank.EIGHT),
        ]
        winning = lead
        contesting = [
            Card(suit=Suit.CLUB, rank=Rank.SEVEN), Card(suit=Suit.CLUB, rank=Rank.SEVEN),
            Card(suit=Suit.CLUB, rank=Rank.SIX), Card(suit=Suit.CLUB, rank=Rank.SIX),
        ]
        assert sequence_identical_set_lead_decision(TRUMP, lead, winning, contesting) is False

    def test_non_tractor_cannot_win(self):
        lead = [
            Card(suit=Suit.CLUB, rank=Rank.SEVEN), Card(suit=Suit.CLUB, rank=Rank.SEVEN),
            Card(suit=Suit.CLUB, rank=Rank.SIX), Card(suit=Suit.CLUB, rank=Rank.SIX),
        ]
        winning = lead
        contesting = [
            Card(suit=Suit.CLUB, rank=Rank.ACE), Card(suit=Suit.CLUB, rank=Rank.ACE),
            Card(suit=Suit.CLUB, rank=Rank.KING), Card(suit=Suit.CLUB, rank=Rank.FIVE),
        ]
        assert sequence_identical_set_lead_decision(TRUMP, lead, winning, contesting) is False
