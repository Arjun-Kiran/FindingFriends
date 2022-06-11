from dataclasses import dataclass
from typing import Dict, List
from uuid import uuid4
from Game.Components.Card import Card, card_list_to_str_list
from Game.Modules.CardConstants import Rank, Suit
from Game.Components.Player import Player

class GameState():
    def __init__(self) -> None:
        self.session: str = str(uuid4())

        # Players
        self.current_alpha_player: str = ''
        self.current_friends_of_alpha: List[str] = list()
        self.player_order: List[Player] = list()
        self.current_player_idx: int = 0
        self.players_and_hand: Dict[str, List[Card]] = dict()
        self.players_round_score: Dict[str, int] = dict()
        self.players_overall_score: Dict[str, int] = dict()

        # Cards in and out of play
        self.cards_in_deck: List[Card] = list()
        self.cards_in_active_pile: List[Card] = list()
        self.card_in_discard_pile: List[Card] = list()
        self.card_out_of_play: List[Card] = list()
        self.leading_hand_of_subround: List[Card] = list()
        self.current_hand_played: List[Card] = list()
        self.declare_trump_rank: Rank = None
        self.declare_trump_suite: Suit = None

        self.friend_calling_cards: str = ''


def game_state_str(current_game_state: GameState) -> str:
    output = '''
    Session Id: {session_id}
    Current Alpha: {current_alpha}
    Player List: {player_list}
    Player Score: {player_score}
    Player Overall Score: {player_overall_score}
    Number Of Cards In Deck: {num_in_deck}
    '''.format(session_id = current_game_state.session,
               current_alpha = current_game_state.current_alpha_player,
               player_list = current_game_state.player_order,
               player_score = current_game_state.players_round_score,
               player_overall_score = current_game_state.players_overall_score,
               num_in_deck = len(current_game_state.cards_in_deck)
               )

    return output


def player_view_state_str(current_game_state: GameState, player_uuid: str) -> str:
    player_object = find_player(current_game_state, player_uuid)
    hand_list_str = card_list_to_str_list(current_game_state.players_and_hand[player_uuid])

    return '''
    Player View
    ------------------
    Player Name: {player_name}
    Player UUID: {player_uuid}
    Player Overall Score: {player_overall_score}
    Player Round Score: {player_round_score}
    Number Of Cards In Deck: {num_in_deck}
    Player Hand: {player_hand}
    '''.format(player_name=player_object.name,
             player_uuid = player_object.uuid,
             player_overall_score = current_game_state.players_overall_score[player_uuid],
             player_round_score = current_game_state.players_round_score[player_uuid],
             player_hand = hand_list_str,
             num_in_deck = len(current_game_state.cards_in_deck))
    

def number_of_players(current_game_state: GameState) -> int:
    return len(current_game_state.player_order)


def find_player(current_game_state: GameState, player_uuid: str) -> Player:
    for p in current_game_state.player_order:
        if p.uuid == player_uuid:
            return p
    else:
        raise Exception("Can't fine Player with UUID: {}".format(player_uuid))






    










    # def __init__(self):
    #     super().__init__()
    #     self.game_type: GameType = GameType.NO_GAME
    #     # Player
    #     self.score_map: Dict[str, int] = dict()
    #     self.player_map: Dict[str, Player] = dict()

    #     # Deck
    #     self.deck: List[Card] = list()
    #     self.discard_pile: List[Card] = list()

    #     # Starting Rules
    #     self.trump_suit: Suit = Suit.SPADE
    #     self.trump_rank: Rank = Rank.TWO

    #     # Round action
    #     self.leading_suit: Suit = Suit.NONE
    #     self.player_order: List[str] = list()
    #     self.player_cards_played: Dict[str, List[Card]] = dict()
    #     self.starting_player_idx: int = 0
    #     self.current_player_turn_idx: int = 0

    # @property
    # def deck_size(self) -> int:
    #     return len(self.deck)

    # @property
    # def number_of_players(self) -> int:
    #     return len(self.player_map.keys())

    # @property
    # def players_turn(self) -> str:
    #     try:
    #         return self.player_order[self.current_player_turn_idx]
    #     except IndexError:
    #         return ''

    # @property
    # def starting_player(self) -> str:
    #     try:
    #         return self.player_order[self.starting_player_idx]
    #     except IndexError:
    #         return ''
