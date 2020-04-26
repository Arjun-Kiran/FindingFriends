from typing import List
from src.Game.Modules.CardConstants import Suit
from src.Game.Components.GameState import GameState
from src.Game.Components.Player import Player
from src.Game.Components.Card import Card


def legal_cards_to_play(game_state: GameState, player: Player) -> List[Card]:
    """
    Legal Cards for a Player can play with their current hand
    :param game_state:
    :param player:
    :return:
    """
    if game_state.leading_suit is Suit.NONE:
        return player.hand
    cards_can_play = [card for card in player.hand if game_state.leading_suit == card.suit]
    return cards_can_play if len(cards_can_play) > 0 else player.hand


def who_wins_the_round(game_state: GameState) -> str:
    return ''

