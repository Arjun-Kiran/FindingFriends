from typing import List, Dict, Optional, Set, Tuple
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


def alpha_team_uuids(current_gs: GameState) -> Set[str]:
    """Everyone currently known to be on the trump maker's team.

    Friends are only known once they play a called card, so this set grows
    during a round. Before that they are indistinguishable from attackers.
    """
    team = set(current_gs.current_friends_of_alpha)
    alpha_uuid = current_gs.current_alpha_player.player_uuid
    if alpha_uuid:
        team.add(alpha_uuid)
    return team


def attacker_team_uuids(current_gs: GameState) -> Set[str]:
    """Everyone not currently known to be on the trump maker's team."""
    alpha_team = alpha_team_uuids(current_gs)
    return {player.uuid for player in current_gs.player_order if player.uuid not in alpha_team}


def team_round_points(current_gs: GameState) -> Tuple[int, int]:
    """Round card points as (alpha team total, attacker total).

    Points are tracked per player as tricks are won, but they belong to a team
    — teammates share one total. Only the attackers' total decides the round.
    """
    scores = current_gs.players_round_score
    alpha_points = sum(scores.get(uuid, 0) for uuid in alpha_team_uuids(current_gs))
    attacker_points = sum(scores.get(uuid, 0) for uuid in attacker_team_uuids(current_gs))
    return alpha_points, attacker_points


def max_alpha_team_size(num_players: int) -> int:
    """Maximum alpha team size (alpha + friends) per the rules table."""
    table = {5: 2, 6: 3, 7: 3, 8: 4, 9: 4, 10: 5, 11: 5, 12: 6}
    return table.get(num_players, 2)


# HR-6. Deck counts the bands are defined for. The game itself only ever deals
# 3 to 6 (HR-1); 2 is here because the source rules define it and the boundary
# tests exercise it.
SUPPORTED_PACKS = (2, 3, 4, 5, 6)


class ScoringError(ValueError):
    """A round that cannot be scored, because the inputs are not a round.

    Raised rather than guessed at. Every one of these means a bug somewhere
    upstream — card points arrive in fives and the deck count comes from the
    table size — and a wrong promotion is far harder to notice after the fact
    than an error at the moment it happens.
    """


def score_round(num_packs: int, attacker_points: int) -> Tuple[str, int]:
    """Which side the round promotes, and by how many levels.

    HR-6, and the whole of it: only the attackers' captured points decide a
    round. The alpha team's total is not consulted, because the two always sum
    to the points in play — saying one says the other.

    The bands are fifths of the points in play. With `U` = a fifth (20 per
    pack) and `N` = the neutral point (two fifths, 40 per pack):

        p == 0       alpha team +3   a shutout, and only a shutout
        0 < p < U    alpha team +2
        U <= p < N   alpha team +1
        p == N       nobody moves    one exact value, not a band
        N < p        attackers, one level per fifth begun past N, capped at 3

    The two sides are deliberately not symmetric at the edges. The alpha bands
    are closed at the bottom (exactly U is +1, not +2) and the attacker bands
    are closed at the top (exactly N + U is +1, not +2): a side gains a level
    for going *past* a fifth, never for landing on it.

    `attacker_points` may exceed the points in play. The kitty counts double
    for the attackers when they take the last trick, which can carry them over
    the raw card total; anything past N + 2U is simply +3.

    Returns ('trump_maker' | 'attacker' | 'none', levels). 'trump_maker' is the
    alpha team, kept as the wire value the round summary already speaks.
    """
    if num_packs not in SUPPORTED_PACKS:
        raise ScoringError(f'{num_packs} packs is not a scorable deck count')
    if isinstance(attacker_points, bool) or not isinstance(attacker_points, int):
        raise ScoringError(f'attacker points must be a whole number, not {attacker_points!r}')
    if attacker_points < 0:
        raise ScoringError(f'attacker points cannot be negative: {attacker_points}')
    if attacker_points % 5:
        raise ScoringError(f'card points come in fives: {attacker_points}')

    unit = 20 * num_packs
    neutral = 2 * unit

    if attacker_points == 0:
        return 'trump_maker', 3
    if attacker_points < unit:
        return 'trump_maker', 2
    if attacker_points < neutral:
        return 'trump_maker', 1
    if attacker_points == neutral:
        return 'none', 0

    # A level per fifth begun past the neutral point: ceiling division, done in
    # integers so no band edge can land on the wrong side of a float.
    surplus = attacker_points - neutral
    return 'attacker', min(3, -(-surplus // unit))


def scoring_bands(num_packs: int) -> List[Tuple[int, Optional[int], str, int]]:
    """The HR-6 ladder for this deck count, as rows to show a player.

    Each row is (low, high, side, levels); `high` is None on the last row,
    which is open-ended because the doubled kitty can carry the attackers past
    the points in play.

    Walked out of score_round rather than written down a second time. A table
    on screen that disagrees with the engine is worse than no table at all, and
    the only way to be sure it cannot is to ask the engine. Cheap: 121 calls at
    the largest deck count, and only when a view is built.
    """
    rows: List[Tuple[int, Optional[int], str, int]] = []
    for points in range(0, 100 * num_packs + 1, 5):
        side, levels = score_round(num_packs, points)
        if rows and rows[-1][2:] == (side, levels):
            low, _, side_before, levels_before = rows[-1]
            rows[-1] = (low, points, side_before, levels_before)
        else:
            rows.append((points, points, side, levels))
    if rows:
        low, _, side, levels = rows[-1]
        rows[-1] = (low, None, side, levels)
    return rows


def promotion_for_round(num_packs: int, alpha_points: int, attacker_points: int,
                        scaled: bool = True) -> Tuple[str, int]:
    """Which side won the round, and how many levels each of its players climbs.

    `scaled` is GameSettings.scaled_level_promotion, on by default: the banded
    ladder above, which is HR-6 and what a table that changes nothing plays.

    Turned off, the round is decided by simply comparing the two totals — more
    points wins, by exactly one level, and an exact tie moves nobody. That was
    HR-6 itself until the bands replaced it, and it stays available for a table
    that wants every round to count the same.
    """
    if scaled:
        return score_round(num_packs, attacker_points)
    if alpha_points > attacker_points:
        return 'trump_maker', 1
    if attacker_points > alpha_points:
        return 'attacker', 1
    return 'none', 0


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
