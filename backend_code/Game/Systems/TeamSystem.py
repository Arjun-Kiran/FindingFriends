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


def copies_played(game_state: GameState, suit: Suit, rank: Rank) -> int:
    """How many copies of a card have been played so far, across all piles."""
    played = 0
    for pile in (game_state.card_in_discard_pile, game_state.cards_in_active_pile):
        for pile_card in pile:
            if pile_card.suit == suit and pile_card.rank == rank:
                played += 1
    return played


def check_friend_card_played(game_state: GameState, player_uuid: str, cards_played: List[Card]) -> List[str]:
    """Register the player as a friend if this play contains a called copy.

    Returns the uuids revealed by this play — empty on most plays. Callers use
    it to announce the reveal; working it out from the friends list afterwards
    means diffing a list against a copy taken beforehand, which is easy to get
    subtly wrong and easy to forget.

    Each calling card names one specific copy ("the first Ace of Clubs"). A
    single play can put several copies on the table at once — a pair or a
    tractor — so each copy has to be given its own position in the sequence.
    Comparing one running total against the order would skip the called copy
    whenever it arrives alongside another copy of the same card.

    Assumes cards_played have already been added to cards_in_active_pile.
    """
    newly_revealed = []
    for calling_card in game_state.friend_calling_cards:
        matches = [card for card in cards_played
                   if card.suit == calling_card.suit and card.rank == calling_card.rank]
        if not matches:
            continue

        # Positions in the sequence that this play occupies. Copies already on
        # the table include the ones just played, so subtract them back out.
        played_before = copies_played(game_state, calling_card.suit, calling_card.rank) - len(matches)
        first_position = played_before + 1
        last_position = played_before + len(matches)

        if first_position <= calling_card.order <= last_position:
            # Against the rule as well as the friends list: one play can satisfy
            # two rules at once (a pair covering the 1st and 2nd copy), and each
            # rule shows its own trigger. First to satisfy a rule keeps it.
            if not calling_card.revealed_by:
                calling_card.revealed_by = player_uuid
            if player_uuid not in game_state.current_friends_of_alpha:
                game_state.current_friends_of_alpha.append(player_uuid)
                newly_revealed.append(player_uuid)

    # Check if all friends have been found
    expected_friends = number_of_cards_to_call_friends(len(game_state.player_order))
    if len(game_state.current_friends_of_alpha) >= expected_friends:
        game_state.all_friends_found = True

    return newly_revealed
