from enum import Enum
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


class Watcher(BaseModel):
    """Someone watching the game without a seat. See HR-8 in HouseRules.md."""
    uuid: str
    name: str = ''
    # When they started watching — or, for a player turned watcher, when that
    # happened. Epoch seconds.
    joined_at: float = 0


class Vacancy(BaseModel):
    """A seat whose player is not at the table right now (HR-8)."""
    # When they dropped or left. Epoch seconds.
    since: float = 0
    # Nobody is coming back to it: they pressed Leave, or were away so long
    # they lost the seat. False while they still have time to reconnect.
    left: bool = False
    # Whether the table has been told the seat is open, so it is said once.
    announced: bool = False


class SeatRequest(BaseModel):
    """A watcher asking to play (HR-8)."""
    watcher_uuid: str
    # The open seat they volunteered for, or '' to join as an extra player when
    # the next round starts.
    seat_uuid: str = ''
    # Joining only. Approving a volunteer seats them on the spot, so a takeover
    # is never left approved and waiting.
    approved: bool = False
    # The level an approved joiner starts on, as a Rank value. Set by the host.
    level: int = Rank.TWO.value


class AlphaDeclarationOrder(str, Enum):
    """The order the alpha works through trump, the kitty and the friend call
    before the first trick. Values are what the lobby sends and stores."""
    TRUMP_FRIENDS_KITTY = 'trump-friends-kitty'
    TRUMP_KITTY_FRIENDS = 'trump-kitty-friends'
    KITTY_TRUMP_FRIENDS = 'kitty-trump-friends'


class GameSettings(BaseModel):
    """House rules the host can change in the lobby, before cards are dealt.

    Most start off, which is the game as HouseRules.md describes it — the
    traditional game in ZhaoPengyou_Rules.md wherever no house rule says
    otherwise. Two start on — random_first_alpha and hide_scores_until_round_end
    — so a table that never opens the settings draws for its first alpha and
    plays with the running totals withheld. That pair is HR-9. Most are a
    permission — turning one on loosens a rule rather than adding one — but
    hide_scores_until_round_end instead withholds something the standard game
    shows, so read each field's own note rather than assuming the direction.

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
    # On by default (HR-9): the first alpha is drawn from the table, so hosting
    # is not an advantage. This is also the traditional starter — ZhaoPengyou
    # draws for the first deal. Turning it off gives the seat to the host, which
    # is what this game used to do, not what the traditional rules say.
    random_first_alpha: bool = True
    # Traditionally the running card-point totals are on screen all round. On by
    # default here, which withholds them until the round ends, so the table has
    # to keep count from the cards it has seen; turn it off to put them back on
    # screen. Enforced in Views/PlayerView.py rather
    # than in the client: the numbers must not be in the payload at all, or
    # anyone with a devtools console is playing a different game to everyone
    # else. The round summary shows the full totals either way.
    hide_scores_until_round_end: bool = True
    # HR-6: normally the side with more card points wins the round and climbs
    # exactly one level; a tie moves nobody. Turning this on brings back the
    # traditional scoring — the defenders' points against the bands, draws,
    # up to three levels for a margin, multiplied for a short-handed alpha
    # team. Read in
    # Main.handle_end_of_round via PointSystem.promotion_for_round.
    scaled_level_promotion: bool = False
    # HR-7: the order of the alpha's opening steps. Not a switch like the rest
    # but a choice of three; the default is the traditional trump, kitty, then
    # friends. Read in Main.advance_alpha_phase.
    alpha_declaration_order: AlphaDeclarationOrder = AlphaDeclarationOrder.TRUMP_KITTY_FRIENDS


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
    # Secret token -> the uuid it acts for: a seat in player_dict, or a watcher.
    # A uuid is on every screen and proves nothing; a token is what a browser
    # shows the server to say who it is. Server-side only: never copy it into a
    # PlayerView. Change it through issue_token, revoke_tokens and
    # repoint_tokens in GameStateSystem.
    tokens: Dict[str, str] = dict()
    # HR-8. Everyone watching, by uuid.
    watchers: Dict[str, Watcher] = dict()
    # Seats whose player is away or gone, by seat uuid. See SeatSystem.
    vacancies: Dict[str, Vacancy] = dict()
    # Watchers asking to play, oldest first. At most one each.
    seat_requests: List[SeatRequest] = list()
    # When fewer than 5 players were last left connected, or 0 while there are
    # enough; and how many warnings the table has had since.
    short_handed_since: float = 0
    short_handed_warnings: int = 0

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
