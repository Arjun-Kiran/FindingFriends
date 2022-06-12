from typing import List
from src.Game.Components.GameState import GameState
from src.Game.Components.Player import Player
from src.Game.Components.Card import Card


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


def who_wins_the_round(game_state: GameState) -> str:
    """
    Bubble sorts, the best hand should be at index 0 and the worst hand at index -1 (last index)
    :param game_state:
    :return: the winning player's uuid
    """
    player_uuids = list(game_state.player_cards_played.keys())
    for i in range(game_state.number_of_players-1):
        for j in range(0, game_state.number_of_players-i-1):
            player_1_hand = game_state.player_cards_played[player_uuids[i]]
            player_2_hand = game_state.player_cards_played[player_uuids[j]]
            if compare_hand(game_state, player_1_hand, player_2_hand) is False:
                player_uuids[j], player_uuids[j+1] = player_uuids[j+1], player_uuids[j]

    return player_uuids[0]


def compare_hand(game_state: GameState, hand_1: List[Card], hand_2: List[Card]) -> bool:
    """
    If hand_1 is better than hand_2, return True
    If hand_2 is better than hand_2, return False
    :param game_state:
    :param hand_1:
    :param hand_2:
    :return:
    """
    if game_state.game_type is GameType.SPADES:
        return compare_hand_spades(game_state, hand_1, hand_2)

    raise Exception("Game Type {game_type} not implemented ".format(game_type=game_state.game_type))


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
