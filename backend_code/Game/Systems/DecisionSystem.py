from collections import Counter
from typing import List, Dict, Optional, Union
from Game.Views.CardView import card_str, card_emoji_str, SUIT_EMOJI
from Game.Components.GameState import GameState
from Game.Components.Player import Player
from Game.Components.Card import Card, Rank, Suit

CARD_VALUE: Dict = {
    Rank.ACE: 13,
    Rank.KING: 12,
    Rank.QUEEN: 11,
    Rank.JACK: 10,
    Rank.TEN: 9,
    Rank.NINE: 8,
    Rank.EIGHT: 7,
    Rank.SEVEN: 6,
    Rank.SIX: 5,
    Rank.FIVE: 4,
    Rank.FOUR: 3,
    Rank.THREE: 2,
    Rank.TWO: 1
}


def group_by_identical(card_play: List[Card]) -> List[List[Card]]:
    """Split a play into its groups of identical cards (same rank AND suit)."""
    groups: Dict[str, List[Card]] = {}
    for card in card_play:
        groups.setdefault(card_str(card), []).append(card)
    return list(groups.values())


def play_shape(card_play: List[Card]) -> tuple:
    """The sizes of a play's identical-card groups, largest first.

    This is what the rules mean by the "shape" of a combination: three pairs
    are (2, 2, 2) and two triples are (3, 3). Both are six cards, and one
    cannot beat the other.
    """
    return tuple(sorted((len(g) for g in group_by_identical(card_play)), reverse=True))


def strongest_component_value(trump: Dict[str, Union[Rank, Suit]], card_play: List[Card]) -> int:
    """How strong a play is, for ranking it against another of the same shape.

    The rules rank combinations by their biggest component — "the highest trump
    set matching the largest combination in the lead" — not by their total. A
    sum would let two middling cards outrank an ace beside a low card.
    """
    groups = group_by_identical(card_play)
    largest = max(len(group) for group in groups)
    return max(card_value(trump, group[0]) for group in groups if len(group) == largest)


def in_the_running(trump: Dict[str, Union[Rank, Suit]],
                   leading_play: List[Card], card_play: List[Card]) -> bool:
    """Can this play take the trick at all?

    Only two kinds can: one that follows the led suit throughout, or one made
    entirely of trumps. Anything else is a discard, however high it is.
    """
    leading_card = leading_play[0]
    if is_all_trump_cards(trump, card_play):
        return True
    if is_trump(trump, leading_card):
        # Trumps were led, so only trumps follow.
        return False
    return all(card.suit == leading_card.suit and not is_trump(trump, card)
               for card in card_play)


def outranks(trump: Dict[str, Union[Rank, Suit]],
             winning_play: List[Card], contesting_play: List[Card]) -> bool:
    """Does the contesting play take the trick off the current winner?

    Assumes both are already known to be legal contenders of the right shape.
    Ties stay with the current winner, which is the player who played first.
    """
    contesting_trumps = is_all_trump_cards(trump, contesting_play)
    winning_trumps = is_all_trump_cards(trump, winning_play)
    if contesting_trumps != winning_trumps:
        # Trumps beat the led suit, never the other way round.
        return contesting_trumps
    return (strongest_component_value(trump, contesting_play)
            > strongest_component_value(trump, winning_play))


def sets_of_size(card_play: List[Card], size: int) -> int:
    """How many separate identical sets of `size` these cards can make."""
    counts = Counter(card_str(card) for card in card_play)
    return sum(count // size for count in counts.values())


def cards_of_led_suit(trump: Dict[str, Union[Rank, Suit]],
                      leading_card: Card, hand: List[Card]) -> List[Card]:
    """The cards in `hand` that belong to the led suit, trumps being a suit of
    their own."""
    if is_trump(trump, leading_card):
        return [card for card in hand if is_trump(trump, card)]
    return [card for card in hand
            if card.suit == leading_card.suit and not is_trump(trump, card)]


def beatable_components(game_state: GameState, player: Player,
                        leading_play: List[Card]) -> List[List[Card]]:
    """The parts of a would-be group-of-top lead that somebody else can beat.

    Leading a group of top cards is a claim that no card of that suit beats any
    part of it. The rules settle a false claim after the event, with a
    challenge and a points penalty; the server can just check the claim first,
    since it can see every hand. A lead that would have been a foul is refused
    instead of punished, and the player leads something else.

    A component of `n` identical cards is beaten by `n` identical higher cards
    of the same suit in one other player's hand — one opponent holding a lone
    higher card does not beat a pair.
    """
    trump = {'suit': game_state.declare_trump.suit, 'rank': game_state.declare_trump.rank}
    leading_card = leading_play[0]
    leader_uuid = str(player.uuid)

    beatable = []
    for component in group_by_identical(leading_play):
        size = len(component)
        to_beat = card_value(trump, component[0])
        for holder_uuid, hand in game_state.players_and_hand.items():
            if str(holder_uuid) == leader_uuid:
                continue
            their_suit_cards = cards_of_led_suit(trump, leading_card, hand)
            if any(len(group) >= size and card_value(trump, group[0]) > to_beat
                   for group in group_by_identical(their_suit_cards)):
                beatable.append(component)
                break
    return beatable


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


def trump_rank_decoys(trump: Dict[str, Union[Rank, Suit]],
                      leading_card: Card, hand: List[Card]) -> List[Card]:
    """Cards in hand printed in the led suit that are really trumps.

    With twos trump, the 2♦ is a trump and not a diamond — it neither follows a
    diamond lead nor counts towards the diamonds you are holding. That is the
    least obvious rule in the game, so a message about following suit should
    say it out loud rather than leave the player counting their own hand and
    getting a different answer.
    """
    if is_trump(trump, leading_card):
        return []
    return [card for card in hand
            if card.suit == leading_card.suit and is_trump(trump, card)]


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

    if determine_leading_play(trump, played_cards) == 'group_of_top':
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
            one = required == 1
            kind = _set_name(set_size).lower().replace('a ', '')
            reason = (f'{_set_name(set_size)} was led and you hold '
                      f'{_count(held_sets, kind)} in {suit} — play '
                      f'{"it" if one else f"{NUMBER_WORDS.get(required, required)} of them"} '
                      f'rather than splitting {"it" if one else "them"} up.')
            return reason + _decoy_note(trump, leading_card, hand, suit)
    return None


def explain_illegal_play(game_state: GameState, player: Player,
                         played_cards: List[Card]) -> Optional[str]:
    """Why this play is not allowed, in words for the player, or None."""
    if not played_cards:
        return 'You have to play at least one card.'
    if not game_state.leading_hand_of_subround:
        return explain_illegal_lead(game_state, player, played_cards)
    return explain_illegal_follow(game_state, player, played_cards)


# --- which cards could still be part of a legal play ------------------------
# A hint for the player's own hand, not a rule. The rules are enforced by
# explain_illegal_play above, which is what actually refuses a play; this only
# decides which of your own cards are worth drawing attention to.
#
# The question it answers is "could this card appear in ANY legal play here",
# so a highlighted card is never a promise that any combination containing it
# is legal — only that the card is not already ruled out.


def playable_cards(game_state: GameState, hand: List[Card]) -> List[bool]:
    """One flag per card in `hand`: could it be part of a legal play?

    `hand` is passed in rather than read from the game state because the caller
    decides what order it is in — the view sorts it before sending it, and the
    flags have to line up with what the player is actually looking at.
    """
    leading_hand = game_state.leading_hand_of_subround
    # Leading is wide open: any single card is a legal lead, so nothing here is
    # ruled out and highlighting all of it would say nothing.
    if not leading_hand:
        return [True] * len(hand)

    trump = {'suit': game_state.declare_trump.suit, 'rank': game_state.declare_trump.rank}
    leading_card = leading_hand[0]
    needed = len(leading_hand)
    in_suit = cards_of_led_suit(trump, leading_card, hand)

    # Short of the led suit, every card can appear in some legal play: the suit
    # cards are owed, and the rest make up the difference.
    if len(in_suit) < needed:
        return [True] * len(hand)

    eligible = _eligible_when_following(trump, leading_hand, in_suit, needed)
    remaining = Counter(card_str(card) for card in eligible)
    flags = []
    for card in hand:
        key = card_str(card)
        # Counted rather than matched by value: holding one of a pair means one
        # of the two identical cards is highlighted, not both.
        if remaining.get(key):
            remaining[key] -= 1
            flags.append(True)
        else:
            flags.append(False)
    return flags


def _eligible_when_following(trump: Dict[str, Union[Rank, Suit]],
                             leading_hand: List[Card], in_suit: List[Card],
                             needed: int) -> List[Card]:
    """Which of the led-suit cards are still in play, sets taken into account.

    Holding enough of the led suit means nothing else can be played. On top of
    that, a set led against sets held has to be answered with those sets — so
    when a pair is led and you hold exactly one pair in the suit, that pair is
    the only pair-shaped answer and the singletons beside it are not eligible.
    """
    shape = play_shape(leading_hand)
    set_size = shape[0]
    # Only a uniform lead — a set or a tractor — obliges you to keep sets
    # together. A mixed shape has no set to match.
    if set_size == 1 or len(set(shape)) != 1:
        return in_suit

    held = sets_of_size(in_suit, set_size)
    required = min(held, len(shape))
    if required == 0:
        return in_suit

    counts = Counter(card_str(card) for card in in_suit)
    committed = Counter()
    for key, count in counts.items():
        committed[key] = (count // set_size) * set_size

    # Sets alone may not fill the play. Whatever is left over is free, so the
    # cards outside the sets stay eligible as the filler.
    if required * set_size < needed:
        return in_suit

    # More sets than the lead calls for means the player chooses which to play,
    # so every card that forms one is eligible.
    return [card for card in in_suit if committed.get(card_str(card))]


def single_card_lead_decision(trump: Dict[str,Union[Rank, Suit]], leading_play: Card, winning_play: Card, contesting_play: Card) -> bool:
    """
    Determines the winner of the single card plays. 
    If this function returns True, the contesting player is the new winning play
    If this function returns False, the current winning player is still the winning play
    
    """
    def matching(leading_play: Card, play: Card) -> bool:
        _matching = False
        if leading_play.suit == play.suit:
            _matching = True
        if is_trump(trump, play):
            _matching = True
        return _matching
    
    winning_play_matching_leading_play = matching(leading_play, winning_play)
    contesting_play_matching_leading_play = matching(leading_play, contesting_play)
    if card_value_match_bonus(trump, winning_play, winning_play_matching_leading_play) < card_value_match_bonus(trump, contesting_play, contesting_play_matching_leading_play):
        return True
    return False 


def identical_set_lead_decision(trump: Dict[str,Union[Rank, Suit]], leading_play: List[Card], winning_play: List[Card], contesting_play: List[Card]) -> bool:
    """
    Determines the winner when a set of identical cards (a pair, a triple...)
    is led. The contesting play only competes if it is an identical set of the
    same size, in the led suit or entirely of trumps.
    Returns True if the contesting player is the new winner.
    """
    if play_shape(contesting_play) != play_shape(leading_play):
        return False
    if not in_the_running(trump, leading_play, contesting_play):
        return False
    return outranks(trump, winning_play, contesting_play)


def sequence_identical_set_lead_decision(trump: Dict[str,Union[Rank, Suit]], leading_play: List[Card], winning_play: List[Card], contesting_play: List[Card]) -> bool:
    """
    Determines the winner when a tractor (a sequence of identical sets) is led.

    The rules allow only "a higher sequence of the same shape (same size and
    length)". Same shape, not merely the same number of cards: three pairs and
    two triples are both six cards, and neither can take the other.
    Returns True if the contesting player is the new winner.
    """
    if play_shape(contesting_play) != play_shape(leading_play):
        return False
    if not is_check_identical_set_sequence(contesting_play, trump):
        return False
    if not in_the_running(trump, leading_play, contesting_play):
        return False
    return outranks(trump, winning_play, contesting_play)


def leading_group_of_top_decision(trump: Dict[str,Union[Rank, Suit]], leading_play: List[Card], winning_play: List[Card], contesting_play: List[Card]) -> bool:
    """
    Determines the winner when a group of top cards is led.

    A group of top cards is, by definition, unbeatable in its own suit — that
    is what makes the lead legal, and leading a beatable one is a foul rather
    than a gamble. So following suit can never take it: only a player void in
    the led suit, playing trumps that mirror the shape of the lead, can.
    Between two such players the bigger trump component wins.
    Returns True if the contesting player is the new winner.
    """
    if play_shape(contesting_play) != play_shape(leading_play):
        return False
    if not is_all_trump_cards(trump, contesting_play):
        return False
    return outranks(trump, winning_play, contesting_play)


def determine_leading_play(trump: Dict[str,Union[Rank, Suit]], leading_play: List[Card]) -> str:
    if is_all_the_same_suit(trump, leading_play) is False:
        return 'invalid'
    
    if len(leading_play) == 1:
        return 'single'

    if is_an_identical_set(leading_play):
        return 'identical_set'

    if is_check_identical_set_sequence(leading_play, trump):
        return 'identical_sequence'

    return 'group_of_top'


def is_check_identical_set_sequence(leading_play: List[Card], trump: Dict[str, Union[Rank, Suit]] = None) -> bool:
    """Check if a leading play is a valid tractor (sequence of identical sets).
    E.g. 8♣-8♣-7♣-7♣ is a tractor of pairs.
    All sets must be same size, same suit, and adjacent ranks (skipping trump rank).
    Trump rank cards and jokers cannot be part of a tractor.
    """
    if len(leading_play) < 4:
        return False

    # Group cards by (suit, rank)
    groups: Dict[str, List[Card]] = {}
    for c in leading_play:
        key = card_str(c)
        groups.setdefault(key, []).append(c)

    # All groups must be the same size
    group_sizes = list(groups.values())
    set_size = len(group_sizes[0])
    if set_size < 2:
        return False
    if not all(len(g) == set_size for g in group_sizes):
        return False

    # Total cards must equal num_groups * set_size
    if len(leading_play) != len(groups) * set_size:
        return False

    # Extract the unique cards (one per group) and check same suit
    unique_cards = [g[0] for g in groups.values()]

    # All must be same suit
    suits = {c.suit for c in unique_cards}
    if len(suits) != 1:
        return False

    # Trump rank and jokers cannot be in a tractor
    if trump:
        for c in unique_cards:
            if c.rank == trump['rank'] or c.rank == Rank.JOKER:
                return False

    # Sort by rank value and check adjacency (skipping trump rank)
    rank_values = sorted([c.rank.value for c in unique_cards])
    for i in range(1, len(rank_values)):
        expected_next = rank_values[i - 1] + 1
        # Skip over trump rank if needed
        if trump and expected_next == trump['rank'].value:
            expected_next += 1
        if rank_values[i] != expected_next:
            return False

    return True


def is_an_identical_set(card_play: List[Card]) -> bool:
    length=len(card_play)
    counting_dictionary = counting_card(card_play)
    return length in counting_dictionary.values()


def is_an_identical_sequence_set(card_play: List[Card], trump: Dict[str, Union[Rank, Suit]] = None) -> bool:
    """Alias — checks whether a card play forms a valid tractor."""
    return is_check_identical_set_sequence(card_play, trump)


def is_all_the_same_suit(trump: Dict[str,Union[Rank, Suit]], card_play: List[Card]) -> bool:
    """Is this play all one suit, with trumps counting as a suit of their own?

    A trump-rank card keeps its printed suit but does not belong to it — with
    fives trump, ♠5 is a trump and ♠A is a spade, so ♠5-♠A is two suits, not
    one, and cannot be led together.
    """
    if is_all_trump_cards(trump, card_play):
        return True
    if any(is_trump(trump, card) for card in card_play):
        return False
    return len({card.suit for card in card_play}) == 1


def is_all_trump_cards(trump: Dict[str,Union[Rank, Suit]], card_play: List[Card]) -> bool:
    output = [is_trump(trump, card) for card in card_play]
    return all(output)


def counting_card(hand: List[Card]) -> Dict:
    counting_dictionary = dict()
    for c in hand:
        counting_dictionary[card_str(c)] = counting_dictionary.get(card_str(c), 0) + 1
    return counting_dictionary    



def is_trump(trump: Dict[str,Union[Rank, Suit]], card_played: Card) -> bool:
    if card_played.suit == trump['suit']:
        return True

    if card_played.rank in [trump['rank'], Rank.JOKER]:
        return True
    
    return False


def card_value_match_bonus(trump: Dict[str,Union[Rank, Suit]], card_played: Card, matching_leading_play: bool) -> int:
    match_bonus = 600 if matching_leading_play else 0
    return card_value(trump, card_played) + match_bonus


def card_value(trump: Dict[str,Union[Rank, Suit]], card_played: Card) -> int:
    """
    This is a simple mathmatical solution to determine which card played is more valuable in play.

    Example: suppose that eights and diamonds are trumps. Then the ranking of the trump suit from high to low is: 
    red joker, black joker, diamond8, [spade8, heart8, club8 - all equal], 
    diamondA, diamondK, diamondQ, diamondJ, diamond10, diamond9, diamond7, diamond6, diamond5, diamond4, diamond3, diamond2. 
    The rank of the other three suits, from high to low, is A, K, Q, J, 10, 9, 7, 6, 5, 4, 3, 2.
    """
    trump_rank: Rank = trump['rank']
    trump_suit: Suit = trump['suit']
    if card_played.rank == Rank.JOKER:
        if card_played.suit == Suit.BIG:
            return 500
        elif card_played.suit == Suit.SMALL:
            return 400
    
    if (card_played.rank, card_played.suit) == (trump_rank, trump_suit):
        return 300
    
    if card_played.rank == trump_rank:
        return 200
    
    if card_played.suit == trump_suit:
        return 100 + CARD_VALUE[card_played.rank]
    
    return CARD_VALUE[card_played.rank]


def hand_value(trump: Dict[str,Union[Rank, Suit]], hand: List[Card], matching_leading_play: bool) -> int:
    return sum([card_value_match_bonus(trump, card, matching_leading_play) for card in hand])



def legal_cards_to_play(game_state: GameState, player: Player) -> List[Card]:
    """
    Returns the list of cards the player is allowed to choose from.
    For single-card leads: must follow suit if able.
    For multi-card leads: must play suit cards. The full validation of sets/tractors
    is done separately in validate_multi_card_play.
    """
    hand = game_state.players_and_hand.get(player.uuid, [])
    if not game_state.leading_hand_of_subround:
        return hand

    leading_card = game_state.leading_hand_of_subround[0]
    trump = {'suit': game_state.declare_trump.suit, 'rank': game_state.declare_trump.rank}
    leading_is_trump = is_trump(trump, leading_card)

    if leading_is_trump:
        suit_cards = [card for card in hand if is_trump(trump, card)]
    else:
        suit_cards = [card for card in hand if card.suit == leading_card.suit and not is_trump(trump, card)]

    return suit_cards if suit_cards else hand


def validate_multi_card_play(game_state: GameState, player: Player, played_cards: List[Card]) -> bool:
    """
    Validates a multi-card play against the leading hand rules.
    - Leading player: must play a valid combination (identical set, tractor, or group of same suit)
    - Following player: must play correct number of cards, following suit and matching
      set structure as much as possible.
    Returns True if the play is valid.
    """
    hand = game_state.players_and_hand.get(player.uuid, [])
    leading_hand = game_state.leading_hand_of_subround
    trump = {'suit': game_state.declare_trump.suit, 'rank': game_state.declare_trump.rank}

    # If this is the leading play, validate the combination
    if not leading_hand:
        if len(played_cards) == 1:
            return True
        if not is_all_the_same_suit(trump, played_cards):
            return False
        play_type = determine_leading_play(trump, played_cards)
        if play_type == 'invalid':
            return False
        # A group of top cards has to actually be unbeatable. Checked here
        # rather than penalised later, and safe to refuse outright because a
        # leader always has a legal alternative — a single card is always a
        # legal lead, so nobody can be forced into this.
        if play_type == 'group_of_top' and beatable_components(game_state, player, played_cards):
            return False
        return True

    num_needed = len(leading_hand)

    # Following: must play the correct number of cards
    if len(played_cards) != num_needed:
        return False

    # All played cards must be in hand
    temp_hand = list(hand)
    for pc in played_cards:
        found = False
        for i, hc in enumerate(temp_hand):
            if hc.suit == pc.suit and hc.rank == pc.rank:
                temp_hand.pop(i)
                found = True
                break
        if not found:
            return False

    # Following player: must play suit cards first
    leading_card = leading_hand[0]
    leading_is_trump = is_trump(trump, leading_card)

    if leading_is_trump:
        suit_cards_in_hand = [c for c in hand if is_trump(trump, c)]
    else:
        suit_cards_in_hand = [c for c in hand if c.suit == leading_card.suit and not is_trump(trump, c)]

    if leading_is_trump:
        suit_cards_played = [c for c in played_cards if is_trump(trump, c)]
    else:
        suit_cards_played = [c for c in played_cards if c.suit == leading_card.suit and not is_trump(trump, c)]

    # Must play as many suit cards as possible (up to num_needed)
    expected_suit_count = min(len(suit_cards_in_hand), num_needed)
    if len(suit_cards_played) < expected_suit_count:
        return False

    # Having enough cards of the suit is not enough: the rules also require
    # matching sets where the player holds them. Holding ♥10-♥10 against a led
    # pair of ♥J, playing ♥A-♥6 instead is not a choice the player has.
    #
    # Only for leads whose groups are all one size — a set or a tractor. A
    # group of top cards mixes sizes, and what "as far as possible" means there
    # is not pinned down well enough to enforce.
    lead_shape = play_shape(leading_hand)
    set_size = lead_shape[0]
    if set_size > 1 and len(set(lead_shape)) == 1:
        sets_needed = len(lead_shape)
        sets_held = sets_of_size(suit_cards_in_hand, set_size)
        sets_required = min(sets_held, sets_needed)
        if sets_of_size(suit_cards_played, set_size) < sets_required:
            return False

    return True
