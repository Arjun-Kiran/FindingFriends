from typing import List, Dict, Set, Tuple
from Game.Components.GameState import GameState
from Game.Components.Player import Player
from Game.Components.Card import Card, Rank
from Game.Systems.DeckSystem import number_of_decks


# Ordered list of playable levels (TWO through ACE)
LEVEL_ORDER = [
    Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX, Rank.SEVEN,
    Rank.EIGHT, Rank.NINE, Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING, Rank.ACE
]


def point_card_pile(card_pile: List[Card]) -> int:
    total_points = 0
    for card in card_pile:
        if card.rank in [Rank.KING, Rank.TEN]:
            total_points += 10

        if card.rank in [Rank.FIVE]:
            total_points += 5

    return total_points


def calculate_rounds_points(current_gs: GameState):
    leading_uuid = current_gs.winning_player_of_round.player_uuid
    points_won = point_card_pile(current_gs.cards_in_active_pile)
    current_gs.players_round_score[leading_uuid] += points_won


def max_alpha_team_size(num_players: int) -> int:
    """Maximum alpha team size (alpha + friends) per the rules table."""
    table = {5: 2, 6: 3, 7: 3, 8: 4, 9: 4, 10: 5, 11: 5, 12: 6}
    return table.get(num_players, 2)


def calculate_level_promotion(num_packs: int, defender_points: int,
                               alpha_team_actual: int, alpha_team_max: int) -> Tuple[str, int]:
    """
    Determine which team wins and by how many levels.

    Returns (winning_side, levels) where:
      winning_side = 'trump_maker' or 'defender' or 'none'
      levels = number of levels to promote (0 means neither side wins)

    Based on the scoring tables from the rules:
      Points per pack: 0 → T+3, 5-35 → T+2, 40-75 → T+1,
                       80-115 → 0, 120-155 → D+1, 160-195 → D+2, 200 → D+3
      With bonus for undersized alpha team.
    """
    pts_per_pack = 200  # base points per pack (K=10, 10=10, 5=5) × cards per pack

    # Scale thresholds by number of packs (the rules tables show per-pack ranges)
    # 2 packs: 0, 5-35, 40-75, 80-115, 120-155, 160-195, 200
    # 3 packs: 0, 5-55, 60-115, 120-175, 180-235, 240-295, 300
    # The pattern: each tier spans (pts_per_pack * num_packs) / ~5.33 roughly
    # Let's use the exact thresholds from the rules
    total_pts = pts_per_pack * num_packs

    # Thresholds (defender points): [0, tier1_end, tier2_end, tier3_end, tier4_end, tier5_end, total]
    # The tiers from rules for 2 packs: 0, 5-35, 40-75, 80-115, 120-155, 160-195, 200
    # For N packs, scale proportionally
    if num_packs == 2:
        thresholds = [(0, 0), (1, 35), (36, 75), (76, 115), (116, 155), (156, 195), (196, 400)]
    elif num_packs == 3:
        thresholds = [(0, 0), (1, 55), (56, 115), (116, 175), (176, 235), (236, 295), (296, 600)]
    elif num_packs == 4:
        thresholds = [(0, 0), (1, 75), (76, 155), (156, 235), (236, 315), (316, 395), (396, 800)]
    else:
        # Fallback: scale from 2-pack thresholds
        scale = num_packs / 2
        thresholds = [
            (0, 0),
            (1, int(35 * scale)),
            (int(36 * scale), int(75 * scale)),
            (int(76 * scale), int(115 * scale)),
            (int(116 * scale), int(155 * scale)),
            (int(156 * scale), int(195 * scale)),
            (int(196 * scale), int(400 * scale)),
        ]

    # Results per tier: (side, base_levels)
    # T+3, T+2, T+1, 0, D+1, D+2, D+3
    tier_results = [
        ('trump_maker', 3),
        ('trump_maker', 2),
        ('trump_maker', 1),
        ('none', 0),
        ('defender', 1),
        ('defender', 2),
        ('defender', 3),
    ]

    # Find which tier the defender_points fall into
    side = 'none'
    base_levels = 0
    for i, (low, high) in enumerate(thresholds):
        if low <= defender_points <= high:
            side, base_levels = tier_results[i]
            break
    else:
        # If defender_points exceeds all thresholds
        side, base_levels = 'defender', 3

    if side == 'none':
        return ('none', 0)

    # Bonus for undersized alpha team (only when trump makers win)
    if side == 'trump_maker':
        missing_players = alpha_team_max - alpha_team_actual
        if missing_players > 0:
            base_levels = base_levels * (1 + missing_players)

    return (side, base_levels)


def advance_level(current_level_value: int, levels: int) -> Tuple[int, bool]:
    """
    Advance a player's level by the given number of levels.
    Returns (new_level_value, passed_ace) where passed_ace means the player
    has gone beyond Ace and wins the game.
    """
    new_value = current_level_value + levels
    max_level = Rank.ACE.value  # 13
    if new_value > max_level:
        return max_level, True
    return new_value, False


def rank_from_value(value: int) -> Rank:
    """Convert a rank integer value back to a Rank enum."""
    for r in LEVEL_ORDER:
        if r.value == value:
            return r
    return Rank.ACE
