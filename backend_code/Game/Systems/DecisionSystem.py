from collections import Counter
from typing import List, Dict, Union
from Game.Views.CardView import card_str
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
