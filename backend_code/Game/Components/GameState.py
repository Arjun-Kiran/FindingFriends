from pydantic import BaseModel
from typing import Dict, List, Optional
from uuid import uuid4
from Game.Components.Card import Card
from Game.Modules.CardConstants import Rank, Suit
from Game.Modules.EventEnum import EventItem, GameEventState
from Game.Components.Player import Player, PlayerPointer


class DeclareTrump(BaseModel):
    rank: Optional[Rank]
    suit: Optional[Suit]

class DeclareCallingCard(BaseModel):
    suit: Suit
    rank: Rank
    order: int
    # The player who satisfied this particular rule, once someone has. Held per
    # rule rather than only in current_friends_of_alpha, so a table with
    # several called cards can see which one outed whom. Public knowledge —
    # a revealed friend is revealed to everyone.
    revealed_by: str = ''


class GameSettings(BaseModel):
    """House rules the host can change in the lobby, before cards are dealt.

    Every one defaults to the game as ZhaoPengyou_Rules.md describes it, so a
    table that never opens the settings plays the standard game. Each field is
    a permission: turning it on loosens a rule rather than adding one.

    Old saved games have no settings key at all, which is why every field has a
    default — they load as a standard game.
    """
    # Called cards must not be trumps (Main.handle_call_friends). Turning this
    # on lets the alpha call a trump, which makes the friend much harder to
    # find because the card is one nobody wants to spend early.
    trumps_can_be_called: bool = False
    # Normally the alpha must declare their own level, in a suit they hold.
    # Turning this on lets them name any suit and any rank at all.
    free_trump_choice: bool = False
    # Normally the host is the first alpha. Turning this on draws the first
    # alpha from the table instead, so hosting is not an advantage.
    random_first_alpha: bool = False


class GameState(BaseModel):
    session: str = str(uuid4())
    game_event_state: GameEventState = GameEventState.NOT_AVAILABLE
    game_code: str = ''
    can_start_game: bool = False
    settings: GameSettings = GameSettings()
    hosting_player: Optional[Player] = None
    current_alpha_player: PlayerPointer = PlayerPointer(index=0, player_uuid='')
    # Players
    current_friends_of_alpha: List[str] = list()
    player_dict: Dict[str, Player] = dict()
    player_order: List[Player] = list()

    current_player: PlayerPointer = PlayerPointer(index=0, player_uuid='')
    leading_player: PlayerPointer = PlayerPointer(index=0, player_uuid='')
    winning_player_of_round: PlayerPointer = PlayerPointer(index=0, player_uuid='')

    players_and_hand: Dict[str, List[Card]] = dict()
    players_round_score: Dict[str, int] = dict()
    players_overall_score: Dict[str, int] = dict()

    # Cards in and out of play
    cards_in_deck: List[Card] = list()
    cards_in_active_pile: List[Card] = list()
    # Who played each card in cards_in_active_pile — one uuid per card, in the
    # same order. Stored rather than derived from seat order: the positional
    # arithmetic only holds while every play in a trick is the same size, and
    # getting it wrong would put the wrong name under a card.
    # Always mutate through play_cards_into_active_pile/clear_active_pile.
    active_pile_player_uuids: List[str] = list()
    card_in_discard_pile: List[Card] = list()
    card_out_of_play: List[Card] = list()
    leading_hand_of_subround: List[Card] = list()
    current_hand_played: List[Card] = list()
    declare_trump: DeclareTrump = DeclareTrump(rank=None, suit=None)

    friend_calling_cards: List[DeclareCallingCard] = list()
    all_friends_found: bool = False
    player_levels: Dict[str, int] = dict()
    last_trick_winner: str = ''
    # Round result info (populated at end of round)
    round_winner_side: str = ''  # 'trump_maker', 'defender', or 'none'
    round_defender_points: int = 0
    round_promotion_levels: int = 0
    round_promoted_players: List[str] = list()  # UUIDs of promoted players
    game_winner: str = ''  # UUID of player who passed Ace (game over)
    # Typed so events survive the trip through the database as EventItems.
    # Left bare, pydantic hands them back as plain dicts on load, and the list
    # ends up holding both shapes once a new event is appended.
    events: List[EventItem] = list()
