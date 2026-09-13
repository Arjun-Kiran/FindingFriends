import time
from enum import Enum
from pydantic import BaseModel
from typing import Dict, List, Optional, Set
from Game.Components.GameState import GameState, DeclareTrump, DeclareCallingCard, GameSettings, SeatRequest, Vacancy, Watcher
from Game.Components.Card import Card
from Game.Components.Player import Player
from Game.Systems.GameStateSystem import is_player_an_alpha
from Game.Systems.DecisionSystem import playable_cards
from Game.Systems.SeatSystem import CLOSE_AFTER_SECONDS, GRACE_SECONDS, open_seats, round_held_up
from Game.Systems.TeamSystem import number_of_cards_to_call_friends
from Game.Systems.PointSystem import alpha_team_uuids, team_round_points
from Game.Modules.EventEnum import EventItem, GameEventState
from Game.Modules.Avatars import ANIMAL_AVATARS


def _serialize_for_json(obj):
    """Recursively convert a Pydantic .model_dump() output to JSON-safe types.
    Enum objects are converted to their .name (string) so the frontend
    sees 'HEART' instead of 48.
    """
    if isinstance(obj, Enum):
        return obj.name if not isinstance(obj, str) else obj.value
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(v) for v in obj]
    return obj


class PlayerView(BaseModel):
    name: str = ''
    uuid: str = ''
    # This player's own avatar. Everyone else's rides along on player_list.
    avatar: str = ''
    # The whole catalog, so the lobby picker and the server agree on what is
    # offered. Which ones are taken is derivable from player_list.
    avatar_choices: List[str] = list()
    can_start_game: bool = False
    # The house rules this table is playing. Public — everyone needs to know
    # what game they are in, not just whoever set it.
    settings: GameSettings = GameSettings()
    # Who the alpha and the host are, for everyone — not just "is it me".
    # Both are public knowledge at the table, and the players bar needs them
    # to put the crown on the right player.
    alpha_uuid: str = ''
    host_uuid: str = ''
    my_turn: bool = False
    hosting: bool = False
    is_alpha: bool = False
    on_alpha_team: bool = False
    number_of_players: int = 0
    current_player: Optional[Player] = None
    leading_player: Optional[Player] = None
    winning_player_of_round: Optional[Player] = None
    player_list: List[Player] = list()
    player_hand: List[Card] = list()
    # One flag per card in player_hand: could that card be part of a legal play
    # against the current lead? A hint about the player's own hand, sent to
    # everyone during a round so a player can plan while they wait — the server
    # still refuses an illegal play either way. Empty outside a round.
    playable_hand_cards: List[bool] = list()
    players_round_score: Dict[str, int] = dict()
    players_overall_score: Dict[str, int] = dict()
    # Round points belong to a team, not a player — teammates share one total.
    alpha_team_points: int = 0
    defender_team_points: int = 0
    my_team_points: int = 0
    # True while the hide_scores_until_round_end house rule is withholding the
    # six fields above. They are zeroed rather than dropped, so every client
    # keeps the shape it expects — which is exactly why this flag exists: a
    # zero is a real score too, and without it the client cannot tell a table
    # that has taken no points from one that is not being told.
    scores_hidden: bool = False
    # Everyone level-pegging at the top of the round's card points, or empty
    # while the table is still scoreless. Survives scores_hidden on purpose —
    # see the note in _table_view.
    top_scorer_uuids: List[str] = list()
    game_event_state: GameEventState = GameEventState.NOT_AVAILABLE
    game_code: str = ''
    declare_trump: DeclareTrump = DeclareTrump(rank=None, suit=None)
    cards_in_active_pile: List[Card] = list()
    # Who played each card above, one uuid per card in the same order, so the
    # table can see whose card is whose during a trick.
    active_pile_player_uuids: List[str] = list()
    leading_hand_of_subround: List[Card] = list()
    kitty_size: int = 0
    # What the alpha buried. Private while the round is played — naming it
    # would hand the defenders the round — so only filled once it has ended.
    kitty_cards: List[Card] = list()
    my_level: int = 0
    player_levels: Dict[str, int] = dict()
    friend_calling_cards: List[DeclareCallingCard] = list()
    num_friends_to_call: int = 0
    revealed_friends: List[str] = list()
    # Team totals give away hidden partnerships, so they stay hidden until
    # every friend has revealed themselves by playing a called card.
    all_friends_found: bool = False
    round_winner_side: str = ''
    round_defender_points: int = 0
    round_promotion_levels: int = 0
    round_promoted_players: List[str] = list()
    game_winner: str = ''
    # Uuids of players in this game with no live socket right now. Their seats
    # are held — hands are dealt and turn order depends on them — so this is
    # what lets the table see who they are waiting on.
    disconnected_players: List[str] = list()
    events: List[EventItem] = list()

    # --- HR-8: watching, and seats changing hands ---
    # Someone watching rather than playing. Their view is the table's, and no
    # more: no hand, and nothing a player at the table is not also shown.
    is_watcher: bool = False
    # Everyone watching right now.
    watchers: List[Watcher] = list()
    # Seats whose player is away or gone, by seat uuid, with when that
    # happened — what the countdown beside a name is drawn from. `server_time`
    # is when this view was built, so a client can run the countdown on its own
    # clock without trusting that clock to agree with the server's.
    seat_vacancies: Dict[str, Vacancy] = dict()
    seat_grace_seconds: int = GRACE_SECONDS
    server_time: float = 0
    # Of those, the seats that are open now: the player left, or their time ran out.
    open_seats: List[str] = list()
    # A round is in play and an open seat is holding it up, so the host may end
    # it as a draw.
    round_held_up: bool = False
    # Watchers asking to play — for an open seat, or from the next round.
    seat_requests: List[SeatRequest] = list()
    # When the room closes for want of players, or 0 while there are enough.
    room_closes_at: float = 0

    def to_json_dict(self) -> dict:
        """Return a dict safe for JSON serialization (enums as name strings)."""
        return _serialize_for_json(self.model_dump())


def _table_view(current_game_state: GameState, connected_uuids: Optional[Set[str]],
                now: float) -> PlayerView:
    """Everything about the game the whole table is shown.

    The one place a view starts from, for a player and a watcher alike. What
    belongs to a single player — a hand, a turn, a side — is added on top in
    player_view_state, so a watcher built from this alone cannot be sent any
    of it."""
    view = PlayerView()
    view.avatar_choices = list(ANIMAL_AVATARS)
    view.game_event_state = current_game_state.game_event_state
    view.game_code = current_game_state.game_code
    view.alpha_uuid = str(current_game_state.current_alpha_player.player_uuid or '')
    view.host_uuid = (str(current_game_state.hosting_player.uuid)
                      if current_game_state.hosting_player else '')
    view.number_of_players = len(current_game_state.player_order)
    view.players_round_score = current_game_state.players_round_score
    view.players_overall_score = current_game_state.players_overall_score
    view.can_start_game = current_game_state.can_start_game
    view.settings = current_game_state.settings
    view.player_list = current_game_state.player_order
    view.declare_trump = current_game_state.declare_trump
    view.cards_in_active_pile = current_game_state.cards_in_active_pile
    view.active_pile_player_uuids = current_game_state.active_pile_player_uuids
    view.leading_hand_of_subround = current_game_state.leading_hand_of_subround
    view.kitty_size = len(current_game_state.cards_in_deck)
    view.player_levels = current_game_state.player_levels
    view.friend_calling_cards = current_game_state.friend_calling_cards
    view.revealed_friends = current_game_state.current_friends_of_alpha
    view.all_friends_found = current_game_state.all_friends_found
    view.events = current_game_state.events
    if connected_uuids is not None:
        view.disconnected_players = [
            uuid for uuid in current_game_state.player_dict
            if uuid not in connected_uuids
        ]
    num_players = len(current_game_state.player_order)
    view.num_friends_to_call = number_of_cards_to_call_friends(num_players) if num_players >= 5 else 0

    # Team point totals — teammates see the same number
    alpha_points, defender_points = team_round_points(current_game_state)
    view.alpha_team_points = alpha_points
    view.defender_team_points = defender_points

    # Who is ahead on card points, for the flame on their name. Read off the
    # real scores before _withhold_scores takes them away, and deliberately left
    # standing when it does: the blind table is told who is winning but never
    # by how much, which is the whole trade the house rule offers.
    #
    # Nobody at all until a point has actually been taken. Every player starts
    # a round on nothing, and "everyone is tied for first" is not a fact worth
    # setting five names on fire over.
    #
    # These are individual trick points, the same figures the visible bar shows
    # player by player before the friends are out, so this says nothing about
    # who is on which side. Sides stay the round's secret.
    round_scores = current_game_state.players_round_score
    best_score = max(round_scores.values(), default=0)
    if (current_game_state.game_event_state == GameEventState.ROUND_STARTED
            and best_score > 0):
        view.top_scorer_uuids = [uuid for uuid, points in round_scores.items()
                                 if points == best_score]

    # Round result info
    view.round_winner_side = current_game_state.round_winner_side
    view.round_defender_points = current_game_state.round_defender_points
    view.round_promotion_levels = current_game_state.round_promotion_levels
    view.round_promoted_players = current_game_state.round_promoted_players
    view.game_winner = current_game_state.game_winner
    if current_game_state.game_event_state == GameEventState.ROUND_ENDED:
        view.kitty_cards = current_game_state.card_out_of_play

    current_player_uuid = current_game_state.current_player.player_uuid
    if current_player_uuid and current_player_uuid in current_game_state.player_dict:
        view.current_player = current_game_state.player_dict[current_player_uuid]

    leading_uuid = current_game_state.leading_player.player_uuid
    if leading_uuid and leading_uuid in current_game_state.player_dict:
        view.leading_player = current_game_state.player_dict[leading_uuid]

    winning_uuid = current_game_state.winning_player_of_round.player_uuid
    if winning_uuid and winning_uuid in current_game_state.player_dict:
        view.winning_player_of_round = current_game_state.player_dict[winning_uuid]

    # HR-8. Watchers who are not here are left off: a list of people who are
    # not watching is not who is watching.
    view.watchers = [watcher for watcher in current_game_state.watchers.values()
                     if connected_uuids is None or watcher.uuid in connected_uuids]
    view.seat_vacancies = current_game_state.vacancies
    view.server_time = now
    view.open_seats = open_seats(current_game_state, now)
    view.round_held_up = round_held_up(current_game_state, now)
    view.seat_requests = current_game_state.seat_requests
    if current_game_state.short_handed_since:
        view.room_closes_at = current_game_state.short_handed_since + CLOSE_AFTER_SECONDS
    return view


def _withhold_scores(view: PlayerView, current_game_state: GameState):
    """The house rule that keeps the running totals off the table until the
    round is done. Only while the round is actually being played: the whole
    point is that the count arrives at the end, so ROUND_ENDED and everything
    after it — the round summary, the next lobby — report in full.

    Applied last, below every score assignment, rather than at each of them:
    the totals reach a view from several places, and one added later must not
    be able to reopen the leak. round_defender_points is exempt only because
    the round reset zeroes it and nothing fills it in until the round is over.
    """
    if (current_game_state.settings.hide_scores_until_round_end
            and current_game_state.game_event_state == GameEventState.ROUND_STARTED):
        view.scores_hidden = True
        view.players_round_score = {}
        view.players_overall_score = {}
        view.alpha_team_points = 0
        view.defender_team_points = 0
        view.my_team_points = 0


def player_view_state(current_game_state: GameState, player_uuid: str,
                      connected_uuids: Optional[Set[str]] = None,
                      now: Optional[float] = None) -> PlayerView:
    """Build one player's view of the game.

    `connected_uuids` is who currently holds a live socket. Pass None when
    connection state isn't known (tests, tooling) and everyone is treated as
    present. `now` is the time the seat countdowns are measured at."""
    player_object = current_game_state.player_dict[player_uuid]
    view = _table_view(current_game_state, connected_uuids, time.time() if now is None else now)
    view.uuid = str(player_object.uuid)
    view.name = str(player_object.name)
    view.avatar = str(player_object.avatar)
    view.hosting = str(current_game_state.hosting_player.uuid) == str(player_object.uuid)
    view.is_alpha = is_player_an_alpha(current_game_state, player_object.uuid)

    raw_hand = list(current_game_state.players_and_hand.get(player_uuid, []))
    # During kitty sort, show the alpha player the kitty cards added to their hand
    if (current_game_state.game_event_state == GameEventState.WAITING_ON_ALPHA_KITTY_SORT
            and view.is_alpha):
        raw_hand.extend(current_game_state.cards_in_deck)
    # Sent in the order the engine holds it. How a hand is laid out is the
    # player's own business and lives in the client, which lets them drag cards
    # around and keep that arrangement — see frontend utils/handOrder.js. A
    # server-side sort would fight it on every push.
    view.player_hand = raw_hand
    view.my_level = current_game_state.player_levels.get(player_uuid, 0)
    view.on_alpha_team = player_uuid in alpha_team_uuids(current_game_state)
    view.my_team_points = view.alpha_team_points if view.on_alpha_team else view.defender_team_points
    view.my_turn = current_game_state.current_player.player_uuid == player_uuid

    # Worked out for everyone at the table, not only whoever is on turn: a
    # player watching a trick come round to them wants to see what they will be
    # able to answer with. It is their own hand against a lead everyone can
    # see, so there is nothing here they could not work out themselves.
    if current_game_state.game_event_state == GameEventState.ROUND_STARTED:
        view.playable_hand_cards = playable_cards(current_game_state, view.player_hand)

    _withhold_scores(view, current_game_state)
    return view


def watcher_view_state(current_game_state: GameState, watcher_uuid: str,
                       connected_uuids: Optional[Set[str]] = None,
                       now: Optional[float] = None) -> PlayerView:
    """What someone watching is shown: the table, and nothing of anyone's own.

    Held to the same house rules as the players. A watcher who could see more
    than the table — the kitty, or the totals a blind table is playing without
    — could tell a player, so they are shown exactly what a player is shown,
    less the hand."""
    watcher = current_game_state.watchers[watcher_uuid]
    view = _table_view(current_game_state, connected_uuids, time.time() if now is None else now)
    view.uuid = watcher.uuid
    view.name = watcher.name
    view.is_watcher = True
    _withhold_scores(view, current_game_state)
    return view
