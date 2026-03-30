from typing import List
from Game.Components.GameState import GameState, DeclareCallingCard
from Game.Components.Card import Card
from Game.Modules.CardConstants import Suit, Rank


def number_of_cards_to_call_friends(number_of_players: int) -> int:
    if number_of_players < 5:
        raise Exception("Not enough players. Need 5 or more")

    if number_of_players > 12:
        raise Exception("Too many players")

    call_to_friend_dict = {
        '5': 1,
        '6': 2,
        '7': 2,
        '8': 3,
        '9': 3,
        '10': 4,
        '11': 4,
        '12': 5
    }

    return call_to_friend_dict[str(number_of_players)]


def check_friend_card_played(game_state: GameState, player_uuid: str, cards_played: List[Card]):
    """Check if any of the played cards match a calling card.

    Each calling card specifies a suit, rank, and order (e.g. "first Ace of Clubs").
    We track how many times a given suit+rank has been played across the game using
    a counter stored in game_state. When the count matches the calling card's order,
    the player who played it becomes a friend of alpha.
    """
    for card in cards_played:
        for calling_card in game_state.friend_calling_cards:
            if card.suit == calling_card.suit and card.rank == calling_card.rank:
                # Count how many of this suit+rank have been played so far
                # (cards_in_active_pile + card_in_discard_pile already include the current play)
                count = 0
                for pile_card in game_state.card_in_discard_pile:
                    if pile_card.suit == calling_card.suit and pile_card.rank == calling_card.rank:
                        count += 1
                for pile_card in game_state.cards_in_active_pile:
                    if pile_card.suit == calling_card.suit and pile_card.rank == calling_card.rank:
                        count += 1

                if count == calling_card.order:
                    if player_uuid not in game_state.current_friends_of_alpha:
                        game_state.current_friends_of_alpha.append(player_uuid)

    # Check if all friends have been found
    expected_friends = number_of_cards_to_call_friends(len(game_state.player_order))
    if len(game_state.current_friends_of_alpha) >= expected_friends:
        game_state.all_friends_found = True
