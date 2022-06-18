from typing import List
from Game.Components.GameState import GameState
from Game.Components.Player import Player
from Game.Components.Card import Card, Rank


def point_card_pile(card_pile: List[Card]) -> int:
    total_points = 0
    for card in card_pile:
        if card.rank in [Rank.KING, Rank.TEN]:
            total_points += 10

        if card.rank in [Rank.FIVE]:
            total_points += 5
    
    return total_points


def calculate_rounds_points(current_gs: GameState):
    leading_uuid = current_gs.winning_player_of_round["player_uuid"]
    points_won = point_card_pile(current_gs.cards_in_active_pile)
    current_gs.players_round_score[leading_uuid] += points_won
