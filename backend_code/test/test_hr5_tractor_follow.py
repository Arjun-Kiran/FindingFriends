"""HR-5: a tractor led must be answered with a tractor, if you hold one.

ZhaoPengyou_Rules.md lets a follower answer a tractor with any sets of the
right size — "any sets of the right size will do". HouseRules.md HR-5 overrides
that and adopts the Forced sub-patterns variation instead: what runs together
in your hand, you have to keep together.

The rule is built on links — one link is one neighbouring pair of ranks among
the sets you play — so these check the two halves separately: that a player who
holds a run is made to play it, and that a player who holds none keeps every bit
of the choice the traditional rules give them.
"""
import pytest

from Game.Components.Card import Card
from Game.Components.GameState import GameState, DeclareTrump
from Game.Components.Player import Player
from Game.Modules.CardConstants import Rank, Suit
from Game.Systems.DecisionSystem import (
    explain_illegal_play, playable_cards, validate_multi_card_play,
)


def _club(rank):
    return Card(rank=rank, suit=Suit.CLUB)


def _pairs(*ranks):
    return [_club(rank) for rank in ranks for _ in range(2)]


def _table(hand, lead, trump_rank=Rank.TWO, trump_suit=Suit.HEART):
    """A follower holding `hand`, facing `lead`, ready to be asked."""
    game_state = GameState()
    game_state.declare_trump = DeclareTrump(rank=trump_rank, suit=trump_suit)
    game_state.leading_hand_of_subround = lead
    game_state.cards_in_active_pile = list(lead)
    player = Player(name='Follower')
    game_state.players_and_hand[str(player.uuid)] = hand
    game_state.player_dict[str(player.uuid)] = player
    return game_state, player


def _allowed(hand, lead, play, **trump):
    game_state, player = _table(hand, lead, **trump)
    return validate_multi_card_play(game_state, player, play)


# Ten-ten-nine-nine: the lead from the game this rule came out of.
TRACTOR_LEAD = _pairs(Rank.TEN, Rank.NINE)


@pytest.mark.unit
def test_a_run_in_hand_has_to_be_played():
    """The table that prompted the rule: 8-8 and 5-5 answered a led tractor
    while 5-5 and 4-4 sat in the same hand."""
    hand = _pairs(Rank.EIGHT, Rank.FIVE, Rank.FOUR)

    assert not _allowed(hand, TRACTOR_LEAD, _pairs(Rank.EIGHT, Rank.FIVE))


@pytest.mark.unit
def test_and_playing_it_is_accepted():
    hand = _pairs(Rank.EIGHT, Rank.FIVE, Rank.FOUR)

    assert _allowed(hand, TRACTOR_LEAD, _pairs(Rank.FIVE, Rank.FOUR))


@pytest.mark.unit
def test_the_refusal_names_the_cards_that_run_together():
    """A player who missed the tractor is not helped by being told to play it.
    They have to be told which cards it is."""
    game_state, player = _table(_pairs(Rank.EIGHT, Rank.FIVE, Rank.FOUR), TRACTOR_LEAD)

    reason = explain_illegal_play(game_state, player, _pairs(Rank.EIGHT, Rank.FIVE))

    assert '5-5 and 4-4' in reason


@pytest.mark.unit
def test_pairs_that_run_nowhere_keep_the_free_choice():
    """HR-5 only takes away a choice the player had a run to make. Holding
    three pairs that touch nothing, any two of them still answer the lead."""
    hand = _pairs(Rank.KING, Rank.EIGHT, Rank.SIX)

    assert _allowed(hand, TRACTOR_LEAD, _pairs(Rank.KING, Rank.EIGHT))
    assert _allowed(hand, TRACTOR_LEAD, _pairs(Rank.EIGHT, Rank.SIX))


@pytest.mark.unit
def test_a_run_you_could_not_make_is_not_owed():
    """Two pairs held and two owed: there is no choice to constrain, and the
    rule must not refuse the only play the player has."""
    hand = _pairs(Rank.KING, Rank.EIGHT)

    assert _allowed(hand, TRACTOR_LEAD, _pairs(Rank.KING, Rank.EIGHT))


@pytest.mark.unit
def test_adjacency_steps_over_the_trump_rank():
    """Sixes and fours are neighbours when fives are trump, so 6-6 and 4-4 is
    a run and has to be kept together like any other."""
    hand = _pairs(Rank.KING, Rank.SIX, Rank.FOUR)

    assert not _allowed(hand, TRACTOR_LEAD, _pairs(Rank.KING, Rank.SIX),
                        trump_rank=Rank.FIVE)
    assert _allowed(hand, TRACTOR_LEAD, _pairs(Rank.SIX, Rank.FOUR),
                    trump_rank=Rank.FIVE)


@pytest.mark.unit
def test_a_pair_of_the_trump_rank_is_a_pair_but_never_a_run():
    """The trump rank is barred from a tractor, so holding it beside a
    neighbour builds nothing the player can be made to keep."""
    # Fives trump: 5-5 are trumps, not clubs, so the club pairs stand alone.
    hand = _pairs(Rank.KING, Rank.SIX)

    assert _allowed(hand, TRACTOR_LEAD, _pairs(Rank.KING, Rank.SIX),
                    trump_rank=Rank.FIVE)


@pytest.mark.unit
def test_the_longest_run_wins_over_a_shorter_one():
    """Three pairs owed. A three-rank run holds two links and any other choice
    holds one, so the run is what the hand owes."""
    lead = _pairs(Rank.KING, Rank.QUEEN, Rank.JACK)
    hand = _pairs(Rank.NINE, Rank.EIGHT, Rank.SEVEN, Rank.FOUR)

    assert not _allowed(hand, lead, _pairs(Rank.NINE, Rank.EIGHT, Rank.FOUR))
    assert _allowed(hand, lead, _pairs(Rank.NINE, Rank.EIGHT, Rank.SEVEN))


@pytest.mark.unit
def test_one_link_is_all_that_is_owed_when_that_is_all_there_is():
    """Two separate runs and three sets owed: the player keeps one run whole
    and is free with the third set, because two links cannot be had."""
    lead = _pairs(Rank.KING, Rank.QUEEN, Rank.JACK)
    hand = _pairs(Rank.NINE, Rank.EIGHT, Rank.FIVE, Rank.FOUR)

    # Either run kept is enough, and which one is the player's business.
    assert _allowed(hand, lead, _pairs(Rank.NINE, Rank.EIGHT, Rank.FIVE))
    assert _allowed(hand, lead, _pairs(Rank.FIVE, Rank.FOUR, Rank.NINE))
    # Breaking both is not a play that exists here: drop any one of these four
    # ranks and a run still survives among the three that are left. The rule
    # never asks for more than the hand can give, and here it cannot be cheated
    # either.


@pytest.mark.unit
def test_a_plain_pair_lead_is_untouched():
    """HR-5 is about sequences. One pair led owes one pair and nothing more."""
    lead = _pairs(Rank.TEN)
    hand = _pairs(Rank.EIGHT, Rank.FIVE, Rank.FOUR)

    assert _allowed(hand, lead, _pairs(Rank.EIGHT))


@pytest.mark.unit
def test_the_hint_stops_offering_cards_the_rule_forbids():
    """The highlight in a player's hand has to agree with what the server will
    accept, or it invites exactly the play that gets refused."""
    hand = _pairs(Rank.EIGHT, Rank.FIVE, Rank.FOUR)
    game_state, player = _table(hand, TRACTOR_LEAD)

    playable = playable_cards(game_state, hand)

    by_rank = {card.rank: ok for card, ok in zip(hand, playable)}
    assert by_rank[Rank.FIVE] is True
    assert by_rank[Rank.FOUR] is True
    assert by_rank[Rank.EIGHT] is False
