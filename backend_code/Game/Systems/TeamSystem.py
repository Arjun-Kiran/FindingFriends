from typing import List, Tuple
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


MULTIPLE_WORDS = {2: 'double', 3: 'triple', 4: 'quadruple', 5: 'quintuple', 6: 'sextuple'}
SPOT_WORDS = {2: 'two', 3: 'three', 4: 'four', 5: 'five'}


def friend_reveal_announcement(game_state: GameState, player_uuid: str, name: str) -> Tuple[str, str]:
    """(message, clause) announcing a player credited with a called card.

    Worded by how many places on the alpha team this one player now fills:

    - a player's first called card: "joined the alpha team"
    - a player holding two or more: "double jumped onto the alpha team" — one
      player standing in for several friends, so the team is smaller than the
      calls promised
    - the alpha playing a card they called: "double joined the alpha team" —
      they were on it already, so their first own card is their second place

    Call after check_friend_card_played, which credits the rules this counts.
    The clause is the subjectless form the big notification stitches under the
    player's name; see EventItem.clause.
    """
    satisfied = sum(1 for calling_card in game_state.friend_calling_cards
                    if calling_card.revealed_by == player_uuid)
    is_alpha = game_state.current_alpha_player.player_uuid == player_uuid
    places = satisfied + 1 if is_alpha else satisfied

    if places <= 1:
        clause = 'joined the alpha team'
        return f'{name} has {clause}', clause

    times = MULTIPLE_WORDS.get(places, f'{places}-times')
    if is_alpha:
        clause = f'{times} joined the alpha team'
        return f'{name} has {clause} by playing a card they called themselves', clause

    clause = f'{times} jumped onto the alpha team'
    spots = SPOT_WORDS.get(places, str(places))
    return f'{name} has {clause}, filling {spots} friend spots', clause


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

    Returns the uuids of players this play credited with a called card — empty
    on most plays. That includes a player who was already a friend and has just
    satisfied another rule (a double jump), and the alpha playing a card they
    called themselves: both are worth announcing, and friend_reveal_announcement
    words them. Working it out from the friends list afterwards means diffing a
    list against a copy taken beforehand, which is easy to get subtly wrong and
    easy to forget.

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

        # Against the rule as well as the friends list: one play can satisfy
        # two rules at once (a pair covering the 1st and 2nd copy), and each
        # rule shows its own trigger. First to satisfy a rule keeps it.
        if first_position <= calling_card.order <= last_position and not calling_card.revealed_by:
            calling_card.revealed_by = player_uuid
            if player_uuid not in game_state.current_friends_of_alpha:
                game_state.current_friends_of_alpha.append(player_uuid)
            # Once per play however many rules it satisfied: a pair covering
            # both copies is one announcement, worded as a double jump.
            if player_uuid not in newly_revealed:
                newly_revealed.append(player_uuid)

    # The hunt is over when every called card has been played, whoever played
    # it. Counted by rules rather than by players in the friends list: one
    # player can satisfy two rules — a double jump, a pair covering the 1st
    # and 2nd copy, or the alpha playing cards they called themselves — and
    # only joins that list once, so counting heads would leave the sides
    # unresolved for the rest of the round with nobody left to find.
    called = game_state.friend_calling_cards
    if called and all(calling_card.revealed_by for calling_card in called):
        game_state.all_friends_found = True

    return newly_revealed
