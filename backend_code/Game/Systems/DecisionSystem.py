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
    Determines the winner of the identical set plays. 
    If this function returns True, the contesting player is the new winning play
    If this function returns False, the current winning player is still the winning play
    
    """
    pass


def sequence_identical_set_lead_decision(trump: Dict[str,Union[Rank, Suit]], leading_play: List[Card], winning_play: List[Card], contesting_play: List[Card]) -> bool:
    pass


def leading_group_of_top_decision(trump: Dict[str,Union[Rank, Suit]], leading_play: List[Card], winning_play: List[Card], contesting_play: List[Card]) -> bool:
    pass


def determine_leading_play(leading_play: List[Card]) -> str:
    if is_all_the_same_suit(leading_play) is False:
        return 'invalid'
    
    if len(leading_play) == 1:
        return 'single'

    if is_an_identical_set(leading_play):
        return 'identical_set'

    if is_check_identical_set_sequence(leading_play):
        return 'identical_sequence'

    return 'group_of_top'


def is_check_identical_set_sequence(leading_play: List[Card]) -> bool:
    pass


def is_an_identical_set(card_play: List[Card]) -> bool:
    length=len(card_play)
    counting_dictionary = counting_card(card_play)
    return length in counting_dictionary.values()


def is_an_identical_sequence_set(card_play: List[Card]) -> bool:
    pass


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
    Legal Cards for a Player can play with their current hand.
    The cards must obey the leading trick, if they can not the player can play whatever
    returns a list of cards that be played.
    :param game_state:
    :param player:
    :return: returns a list of cards that can be played
    """
    cards_can_play = [card for card in player.hand if game_state.leading_suit == card.suit]
    return cards_can_play if len(cards_can_play) > 0 else player.hand


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
