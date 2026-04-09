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
    Determines the winner of the identical set plays (pairs, triples, etc).
    The contesting play can only win if it is an identical set of the same size
    and has a higher value (following suit or trump).
    Returns True if the contesting player is the new winner.
    """
    # Contesting play must be an identical set of the same size to compete
    if not is_an_identical_set(contesting_play) or len(contesting_play) != len(leading_play):
        return False

    leading_card = leading_play[0]

    def matching(play_card: Card) -> bool:
        if leading_card.suit == play_card.suit:
            return True
        if is_trump(trump, play_card):
            return True
        return False

    winning_match = matching(winning_play[0])
    contesting_match = matching(contesting_play[0])
    winning_val = card_value_match_bonus(trump, winning_play[0], winning_match)
    contesting_val = card_value_match_bonus(trump, contesting_play[0], contesting_match)
    return contesting_val > winning_val


def sequence_identical_set_lead_decision(trump: Dict[str,Union[Rank, Suit]], leading_play: List[Card], winning_play: List[Card], contesting_play: List[Card]) -> bool:
    """
    Determines the winner when a tractor (sequence of identical sets) is led.
    The contesting play must be a tractor of the same shape (same number of sets,
    same set size) and higher value to win.
    Returns True if the contesting player is the new winner.
    """
    # Contesting play must be a valid tractor of the same total size
    if len(contesting_play) != len(leading_play):
        return False
    if not is_check_identical_set_sequence(contesting_play, trump):
        return False

    # Compare by hand value (matching logic same as single/set)
    leading_card = leading_play[0]

    def matching(play: List[Card]) -> bool:
        card = play[0]
        if leading_card.suit == card.suit:
            return True
        if is_trump(trump, card):
            return True
        return False

    winning_match = matching(winning_play)
    contesting_match = matching(contesting_play)
    winning_val = hand_value(trump, winning_play, winning_match)
    contesting_val = hand_value(trump, contesting_play, contesting_match)
    return contesting_val > winning_val


def leading_group_of_top_decision(trump: Dict[str,Union[Rank, Suit]], leading_play: List[Card], winning_play: List[Card], contesting_play: List[Card]) -> bool:
    """
    Determines the winner when a group of top cards is led.
    A group-of-top lead can only be beaten by trumps if the player is void in the led suit.
    The comparison is done by total hand value.
    Returns True if the contesting player is the new winner.
    """
    if len(contesting_play) != len(leading_play):
        return False

    leading_card = leading_play[0]

    def matching(play: List[Card]) -> bool:
        card = play[0]
        if leading_card.suit == card.suit:
            return True
        if is_trump(trump, card):
            return True
        return False

    winning_match = matching(winning_play)
    contesting_match = matching(contesting_play)
    winning_val = hand_value(trump, winning_play, winning_match)
    contesting_val = hand_value(trump, contesting_play, contesting_match)
    return contesting_val > winning_val


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
    if is_all_trump_cards(trump, card_play):
        return True
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
        return play_type != 'invalid'

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

    return True


def compare_hand_spades(game_state: GameState, hand_1: List[Card], hand_2: List[Card]) -> bool:
    """
    Compares hands according to card game spades rules
    Winning Cards, from Highest to Lowest
    1. Big Joker
    2. Small Joker
    3. Ace of Spades
    4. King of Spades -> Three of Spades
    5. Dueces
    6. Trick Suit Ace, King -> Three of Trick Suit
    7. Other cards
    :param game_state:
    :param hand_1:
    :param hand_2:
    :return:
    """
    hand_1_card: Card = hand_1.pop()
    hand_2_card: Card = hand_2.pop()
    if hand_1_card.suit is game_state.trump_suit ^ hand_2_card.suit is game_state.trump_suit:
        return hand_1_card.suit is game_state.trump_suit
    elif hand_1_card.suit is hand_2_card.suit or hand_2_card.suit is not game_state.trump_suit or hand_2_card.rank is not game_state.trump_rank:
        return int(hand_1_card.rank.value) > int(hand_2_card.rank.value)
    return False
