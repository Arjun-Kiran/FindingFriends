"""The trick engine, checked against ZhaoPengyou_Rules.md.

Each test names the rule it comes from. The worked examples in the rules
document are reproduced verbatim where they exist, because they are the
clearest statement of what the engine is supposed to do.
"""
import pytest

from Game.Components.Card import Card
from Game.Components.GameState import GameState, DeclareTrump
from Game.Modules.CardConstants import Rank, Suit
from Game.Systems.GameStateSystem import add_player, generate_player
from Game.Systems.DecisionSystem import (
    card_value, determine_leading_play, identical_set_lead_decision,
    leading_group_of_top_decision, play_shape, sequence_identical_set_lead_decision,
    single_card_lead_decision, strongest_component_value, validate_multi_card_play,
)


def c(rank, suit):
    return Card(rank=rank, suit=suit)


# Fives and hearts are trumps, as in most of the rules document's examples.
TRUMP = {'rank': Rank.FIVE, 'suit': Suit.HEART}


def _hand_of(cards, leading):
    """A game state where one player holds `cards` and `leading` has been led."""
    gs = GameState()
    players = [generate_player(f'p{i}') for i in range(5)]
    for player in players:
        add_player(gs, player)
    me = players[1]
    gs.declare_trump = DeclareTrump(rank=TRUMP['rank'], suit=TRUMP['suit'])
    gs.players_and_hand[str(me.uuid)] = list(cards)
    gs.leading_hand_of_subround = list(leading)
    return gs, me


# --- "Trumps": the hierarchy table ---

@pytest.mark.unit
def test_the_trump_hierarchy_is_ordered_as_the_rules_list_it():
    """red joker > black joker > trump rank+suit > trump rank > trump suit > rest."""
    trump = {'rank': Rank.EIGHT, 'suit': Suit.DIAMOND}
    descending = [
        c(Rank.JOKER, Suit.BIG), c(Rank.JOKER, Suit.SMALL),
        c(Rank.EIGHT, Suit.DIAMOND), c(Rank.EIGHT, Suit.SPADE),
        c(Rank.ACE, Suit.DIAMOND), c(Rank.TWO, Suit.DIAMOND),
        c(Rank.ACE, Suit.SPADE),
    ]
    values = [card_value(trump, card) for card in descending]
    assert values == sorted(values, reverse=True)


@pytest.mark.unit
def test_trump_rank_cards_of_other_suits_are_all_equal():
    trump = {'rank': Rank.EIGHT, 'suit': Suit.DIAMOND}
    off_suit = [c(Rank.EIGHT, s) for s in (Suit.SPADE, Suit.HEART, Suit.CLUB)]

    assert len({card_value(trump, card) for card in off_suit}) == 1


# --- "Single Card Lead" ---

@pytest.mark.unit
def test_the_highest_card_of_the_led_suit_wins():
    lead = c(Rank.SEVEN, Suit.SPADE)
    assert single_card_lead_decision(TRUMP, lead, lead, c(Rank.ACE, Suit.SPADE))


@pytest.mark.unit
def test_a_discard_cannot_win_however_high():
    lead = c(Rank.SEVEN, Suit.SPADE)
    assert not single_card_lead_decision(TRUMP, lead, lead, c(Rank.ACE, Suit.DIAMOND))


@pytest.mark.unit
def test_any_trump_beats_the_led_suit():
    lead = c(Rank.ACE, Suit.SPADE)
    assert single_card_lead_decision(TRUMP, lead, lead, c(Rank.TWO, Suit.HEART))


@pytest.mark.unit
def test_ties_go_to_the_first_played():
    """'Other cards of the trump rank (all equal - first played wins ties)'."""
    lead = c(Rank.SEVEN, Suit.SPADE)
    winning = c(Rank.FIVE, Suit.SPADE)      # trump rank, played first
    contesting = c(Rank.FIVE, Suit.CLUB)    # trump rank, equal value

    assert not single_card_lead_decision(TRUMP, lead, winning, contesting)


# --- "Leading a Set of Identical Cards" ---

@pytest.mark.unit
def test_a_higher_pair_of_the_led_suit_wins():
    lead = [c(Rank.JACK, Suit.SPADE)] * 2
    assert identical_set_lead_decision(TRUMP, lead, lead, [c(Rank.KING, Suit.SPADE)] * 2)


@pytest.mark.unit
def test_two_cards_of_equal_rank_but_different_suits_are_not_a_set():
    """'two nines are equal in rank but not identical' - they cannot win."""
    trump = {'rank': Rank.NINE, 'suit': Suit.CLUB}
    lead = [c(Rank.JACK, Suit.HEART)] * 2
    two_nines = [c(Rank.NINE, Suit.SPADE), c(Rank.NINE, Suit.HEART)]

    assert not identical_set_lead_decision(trump, lead, lead, two_nines)


@pytest.mark.unit
def test_an_unpaired_high_play_cannot_take_a_pair():
    lead = [c(Rank.JACK, Suit.SPADE)] * 2
    assert not identical_set_lead_decision(
        TRUMP, lead, lead, [c(Rank.ACE, Suit.SPADE), c(Rank.KING, Suit.SPADE)])


@pytest.mark.unit
def test_a_trump_pair_takes_a_pair_of_the_led_suit():
    """'may trump with ♣7-♣7 to win' - the same shape, in trumps."""
    lead = [c(Rank.JACK, Suit.SPADE)] * 2
    assert identical_set_lead_decision(TRUMP, lead, lead, [c(Rank.SEVEN, Suit.HEART)] * 2)


# --- "Leading a Sequence of Sets" (tractors) ---

@pytest.mark.unit
def test_a_higher_tractor_of_the_same_shape_wins():
    lead = [c(Rank.EIGHT, Suit.SPADE)] * 2 + [c(Rank.SEVEN, Suit.SPADE)] * 2
    higher = [c(Rank.KING, Suit.SPADE)] * 2 + [c(Rank.QUEEN, Suit.SPADE)] * 2

    assert sequence_identical_set_lead_decision(TRUMP, lead, lead, higher)


@pytest.mark.unit
def test_a_trump_tractor_takes_a_tractor_of_the_led_suit():
    lead = [c(Rank.KING, Suit.SPADE)] * 2 + [c(Rank.QUEEN, Suit.SPADE)] * 2
    trumps = [c(Rank.THREE, Suit.HEART)] * 2 + [c(Rank.TWO, Suit.HEART)] * 2

    assert sequence_identical_set_lead_decision(TRUMP, lead, lead, trumps)


@pytest.mark.unit
def test_three_pairs_cannot_take_two_triples():
    """'a higher sequence of the same shape (same size and length)'. Both of
    these are six cards; only one of them is two triples."""
    two_triples = [c(Rank.NINE, Suit.SPADE)] * 3 + [c(Rank.EIGHT, Suit.SPADE)] * 3
    three_pairs = ([c(Rank.KING, Suit.SPADE)] * 2 + [c(Rank.QUEEN, Suit.SPADE)] * 2
                   + [c(Rank.JACK, Suit.SPADE)] * 2)

    assert not sequence_identical_set_lead_decision(
        TRUMP, two_triples, two_triples, three_pairs)


@pytest.mark.unit
def test_two_triples_cannot_take_three_pairs_either():
    two_triples = [c(Rank.KING, Suit.SPADE)] * 3 + [c(Rank.QUEEN, Suit.SPADE)] * 3
    three_pairs = ([c(Rank.NINE, Suit.SPADE)] * 2 + [c(Rank.EIGHT, Suit.SPADE)] * 2
                   + [c(Rank.SEVEN, Suit.SPADE)] * 2)

    assert not sequence_identical_set_lead_decision(
        TRUMP, three_pairs, three_pairs, two_triples)


@pytest.mark.unit
def test_a_loose_collection_cannot_take_a_tractor():
    lead = [c(Rank.EIGHT, Suit.SPADE)] * 2 + [c(Rank.SEVEN, Suit.SPADE)] * 2
    loose = [c(Rank.ACE, Suit.SPADE), c(Rank.KING, Suit.SPADE),
             c(Rank.QUEEN, Suit.SPADE), c(Rank.JACK, Suit.SPADE)]

    assert not sequence_identical_set_lead_decision(TRUMP, lead, lead, loose)


# --- "Leading a Group of Top Cards" ---

@pytest.mark.unit
def test_a_group_of_top_cards_is_not_beaten_by_the_led_suit():
    """The lead is unbeatable in its own suit - that is what makes it legal.
    A sum of card values would let ♠K-♠Q outweigh an ace beside a low card."""
    lead = [c(Rank.ACE, Suit.SPADE), c(Rank.THREE, Suit.SPADE)]
    king_queen = [c(Rank.KING, Suit.SPADE), c(Rank.QUEEN, Suit.SPADE)]

    assert not leading_group_of_top_decision(TRUMP, lead, lead, king_queen)


@pytest.mark.unit
def test_a_void_player_takes_a_group_of_top_cards_with_trumps():
    lead = [c(Rank.ACE, Suit.SPADE), c(Rank.KING, Suit.SPADE)]
    trumps = [c(Rank.SEVEN, Suit.HEART), c(Rank.SIX, Suit.HEART)]

    assert leading_group_of_top_decision(TRUMP, lead, lead, trumps)


@pytest.mark.unit
def test_a_part_trump_play_does_not_take_a_group_of_top_cards():
    lead = [c(Rank.ACE, Suit.SPADE), c(Rank.KING, Suit.SPADE)]
    half_trump = [c(Rank.SEVEN, Suit.HEART), c(Rank.TWO, Suit.CLUB)]

    assert not leading_group_of_top_decision(TRUMP, lead, lead, half_trump)


@pytest.mark.unit
def test_between_two_trumping_players_the_bigger_trump_wins():
    """'the one with the highest trump set matching the largest combination'."""
    lead = [c(Rank.ACE, Suit.SPADE), c(Rank.KING, Suit.SPADE)]
    first = [c(Rank.THREE, Suit.HEART), c(Rank.TWO, Suit.HEART)]
    second = [c(Rank.KING, Suit.HEART), c(Rank.QUEEN, Suit.HEART)]

    assert leading_group_of_top_decision(TRUMP, lead, first, second)
    assert not leading_group_of_top_decision(TRUMP, lead, second, first)


# --- lead validity ---

@pytest.mark.unit
def test_a_lead_cannot_mix_a_trump_with_a_card_of_its_printed_suit():
    """With fives trump, ♠5 is a trump and ♠A is a spade - two suits."""
    assert determine_leading_play(
        TRUMP, [c(Rank.FIVE, Suit.SPADE), c(Rank.ACE, Suit.SPADE)]) == 'invalid'


@pytest.mark.unit
def test_a_lead_of_mixed_suits_is_invalid():
    assert determine_leading_play(
        TRUMP, [c(Rank.ACE, Suit.SPADE), c(Rank.ACE, Suit.CLUB)]) == 'invalid'


@pytest.mark.unit
def test_an_all_trump_lead_is_one_suit():
    """Trumps are a suit of their own, so a trump-rank card and a trump-suit
    card can be led together."""
    assert determine_leading_play(
        TRUMP, [c(Rank.FIVE, Suit.SPADE), c(Rank.ACE, Suit.HEART)]) != 'invalid'


# --- following: "must play matching sets if possible" ---

@pytest.mark.unit
def test_holding_a_pair_you_must_play_it():
    """'Hold ♥A, ♥10, ♥10, ♥6 -> must play the pair of tens'."""
    hand = [c(Rank.ACE, Suit.CLUB), c(Rank.TEN, Suit.CLUB),
            c(Rank.TEN, Suit.CLUB), c(Rank.SIX, Suit.CLUB)]
    gs, me = _hand_of(hand, [c(Rank.JACK, Suit.CLUB)] * 2)

    assert validate_multi_card_play(gs, me, [c(Rank.TEN, Suit.CLUB)] * 2)
    assert not validate_multi_card_play(
        gs, me, [c(Rank.ACE, Suit.CLUB), c(Rank.SIX, Suit.CLUB)])


@pytest.mark.unit
def test_without_a_pair_any_two_of_the_suit_will_do():
    """'Hold ♥A, ♥K, ♥10, ♥6 -> play any two hearts, but cannot win'."""
    hand = [c(Rank.ACE, Suit.CLUB), c(Rank.KING, Suit.CLUB),
            c(Rank.TEN, Suit.CLUB), c(Rank.SIX, Suit.CLUB)]
    gs, me = _hand_of(hand, [c(Rank.JACK, Suit.CLUB)] * 2)

    assert validate_multi_card_play(
        gs, me, [c(Rank.ACE, Suit.CLUB), c(Rank.SIX, Suit.CLUB)])


@pytest.mark.unit
def test_with_two_pairs_you_may_choose_which_to_play():
    """'Hold ♥K, ♥K, ♥10, ♥10 -> may play kings (to win) or tens (to lose
    intentionally)'. The obligation is to play a pair, not the best one."""
    hand = [c(Rank.KING, Suit.CLUB), c(Rank.KING, Suit.CLUB),
            c(Rank.TEN, Suit.CLUB), c(Rank.TEN, Suit.CLUB)]
    gs, me = _hand_of(hand, [c(Rank.JACK, Suit.CLUB)] * 2)

    assert validate_multi_card_play(gs, me, [c(Rank.KING, Suit.CLUB)] * 2)
    assert validate_multi_card_play(gs, me, [c(Rank.TEN, Suit.CLUB)] * 2)


@pytest.mark.unit
def test_holding_a_triple_against_a_led_pair_you_must_still_play_a_pair():
    """'Hold ♥8, ♥8, ♥8, ♥6, ♥5 -> must play two eights'."""
    hand = [c(Rank.EIGHT, Suit.CLUB)] * 3 + [c(Rank.SIX, Suit.CLUB), c(Rank.FOUR, Suit.CLUB)]
    gs, me = _hand_of(hand, [c(Rank.JACK, Suit.CLUB)] * 2)

    assert validate_multi_card_play(gs, me, [c(Rank.EIGHT, Suit.CLUB)] * 2)
    assert not validate_multi_card_play(
        gs, me, [c(Rank.SIX, Suit.CLUB), c(Rank.FOUR, Suit.CLUB)])


@pytest.mark.unit
def test_a_tractor_lead_asks_for_as_many_pairs_as_you_hold():
    hand = ([c(Rank.KING, Suit.CLUB)] * 2 + [c(Rank.NINE, Suit.CLUB)] * 2
            + [c(Rank.SIX, Suit.CLUB), c(Rank.FOUR, Suit.CLUB)])
    lead = [c(Rank.JACK, Suit.CLUB)] * 2 + [c(Rank.TEN, Suit.CLUB)] * 2
    gs, me = _hand_of(hand, lead)

    assert validate_multi_card_play(
        gs, me, [c(Rank.KING, Suit.CLUB)] * 2 + [c(Rank.NINE, Suit.CLUB)] * 2)
    # Two pairs held, so breaking both of them up is not allowed.
    assert not validate_multi_card_play(
        gs, me, [c(Rank.KING, Suit.CLUB), c(Rank.NINE, Suit.CLUB),
                 c(Rank.SIX, Suit.CLUB), c(Rank.FOUR, Suit.CLUB)])


@pytest.mark.unit
def test_a_player_void_in_the_suit_may_play_anything():
    """'If a player runs out of the led suit entirely, they may play any cards
    with no obligation to play sets'."""
    hand = [c(Rank.ACE, Suit.SPADE), c(Rank.KING, Suit.DIAMOND)]
    gs, me = _hand_of(hand, [c(Rank.JACK, Suit.CLUB)] * 2)

    assert validate_multi_card_play(
        gs, me, [c(Rank.ACE, Suit.SPADE), c(Rank.KING, Suit.DIAMOND)])


# --- the shape machinery itself ---

@pytest.mark.unit
def test_play_shape_tells_pairs_and_triples_apart():
    three_pairs = ([c(Rank.KING, Suit.SPADE)] * 2 + [c(Rank.QUEEN, Suit.SPADE)] * 2
                   + [c(Rank.JACK, Suit.SPADE)] * 2)
    two_triples = [c(Rank.KING, Suit.SPADE)] * 3 + [c(Rank.QUEEN, Suit.SPADE)] * 3

    assert play_shape(three_pairs) == (2, 2, 2)
    assert play_shape(two_triples) == (3, 3)


@pytest.mark.unit
def test_strength_comes_from_the_biggest_component_not_the_total():
    """An ace beside a low card outranks two middling cards."""
    ace_and_low = [c(Rank.ACE, Suit.SPADE), c(Rank.THREE, Suit.SPADE)]
    king_queen = [c(Rank.KING, Suit.SPADE), c(Rank.QUEEN, Suit.SPADE)]

    assert (strongest_component_value(TRUMP, ace_and_low)
            > strongest_component_value(TRUMP, king_queen))


# --- "Penalty for a false lead", enforced up front ---
# The rules punish a beatable group-of-top lead after the fact. This engine
# refuses it instead, which it can do because it sees every hand — and because
# a leader always has a legal alternative, a single card lead being always
# legal, so refusing can never leave anyone stuck.

def _table_where(leader_hand, others, leading_hand=None):
    """A game state with a chosen leader hand and chosen opponent hands."""
    gs = GameState()
    players = [generate_player(f'p{i}') for i in range(1 + len(others))]
    for player in players:
        add_player(gs, player)
    gs.declare_trump = DeclareTrump(rank=TRUMP['rank'], suit=TRUMP['suit'])
    leader = players[0]
    gs.players_and_hand[str(leader.uuid)] = list(leader_hand)
    for player, hand in zip(players[1:], others):
        gs.players_and_hand[str(player.uuid)] = list(hand)
    gs.leading_hand_of_subround = list(leading_hand or [])
    return gs, leader


@pytest.mark.unit
def test_a_genuine_group_of_top_cards_may_be_led():
    lead = [c(Rank.ACE, Suit.SPADE), c(Rank.KING, Suit.SPADE)]
    gs, leader = _table_where(lead, [[c(Rank.QUEEN, Suit.SPADE), c(Rank.TWO, Suit.SPADE)]])

    assert validate_multi_card_play(gs, leader, lead)


@pytest.mark.unit
def test_a_beatable_group_of_top_cards_is_refused():
    """'A player leads ♠A-♠K... if another player holds a single ♠A' — with two
    packs the second ace is out there, and it beats the king."""
    lead = [c(Rank.ACE, Suit.SPADE), c(Rank.KING, Suit.SPADE)]
    gs, leader = _table_where(lead, [[c(Rank.ACE, Suit.SPADE)]])

    assert not validate_multi_card_play(gs, leader, lead)


@pytest.mark.unit
def test_a_pair_component_is_only_beaten_by_a_higher_pair():
    """'If someone holds ♠Q-♠Q (beating the Jacks)' — one lone queen does not."""
    lead = [c(Rank.ACE, Suit.SPADE), c(Rank.JACK, Suit.SPADE), c(Rank.JACK, Suit.SPADE)]

    one_queen, = [[c(Rank.QUEEN, Suit.SPADE)]]
    gs, leader = _table_where(lead, [one_queen])
    assert validate_multi_card_play(gs, leader, lead)

    gs, leader = _table_where(lead, [[c(Rank.QUEEN, Suit.SPADE)] * 2])
    assert not validate_multi_card_play(gs, leader, lead)


@pytest.mark.unit
def test_a_higher_card_split_between_two_players_does_not_beat_a_pair():
    lead = [c(Rank.ACE, Suit.SPADE), c(Rank.JACK, Suit.SPADE), c(Rank.JACK, Suit.SPADE)]
    gs, leader = _table_where(lead, [[c(Rank.QUEEN, Suit.SPADE)],
                                     [c(Rank.QUEEN, Suit.SPADE)]])

    assert validate_multi_card_play(gs, leader, lead)


@pytest.mark.unit
def test_trumps_in_another_hand_do_not_make_a_lead_false():
    """The claim is only about the led suit — being trumped is the risk you
    take, not a foul."""
    lead = [c(Rank.ACE, Suit.SPADE), c(Rank.KING, Suit.SPADE)]
    gs, leader = _table_where(lead, [[c(Rank.ACE, Suit.HEART), c(Rank.KING, Suit.HEART)]])

    assert validate_multi_card_play(gs, leader, lead)


@pytest.mark.unit
def test_the_leaders_own_second_copy_does_not_beat_their_lead():
    lead = [c(Rank.ACE, Suit.SPADE), c(Rank.KING, Suit.SPADE)]
    leader_hand = lead + [c(Rank.ACE, Suit.SPADE)]
    gs, leader = _table_where(leader_hand, [[c(Rank.TWO, Suit.SPADE)]])

    assert validate_multi_card_play(gs, leader, lead)


@pytest.mark.unit
def test_a_single_card_lead_is_always_legal():
    """Why refusing a false lead is safe: nobody can be forced into one."""
    gs, leader = _table_where([c(Rank.TWO, Suit.SPADE)], [[c(Rank.ACE, Suit.SPADE)]])

    assert validate_multi_card_play(gs, leader, [c(Rank.TWO, Suit.SPADE)])


@pytest.mark.unit
def test_sets_and_tractors_are_not_held_to_the_top_card_claim():
    """Only a group of top cards claims to be unbeatable. Leading a low pair is
    an ordinary, legal thing to do."""
    lead = [c(Rank.THREE, Suit.SPADE)] * 2
    gs, leader = _table_where(lead, [[c(Rank.ACE, Suit.SPADE)] * 2])

    assert validate_multi_card_play(gs, leader, lead)
