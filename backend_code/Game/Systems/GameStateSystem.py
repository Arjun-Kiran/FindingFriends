
from typing import Tuple
from uuid import uuid4
from Game.Components.GameState import GameState
from Game.Components.Player import Player
from Game.Modules.CardConstants import Suit, Rank
from Game.Systems.DeckSystem import build_deck, shuffle_deck
from Game.Systems.EventSystem import build_event, Event


def generate_player(name) -> Player:
    new_player = Player(name=name)
    new_player.uuid = str(uuid4())
    return new_player


def add_player(current_game_state: GameState, joining_player: Player) -> GameState:
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
    current_game_state.events.append(build_event(Event.PLAYER_JOINED, f'New player has joined | Name: {joining_player.name} , UUID: {uuid_str}'))
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
    current_game_state.events.append(build_event(Event.PLAYER_LEFT, f'Player left | Name: {leaving_player.name} , UUID: {player_uuid}'))
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


def reset_round(current_gs: GameState):
    current_gs.card_in_discard_pile.extend(current_gs.cards_in_active_pile)
    current_gs.cards_in_active_pile = list()
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
