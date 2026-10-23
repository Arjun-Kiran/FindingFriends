"""Play rules put into words for the player.

DecisionSystem decides whether a play is legal and who wins a trick; this
module says why, in the sentence a player needs when they are refused. The
two change for different reasons — a rule because HouseRules.md changed, a
message because a player was confused by it — so they live apart.

Depends on DecisionSystem and never the other way round.
"""
from collections import Counter
from typing import Dict, List, Optional, Union

from Game.Components.Card import Card, Rank, Suit
from Game.Components.GameState import GameState
from Game.Components.Player import Player
from Game.Systems.DecisionSystem import (
    PlayShape, beatable_components, cards_of_led_suit, determine_leading_play,
    hr12_bites, is_all_the_same_suit, is_trump, links_played, longest_run_ranks,
    most_links_available, play_shape, sets_of_size, shape_owed, shape_played,
    trump_rank_decoys,
)
from Game.Views.CardView import card_emoji_str, card_str, RANK_EMOJI


# --- explaining a refusal -------------------------------------------------
# Telling a player only that a play is "invalid" leaves them to guess which of
# several rules they broke. These build the sentence the player actually needs.
#
# Anything drawn from the player's own hand is fair to name — they can see it.
# Only the false-lead case touches other hands, and that one stays vague on
# purpose, so a refused lead cannot be used to read the table.

SET_NAMES = {2: 'A pair', 3: 'A triple', 4: 'A set of four'}

SUIT_WORDS = {
    Suit.HEART: 'hearts',
    Suit.DIAMOND: 'diamonds',
    Suit.CLUB: 'clubs',
    Suit.SPADE: 'spades',
}

# Spelled out, never digits. "You still hold 2 ♦️" reads as the two of diamonds
# in a game where that is a real card; "two diamonds" cannot be misread.
NUMBER_WORDS = {
    1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
    6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten',
}


def _count(n: int, noun: str) -> str:
    return f'{NUMBER_WORDS.get(n, n)} {noun}{"" if n == 1 else "s"}'


def _set_name(size: int) -> str:
    return SET_NAMES.get(size, f'A set of {size}')


def suit_label(trump: Dict[str, Union[Rank, Suit]], card: Card) -> str:
    """What to call the led suit in a message — trumps are their own suit."""
    if is_trump(trump, card):
        return 'trumps'
    return SUIT_WORDS.get(card.suit, card.suit.name.lower())


def _cards_text(cards: List[Card]) -> str:
    return ' '.join(card_emoji_str(card) for card in cards)


def explain_illegal_lead(game_state: GameState, player: Player,
                         played_cards: List[Card]) -> Optional[str]:
    """Why this lead is not allowed, or None if it is fine."""
    trump = {'suit': game_state.declare_trump.suit, 'rank': game_state.declare_trump.rank}
    if len(played_cards) == 1:
        return None

    if not is_all_the_same_suit(trump, played_cards):
        if any(is_trump(trump, card) for card in played_cards):
            return ('Everything you lead has to be one suit, and trumps are a suit of '
                    'their own — a trump cannot be led alongside a plain card.')
        return 'Everything you lead has to be one suit.'

    if determine_leading_play(trump, played_cards) == PlayShape.GROUP_OF_TOP:
        if beatable_components(game_state, player, played_cards):
            return ('Leading several cards at once means either a matching set '
                    '(two of the very same card), a run of pairs in next-door ranks, '
                    'or cards that are all unbeatable in that suit. Something out '
                    'there beats part of this one — try leading a single card.')
    return None


def _decoy_note(trump: Dict[str, Union[Rank, Suit]], leading_card: Card,
                hand: List[Card], suit: str) -> str:
    """A sentence naming the trump-rank cards that only look like the led suit.

    Empty when the player holds none, so the common case stays short.
    """
    decoys = trump_rank_decoys(trump, leading_card, hand)
    if not decoys:
        return ''
    names = ' '.join(sorted({card_emoji_str(card) for card in decoys}))
    if len({card_str(card) for card in decoys}) > 1:
        return f' Your {names} are trumps, not {suit}, so they do not count.'
    singular = suit[:-1] if suit.endswith('s') else suit
    article = 'an' if singular[0] in 'aeiou' else 'a'
    return f' Your {names} is a trump, not {article} {singular}, so it does not count.'


def explain_illegal_follow(game_state: GameState, player: Player,
                           played_cards: List[Card]) -> Optional[str]:
    """Why this play does not follow the lead, or None if it is fine."""
    trump = {'suit': game_state.declare_trump.suit, 'rank': game_state.declare_trump.rank}
    hand = game_state.players_and_hand.get(str(player.uuid), [])
    leading_hand = game_state.leading_hand_of_subround
    leading_card = leading_hand[0]
    needed = len(leading_hand)
    suit = suit_label(trump, leading_card)
    # 'diamonds' plural for counting, 'diamond' singular for one of them.
    suit_noun = suit[:-1] if suit.endswith('s') and suit != 'trumps' else suit
    if suit == 'trumps':
        suit_noun = 'trump'

    if len(played_cards) != needed:
        one = needed == 1
        return (f'{needed} card{"" if one else "s"} {"was" if one else "were"} led, '
                f'so you have to play {needed}.')

    held = cards_of_led_suit(trump, leading_card, hand)
    played_in_suit = cards_of_led_suit(trump, leading_card, played_cards)

    must_play = min(len(held), needed)
    if len(played_in_suit) < must_play:
        holding = f'You still hold {_count(len(held), suit_noun)}'
        if needed == 1:
            reason = f'{holding}, so you have to follow suit.'
        elif must_play == needed:
            article = 'an' if suit_noun[0] in 'aeiou' else 'a'
            reason = f'{holding}, so every card you play has to be {article} {suit_noun}.'
        else:
            one = must_play == 1
            reason = (f'{holding}, so {"that one has" if one else f"all {NUMBER_WORDS.get(must_play, must_play)} have"} '
                      f'to be part of what you play.')
        return reason + _decoy_note(trump, leading_card, hand, suit)

    # Sets are only owed when the lead is all one size — a set or a tractor.
    lead_shape = play_shape(leading_hand)
    set_size = lead_shape[0]
    if set_size > 1 and len(set(lead_shape)) == 1:
        held_sets = sets_of_size(held, set_size)
        required = min(held_sets, len(lead_shape))
        if sets_of_size(played_in_suit, set_size) < required:
            # Named in cards, and the lead named as what it is: the player was
            # refused because they had not spotted the set, so "you hold one
            # pair" alone leaves them hunting for it.
            one_held = held_sets == 1
            kind = _set_name(set_size).lower().replace('a ', '')
            lead_name = 'A tractor' if len(lead_shape) > 1 else _set_name(set_size)
            if one_held:
                owed = 'it'
            elif required == held_sets:
                owed = 'them'
            else:
                owed = f'{NUMBER_WORDS.get(required, required)} of them'
            reason = (f'{lead_name} was led and you hold {_count(held_sets, kind)} in {suit} '
                      f'({_held_sets_text(held, set_size)}) — play {owed} '
                      f'rather than splitting {"it" if one_held else "them"} up.')
            return reason + _set_decoy_note(trump, leading_card, hand, suit)

        # HR-5. Says which cards rather than restating the rule: a player who
        # has just been told "keep your tractor together" still has to find it,
        # and the whole reason they played the wrong cards is that they had not
        # spotted it.
        if required >= 2:
            owed = most_links_available(trump, held, set_size, required)
            if links_played(trump, played_in_suit, set_size) < owed:
                runs = _longest_run_text(trump, held, set_size, required)
                return (f'A tractor was led and your {runs} in {suit} runs together '
                        f'— play it rather than breaking it up.'
                        + _set_decoy_note(trump, leading_card, hand, suit))

    # HR-12. Named in cards for the same reason as HR-5: the player has to be
    # told which pair, not only that the rule exists.
    hr12_size = hr12_bites(leading_hand)
    if hr12_size:
        owed_shape = shape_owed(held, hr12_size, needed)
        if shape_played(played_in_suit, hr12_size) != owed_shape:
            lead_name = 'A tractor' if len(lead_shape) > 1 else _set_name(hr12_size)
            return (f'{lead_name} was led, and when you cannot match it the biggest '
                    f'sets you hold in {suit} have to go in — play '
                    f'{_sub_sets_text(held, owed_shape, hr12_size)}, then fill the rest.'
                    + _set_decoy_note(trump, leading_card, hand, suit))
    return None


def explain_illegal_play(game_state: GameState, player: Player,
                         played_cards: List[Card]) -> Optional[str]:
    """Why this play is not allowed, in words for the player, or None."""
    if not played_cards:
        return 'You have to play at least one card.'
    if not game_state.leading_hand_of_subround:
        return explain_illegal_lead(game_state, player, played_cards)
    return explain_illegal_follow(game_state, player, played_cards)


def _set_decoy_note(trump: Dict[str, Union[Rank, Suit]], leading_card: Card,
                    hand: List[Card], suit: str) -> str:
    """The lookalike note, for a message about sets: only when the lookalikes
    could themselves pass for a set. A lone 2♠ cannot be mistaken for a pair
    of spades, and naming it there only sends the player looking at the wrong
    card."""
    decoys = Counter(card_str(card) for card in trump_rank_decoys(trump, leading_card, hand))
    if not any(count >= 2 for count in decoys.values()):
        return ''
    return _decoy_note(trump, leading_card, hand, suit)


def _held_sets_text(held: List[Card], set_size: int) -> str:
    """Every set of `set_size` held, named in cards: '5♠ 5♠ and 8♠ 8♠'."""
    counts = Counter(card_str(card) for card in held)
    examples = {card_str(card): card for card in held}
    sets = [_cards_text([examples[key]] * set_size)
            for key, count in counts.items() for _ in range(count // set_size)]
    return ' and '.join(sets)


def _sub_sets_text(held: List[Card], owed: tuple, set_size: int) -> str:
    """The smaller sets a player owes, named in cards: 'a pair (8♣ 8♣ or
    5♣ 5♣)'. Full-size sets and single cards are left out — the first have
    their own message and the second are only filler."""
    counts = Counter(card_str(card) for card in held)
    examples = {card_str(card): card for card in held}
    parts = []
    for size in sorted({piece for piece in owed if 1 < piece < set_size}, reverse=True):
        wanted = sum(1 for piece in owed if piece == size)
        # A kind can give a piece this size from what is left once its full
        # sets are taken out — which, below the set size, is all of it.
        options = [_cards_text([examples[key]] * size) for key, count in counts.items()
                   if count % set_size >= size]
        name = _set_name(size).lower()
        label = name if wanted == 1 else f'{NUMBER_WORDS.get(wanted, wanted)} {name[2:]}s'
        joiner = ' or ' if len(options) > wanted else ' and '
        parts.append(f'{label} ({joiner.join(options)})')
    return ' and '.join(parts)


def _longest_run_text(trump: Dict[str, Union[Rank, Suit]], held: List[Card],
                      set_size: int, sets_required: int) -> str:
    """The run the player should have kept, named in cards: '5-5 and 4-4'."""
    best = longest_run_ranks(trump, held, set_size, sets_required)
    if not best:
        return 'tractor'
    names = [RANK_EMOJI.get(Rank(value), str(value)) for value in sorted(best, reverse=True)]
    joined = [f'{name}-{name}' if set_size == 2 else '-'.join([name] * set_size)
              for name in names]
    return ' and '.join(joined)


# What the table calls each shape, for the sets whose size has a name of its
# own. Anything larger is just described by its size — nobody says "a sextuple".
#
# Lowercase and indefinite, because these land mid-sentence ('led with a
# tractor'). SET_NAMES above is the same idea for a sentence that starts with
# it ('A pair was led'), which is why the two are not shared.
LEAD_SHAPE_NAMES = {2: 'a pair', 3: 'a triple', 4: 'a four of a kind'}


def name_leading_play(trump: Dict[str, Union[Rank, Suit]], leading_play: List[Card]) -> str:
    """The shape of a lead as a player would say it: 'a tractor', 'a pair'.

    Empty for a single card, which is the ordinary case and needs no naming —
    which also makes this the test for whether a lead is worth announcing.
    """
    shape = determine_leading_play(trump, leading_play)

    if shape == PlayShape.IDENTICAL_SEQUENCE:
        return 'a tractor'
    if shape == PlayShape.IDENTICAL_SET:
        size = len(leading_play)
        return LEAD_SHAPE_NAMES.get(size, f'{size} of a kind')
    if shape == PlayShape.GROUP_OF_TOP:
        return 'a throw'
    # SINGLE, and INVALID — which the caller has already refused by the
    # time this runs, but which is not something to announce either way.
    return ''
