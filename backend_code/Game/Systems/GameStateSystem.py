
from typing import Tuple
from uuid import uuid4
from Game.Components.GameState import GameState
from Game.Components.Player import Player
from Game.Modules.CardConstants import Suit, Rank
from Game.Systems.DeckSystem import build_deck, shuffle_deck
from Game.Systems.EventSystem import record_event, Event
from Game.Modules.Avatars import is_valid_avatar, pick_avatar


def generate_player(name, avatar: str = '') -> Player:
    new_player = Player(name=name, avatar=avatar)
    new_player.uuid = str(uuid4())
    return new_player


def taken_avatars(current_game_state: GameState) -> list:
    """Avatars already spoken for in this game."""
    return [p.avatar for p in current_game_state.player_order if p.avatar]


def set_player_avatar(current_game_state: GameState, player_uuid: str, avatar: str) -> bool:
    """Give a player an avatar. False if it is invalid or already taken.

    Writes through both player_order and player_dict on purpose. They hold the
    same Player object right up until the game state is saved and reloaded,
    after which pydantic rebuilds them as two separate objects — and every
    socket handler works on a freshly reloaded state, so updating only one of
    them would leave the other stale.
    """
    if not is_valid_avatar(avatar):
        return False

    if any(p.avatar == avatar and str(p.uuid) != player_uuid
           for p in current_game_state.player_order):
        return False

    for player in current_game_state.player_order:
        if str(player.uuid) == player_uuid:
            player.avatar = avatar
    if player_uuid in current_game_state.player_dict:
        current_game_state.player_dict[player_uuid].avatar = avatar
    return True


def add_player(current_game_state: GameState, joining_player: Player) -> GameState:
    # Everyone gets an avatar on the way in, so the UI never has to draw a
    # player without one. A pick made in the lobby replaces it later.
    if not is_valid_avatar(joining_player.avatar) or joining_player.avatar in taken_avatars(current_game_state):
        joining_player.avatar = pick_avatar(taken_avatars(current_game_state))
    current_game_state.player_order.append(joining_player)
    uuid_str = str(joining_player.uuid)
    current_game_state.player_dict[uuid_str] = joining_player
    current_game_state.players_round_score[uuid_str] = 0
    current_game_state.players_overall_score[uuid_str] = 0
    current_game_state.players_and_hand[uuid_str] = list()
    current_game_state.player_levels[uuid_str] = Rank.TWO.value
    if current_game_state.hosting_player is None:
        current_game_state.hosting_player = joining_player
    current_game_state.can_start_game = reached_minimum_number_of_players(current_game_state)
    record_event(current_game_state, Event.PLAYER_JOINED, f'{joining_player.name} joined the game',
                 str(joining_player.uuid))
    return current_game_state


def remove_player(current_game_state: GameState, player_uuid: str) -> GameState:
    if player_uuid not in current_game_state.player_dict:
        return current_game_state

    leaving_player = current_game_state.player_dict[player_uuid]
    current_game_state.player_order = [p for p in current_game_state.player_order if p.uuid != player_uuid]
    current_game_state.player_dict.pop(player_uuid, None)
    current_game_state.players_round_score.pop(player_uuid, None)
    current_game_state.players_overall_score.pop(player_uuid, None)
    current_game_state.players_and_hand.pop(player_uuid, None)
    current_game_state.player_levels.pop(player_uuid, None)
    current_game_state.current_friends_of_alpha = [uuid for uuid in current_game_state.current_friends_of_alpha if uuid != player_uuid]

    if current_game_state.hosting_player and str(current_game_state.hosting_player.uuid) == player_uuid:
        current_game_state.hosting_player = current_game_state.player_order[0] if current_game_state.player_order else None

    if current_game_state.current_alpha_player.player_uuid == player_uuid:
        current_game_state.current_alpha_player = PlayerPointer(index=0, player_uuid='')
    if current_game_state.current_player.player_uuid == player_uuid:
        current_game_state.current_player = PlayerPointer(index=0, player_uuid='')
    if current_game_state.leading_player.player_uuid == player_uuid:
        current_game_state.leading_player = PlayerPointer(index=0, player_uuid='')
    if current_game_state.winning_player_of_round.player_uuid == player_uuid:
        current_game_state.winning_player_of_round = PlayerPointer(index=0, player_uuid='')

    current_game_state.can_start_game = reached_minimum_number_of_players(current_game_state)
    record_event(current_game_state, Event.PLAYER_LEFT, f'{leaving_player.name} left the game',
                 str(leaving_player.uuid))
    return current_game_state


def add_deck_to_game(game_state: GameState, number_of_decks: int = 1):
    clear_deck(game_state)
    game_state.cards_in_deck.extend(build_deck(number_of_decks=number_of_decks))
    shuffle_deck(game_state.cards_in_deck)


def clear_deck(game_state: GameState):
    game_state.cards_in_deck = list()


def clear_players_hand(game_state: GameState):
    for player_uuid in game_state.players_and_hand:
        game_state.players_and_hand[player_uuid] = list()


def deal_to_players(game_state: GameState, cards_per_person: int = 5):
    for _ in range(cards_per_person):
        for player_uuid in game_state.players_and_hand:
            game_state.players_and_hand[player_uuid].append(game_state.cards_in_deck.pop())


def find_player(current_game_state: GameState, player_uuid: str) -> Tuple[int, Player]:
    for idx, p in enumerate(current_game_state.player_order):
        if p.uuid == player_uuid:
            return idx, p
    else:
        raise Exception("Can't fine Player with UUID: {}".format(player_uuid))


def set_player_as_alpha(current_game_state: GameState, player_uuid: str):
    _ , check_player = find_player(current_game_state, player_uuid)
    current_game_state.current_alpha_player.player_uuid = check_player.uuid


def is_player_an_alpha(current_game_state: GameState, player_uuid: str) -> bool:
    _ , check_player = find_player(current_game_state, player_uuid)
    return current_game_state.current_alpha_player.player_uuid == check_player.uuid


def set_player_as_leading_player(current_game_state: GameState, player_uuid: str):
    player_idx, check_player = find_player(current_game_state, player_uuid)
    current_game_state.leading_player.player_uuid = check_player.uuid
    current_game_state.leading_player.index = player_idx
    current_game_state.current_player.player_uuid = check_player.uuid
    current_game_state.current_player.index = player_idx


def set_current_player(current_game_state: GameState, player_uuid: str):
    player_idx, check_player = find_player(current_game_state, player_uuid)
    current_game_state.leading_player.player_uuid = check_player.uuid
    current_game_state.leading_player.index = current_game_state.current_player.index = player_idx


def set_winning_player_of_round(current_game_state: GameState, player_uuid: str):
    player_idx, check_player = find_player(current_game_state, player_uuid)
    current_game_state.winning_player_of_round.player_uuid = check_player.uuid
    current_game_state.winning_player_of_round.index = current_game_state.current_player.index = player_idx    


def set_game_state_trump(current_gs: GameState, new_trump_suit: Suit, new_trump_rank: Rank):
    current_gs.declare_trump.rank = new_trump_rank
    current_gs.declare_trump.suit = new_trump_suit


def next_person_turn(current_gs: GameState) -> Tuple[bool, Player]:
    number_of_players = len(current_gs.player_order)
    current_gs.current_player.index += 1
    if number_of_players == current_gs.current_player.index:
        current_gs.current_player.index = 0
    continue_round = current_gs.leading_player.index != current_gs.current_player.index
    return continue_round, current_gs.player_order[current_gs.current_player.index]


def play_cards_into_active_pile(current_gs: GameState, player_uuid: str, cards: list):
    """Add one player's play to the trick, recording who made it.

    The pile and its attribution are only ever grown together, so they cannot
    fall out of step and mislabel a card."""
    current_gs.cards_in_active_pile.extend(cards)
    current_gs.active_pile_player_uuids.extend([str(player_uuid)] * len(cards))


def clear_active_pile(current_gs: GameState):
    """Empty the trick pile and the attribution that belongs to it."""
    current_gs.cards_in_active_pile = list()
    current_gs.active_pile_player_uuids = list()


def reset_round(current_gs: GameState):
    current_gs.card_in_discard_pile.extend(current_gs.cards_in_active_pile)
    clear_active_pile(current_gs)
    set_player_as_leading_player(current_gs, player_uuid=current_gs.winning_player_of_round.player_uuid)
    set_current_player(current_gs, player_uuid=current_gs.winning_player_of_round.player_uuid)
    current_gs.winning_player_of_round.index = 0
    current_gs.winning_player_of_round.player_uuid = ''
    current_gs.leading_hand_of_subround = list()
    current_gs.current_hand_played = list()


def is_round_over(current_gs: GameState) -> bool:
    """Check if all players' hands are empty."""
    for player_uuid in current_gs.players_and_hand:
        if len(current_gs.players_and_hand[player_uuid]) > 0:
            return False
    return True


def reached_minimum_number_of_players(current_gs: GameState) -> bool:
    return len(current_gs.player_order) >= 5
