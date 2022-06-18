from typing import List
from Game.Components.GameState import GameState
from Game.Components.Player import Player
from Game.Components.Card import Card, Rank


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
