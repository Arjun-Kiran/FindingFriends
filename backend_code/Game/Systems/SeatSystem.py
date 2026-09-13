"""HR-8: watching, seats changing hands, and a table running short.

Plain functions on a GameState, following HR-8 in HouseRules.md. The time comes
in as an argument rather than being read here, so every countdown can be tested
without waiting it out. Nothing here knows about sockets either: when a seat
changes hands, Main.py moves the sockets to match.
"""
import random
from typing import List, Set, Tuple
from uuid import uuid4

from Game.Components.GameState import GameState, SeatRequest, Vacancy, Watcher
from Game.Components.Player import Player
from Game.Modules.CardConstants import NONJOKERNUMBERS, Rank
from Game.Modules.EventEnum import Event, GameEventState
from Game.Systems.EventSystem import record_event
from Game.Systems.GameStateSystem import (add_player, clear_active_pile, issue_token,
                                          remove_player, repoint_tokens, revoke_tokens)
from Game.Systems.PointSystem import team_round_points


# A player who loses connection has this long to come back before their seat
# is open — the countdown shown beside their name.
GRACE_SECONDS = 60
# Away this long and the seat is no longer theirs to come back to.
DROP_AFTER_SECONDS = 5 * 60
# A table left short of players is warned at once, warned again at the first of
# these, and closed at the second.
SECOND_WARNING_SECONDS = 5 * 60
CLOSE_AFTER_SECONDS = 10 * 60
MIN_PLAYERS = 5
MAX_PLAYERS = 12

# The phases a round is being played in. The cards are dealt, so a missing
# player holds everyone up.
ROUND_PHASES = (
    GameEventState.WAITING_ON_ALPHA_CHOOSE_TRUMP,
    GameEventState.WAITING_ON_ALPHA_FRIEND_CARD_CHOICE,
    GameEventState.WAITING_ON_ALPHA_KITTY_SORT,
    GameEventState.ROUND_STARTED,
)

LEVELS = [rank.value for rank in NONJOKERNUMBERS]


def game_started(game_state: GameState) -> bool:
    return game_state.game_event_state not in (GameEventState.NOT_AVAILABLE,
                                               GameEventState.WAITING_FOR_PLAYERS_TO_JOIN)


def _name(game_state: GameState, uuid: str) -> str:
    if uuid in game_state.player_dict:
        return str(game_state.player_dict[uuid].name)
    if uuid in game_state.watchers:
        return game_state.watchers[uuid].name
    return 'Someone'


def random_place(size: int) -> int:
    """Where a new player sits among `size` others. Its own function so a test
    can pick the place."""
    return random.randint(0, size)


# --- watchers ---

def add_watcher(game_state: GameState, name: str, now: float) -> Tuple[Watcher, str]:
    """Someone starts watching. Returns the watcher and the token to hand them."""
    watcher = Watcher(uuid=str(uuid4()), name=name, joined_at=now)
    game_state.watchers[watcher.uuid] = watcher
    token = issue_token(game_state, watcher.uuid)
    record_event(game_state, Event.WATCHER_JOINED, f'{name} is watching', watcher.uuid)
    return watcher, token


def remove_watcher(game_state: GameState, watcher_uuid: str):
    """A watcher stops watching, taking any request of theirs with them."""
    watcher = game_state.watchers.pop(watcher_uuid, None)
    if watcher is None:
        return
    revoke_tokens(game_state, watcher_uuid)
    withdraw_request(game_state, watcher_uuid)
    record_event(game_state, Event.WATCHER_LEFT, f'{watcher.name} stopped watching', watcher_uuid)


def _watcher_from_seat(game_state: GameState, seat_uuid: str, now: float) -> str:
    """Turn a seat's player into a watcher, keeping their name.

    Their token follows them, so the next time their browser asks it finds
    itself watching. Returns the new watcher's uuid."""
    watcher = Watcher(uuid=str(uuid4()), name=_name(game_state, seat_uuid), joined_at=now)
    game_state.watchers[watcher.uuid] = watcher
    repoint_tokens(game_state, seat_uuid, watcher.uuid)
    return watcher.uuid


# --- seats whose player is missing ---

def is_open(vacancy: Vacancy, now: float) -> bool:
    """Can the seat be handed on, or the round ended over it?"""
    return vacancy.left or now - vacancy.since >= GRACE_SECONDS


def open_seats(game_state: GameState, now: float) -> List[str]:
    return [seat_uuid for seat_uuid, vacancy in game_state.vacancies.items()
            if seat_uuid in game_state.player_dict and is_open(vacancy, now)]


def round_held_up(game_state: GameState, now: float) -> bool:
    """A round is being played and an open seat is holding it up."""
    return game_state.game_event_state in ROUND_PHASES and bool(open_seats(game_state, now))


def seat_vacated(game_state: GameState, seat_uuid: str, now: float, left: bool = False):
    """A seated player dropped, or — with `left` — pressed Leave.

    Only once the game has started: in the lobby a player who goes is simply
    removed, and there is no seat to hold."""
    if seat_uuid not in game_state.player_dict or not game_started(game_state):
        return
    vacancy = game_state.vacancies.get(seat_uuid)
    if vacancy is None:
        vacancy = game_state.vacancies[seat_uuid] = Vacancy(since=now)
    if left and not vacancy.left:
        vacancy.left = True
        # Said by the leaving itself, so the seat opening is not said twice.
        vacancy.announced = True
        revoke_tokens(game_state, seat_uuid)


def seat_reclaimed(game_state: GameState, seat_uuid: str) -> bool:
    """The seat's player is back before anyone took it over.

    The seat is theirs again, and anyone who volunteered for it goes back to
    watching. False when the seat was not waiting on them."""
    vacancy = game_state.vacancies.get(seat_uuid)
    if vacancy is None or vacancy.left:
        return False
    del game_state.vacancies[seat_uuid]
    game_state.seat_requests = [request for request in game_state.seat_requests
                                if request.seat_uuid != seat_uuid]
    return True


# --- asking to play ---

def withdraw_request(game_state: GameState, watcher_uuid: str) -> bool:
    """Take back a watcher's request, if they had one."""
    before = len(game_state.seat_requests)
    game_state.seat_requests = [request for request in game_state.seat_requests
                                if request.watcher_uuid != watcher_uuid]
    return len(game_state.seat_requests) != before


def volunteer(game_state: GameState, watcher_uuid: str, seat_uuid: str) -> str:
    """A watcher offers to take over a seat whose player dropped or left.

    Allowed from the moment the player goes — the host can approve while the
    player still has time to come back, and the approval stands. Returns a
    problem for the watcher, or '' when the offer is made."""
    if watcher_uuid not in game_state.watchers:
        return 'Only a watcher can volunteer for a seat.'
    if game_state.game_event_state == GameEventState.GAME_ENDED:
        return 'The game is over.'
    if seat_uuid not in game_state.vacancies or seat_uuid not in game_state.player_dict:
        return 'That seat is not free.'
    withdraw_request(game_state, watcher_uuid)
    game_state.seat_requests.append(SeatRequest(watcher_uuid=watcher_uuid, seat_uuid=seat_uuid))
    record_event(game_state, Event.SEAT_REQUESTED,
                 f"{_name(game_state, watcher_uuid)} offered to take {_name(game_state, seat_uuid)}'s seat",
                 watcher_uuid)
    return ''


def ask_to_join(game_state: GameState, watcher_uuid: str) -> str:
    """A watcher asks to join as an extra player from the next round."""
    if watcher_uuid not in game_state.watchers:
        return 'Only a watcher can ask to join.'
    if not game_started(game_state):
        return 'The game has not started yet. Join it from the home screen instead.'
    if game_state.game_event_state == GameEventState.GAME_ENDED:
        return 'The game is over.'
    withdraw_request(game_state, watcher_uuid)
    game_state.seat_requests.append(SeatRequest(watcher_uuid=watcher_uuid))
    record_event(game_state, Event.SEAT_REQUESTED,
                 f'{_name(game_state, watcher_uuid)} asked to play from the next round', watcher_uuid)
    return ''


def decline_request(game_state: GameState, watcher_uuid: str) -> str:
    if not withdraw_request(game_state, watcher_uuid):
        return 'That request is no longer open.'
    return ''


def approve_request(game_state: GameState, watcher_uuid: str, now: float,
                    level=None) -> Tuple[str, str, str]:
    """The host approves a watcher's request. The approval is final.

    Returns (problem, seat_uuid, former_uuid). A volunteer for an open seat
    takes it on the spot: `seat_uuid` names the seat, so the caller can move
    the sockets, and `former_uuid` is the watcher its previous player became,
    or '' if they had already gone. A request to join is instead marked to be
    seated when the next round starts, on `level`."""
    request = next((request for request in game_state.seat_requests
                    if request.watcher_uuid == watcher_uuid), None)
    if request is None or watcher_uuid not in game_state.watchers:
        return 'That request is no longer open.', '', ''

    if request.seat_uuid:
        seat_uuid = request.seat_uuid
        if seat_uuid not in game_state.vacancies or seat_uuid not in game_state.player_dict:
            return 'That seat is no longer free.', '', ''
        return '', seat_uuid, hand_seat_over(game_state, seat_uuid, watcher_uuid, now)

    if level is None:
        level = Rank.TWO.value
    # bool is an int in Python, and True would otherwise pass as Two.
    if isinstance(level, bool) or level not in LEVELS:
        return 'A starting level has to be a rank from Two to Ace', '', ''
    if not request.approved:
        joining = sum(1 for other in game_state.seat_requests if other.approved and not other.seat_uuid)
        if len(game_state.player_order) + joining >= MAX_PLAYERS:
            return f'The table is full: it cannot grow past {MAX_PLAYERS} players.', '', ''
    request.approved = True
    request.level = level
    record_event(game_state, Event.JOIN_APPROVED,
                 f'{_name(game_state, watcher_uuid)} will join when the next round starts', watcher_uuid)
    return '', '', ''


def _rename_seat(game_state: GameState, seat_uuid: str, name: str, now: float):
    """Put a new person on a seat.

    Written through every copy of the Player: player_order, player_dict and
    hosting_player are separate objects once a game has been saved and loaded."""
    copies = [player for player in game_state.player_order if str(player.uuid) == seat_uuid]
    copies.append(game_state.player_dict[seat_uuid])
    if game_state.hosting_player and str(game_state.hosting_player.uuid) == seat_uuid:
        copies.append(game_state.hosting_player)
    for player in copies:
        player.name = name
        player.joined_at = now


def hand_seat_over(game_state: GameState, seat_uuid: str, watcher_uuid: str, now: float) -> str:
    """Seat a watcher in a free seat, taking over everything it holds.

    The hand, level, points, place, avatar and any role in the round all stay
    with the seat — only the person changes, so nothing about the round in
    progress has to. Returns the watcher uuid the seat's previous player now
    has, or '' when they had already left for good."""
    vacancy = game_state.vacancies.pop(seat_uuid)
    newcomer = game_state.watchers.pop(watcher_uuid)
    previous = _name(game_state, seat_uuid)

    former_uuid = ''
    if not vacancy.left:
        # They may yet reconnect, and when they do they find themselves watching.
        former_uuid = _watcher_from_seat(game_state, seat_uuid, now)
    else:
        revoke_tokens(game_state, seat_uuid)
    repoint_tokens(game_state, watcher_uuid, seat_uuid)
    _rename_seat(game_state, seat_uuid, newcomer.name, now)

    # One approval per seat: the other volunteers go back to watching.
    game_state.seat_requests = [request for request in game_state.seat_requests
                                if request.seat_uuid != seat_uuid and request.watcher_uuid != watcher_uuid]
    record_event(game_state, Event.SEAT_TAKEN, f"{newcomer.name} took over {previous}'s seat",
                 seat_uuid, clause=f"took over {previous}'s seat")
    return former_uuid


# --- the host ---

def pass_host(game_state: GameState, connected: Set[str]) -> str:
    """Hand the host role to whoever took their seat earliest, among the
    players still at the table. Returns the new host, or '' if nobody is here
    to take it — in which case the host stays who they were."""
    host_uuid = str(game_state.hosting_player.uuid) if game_state.hosting_player else ''
    candidates = [player for player in game_state.player_order
                  if str(player.uuid) != host_uuid
                  and str(player.uuid) in connected
                  and str(player.uuid) not in game_state.vacancies]
    if not candidates:
        return ''
    # min keeps the first of a tie, so games saved before joined_at fall back
    # to seat order.
    new_host = min(candidates, key=lambda player: player.joined_at)
    new_host_uuid = str(new_host.uuid)
    game_state.hosting_player = game_state.player_dict[new_host_uuid]
    record_event(game_state, Event.HOST_CHANGED, f'{new_host.name} is now the host', new_host_uuid)
    return new_host_uuid


# --- ending a round an empty seat is holding up ---

def end_round_as_draw(game_state: GameState):
    """Nobody moves up and the kitty is not counted. The next round starts as
    usual, with the next alpha in turn."""
    _, defender_points = team_round_points(game_state)
    game_state.card_in_discard_pile.extend(game_state.cards_in_active_pile)
    clear_active_pile(game_state)
    game_state.leading_hand_of_subround = []
    game_state.current_hand_played = []
    game_state.round_winner_side = 'none'
    game_state.round_defender_points = defender_points
    game_state.round_promotion_levels = 0
    game_state.round_promoted_players = []
    game_state.game_event_state = GameEventState.ROUND_ENDED
    record_event(game_state, Event.ROUND_DRAWN, 'The host ended the round as a draw. Nobody moves up.')


# --- between rounds ---

def _next_alpha(game_state: GameState, leaving: Set[str]) -> str:
    order = [str(player.uuid) for player in game_state.player_order]
    current = game_state.current_alpha_player.player_uuid
    start = order.index(current) if current in order else 0
    for step in range(1, len(order) + 1):
        candidate = order[(start + step) % len(order)]
        if candidate not in leaving:
            return candidate
    return ''


def _unseat(game_state: GameState, seat_uuid: str, now: float):
    vacancy = game_state.vacancies.get(seat_uuid)
    if vacancy is not None and not vacancy.left:
        # Gone past their minute but not their five: they can still come back,
        # and when they do they are watching.
        _watcher_from_seat(game_state, seat_uuid, now)
    remove_player(game_state, seat_uuid)


def _seat_joiner(game_state: GameState, request: SeatRequest, now: float):
    watcher = game_state.watchers.pop(request.watcher_uuid)
    # The seat takes the watcher's uuid, so the token they already hold now
    # acts for a seat without anything being re-pointed.
    player = Player(uuid=watcher.uuid, name=watcher.name, joined_at=now)
    add_player(game_state, player)
    game_state.player_levels[watcher.uuid] = request.level
    # A random place at the table, not the end of it.
    game_state.player_order.remove(player)
    game_state.player_order.insert(random_place(len(game_state.player_order)), player)
    withdraw_request(game_state, watcher.uuid)


def prepare_next_round(game_state: GameState, now: float) -> Tuple[str, str]:
    """Settle who sits at the table for the round about to be dealt.

    Open seats nobody took leave, and approved joiners sit down. The next alpha
    is worked out before either, so neither changes whose turn it is to be
    alpha. Returns (next_alpha_uuid, problem); nothing changes when there is a
    problem."""
    leaving = set(open_seats(game_state, now))
    joining = [request for request in game_state.seat_requests
               if request.approved and not request.seat_uuid and request.watcher_uuid in game_state.watchers]
    staying = len(game_state.player_order) - len(leaving)
    joining = joining[:max(0, MAX_PLAYERS - staying)]
    if staying + len(joining) < MIN_PLAYERS:
        return '', (f'Only {staying + len(joining)} players would be at the table. '
                    f'At least {MIN_PLAYERS} are needed to deal the next round.')

    next_alpha = _next_alpha(game_state, leaving)
    for seat_uuid in leaving:
        _unseat(game_state, seat_uuid, now)
    for request in joining:
        _seat_joiner(game_state, request, now)
    game_state.can_start_game = False
    return next_alpha or str(game_state.player_order[0].uuid), ''


# --- the countdowns ---

def sweep(game_state: GameState, now: float, connected: Set[str]) -> Tuple[bool, bool]:
    """Move every HR-8 countdown on to `now`.

    `connected` is every uuid holding a live socket for this game. Returns
    (changed, close): whether the table has something new to be told, and
    whether the room has run out of time and should close."""
    if not game_started(game_state) or game_state.game_event_state == GameEventState.GAME_ENDED:
        return False, False
    changed = False

    for seat_uuid in game_state.player_dict:
        # No socket and no countdown: a drop the server never heard about. Most
        # often a restart, which forgets every socket at once.
        if seat_uuid not in connected and seat_uuid not in game_state.vacancies:
            game_state.vacancies[seat_uuid] = Vacancy(since=now)
            changed = True

    for seat_uuid, vacancy in list(game_state.vacancies.items()):
        if seat_uuid not in game_state.player_dict:
            del game_state.vacancies[seat_uuid]
            changed = True
            continue
        name = _name(game_state, seat_uuid)
        if not vacancy.left and now - vacancy.since >= DROP_AFTER_SECONDS:
            _watcher_from_seat(game_state, seat_uuid, now)
            vacancy.left = True
            record_event(game_state, Event.SEAT_LOST,
                         f'{name} was away for 5 minutes and has lost their seat', seat_uuid)
            changed = True
        if not vacancy.announced and is_open(vacancy, now):
            vacancy.announced = True
            record_event(game_state, Event.SEAT_OPEN, f"{name}'s seat is open", seat_uuid)
            changed = True

    host_uuid = str(game_state.hosting_player.uuid) if game_state.hosting_player else ''
    host_vacancy = game_state.vacancies.get(host_uuid)
    if host_vacancy is not None and is_open(host_vacancy, now) and pass_host(game_state, connected):
        changed = True

    present = sum(1 for seat_uuid in game_state.player_dict
                  if seat_uuid in connected and seat_uuid not in game_state.vacancies)
    if present >= MIN_PLAYERS:
        if game_state.short_handed_since:
            game_state.short_handed_since = 0
            game_state.short_handed_warnings = 0
            changed = True
        return changed, False

    players = f'{present} player{"" if present == 1 else "s"}'
    if not game_state.short_handed_since:
        game_state.short_handed_since = now
        game_state.short_handed_warnings = 1
        record_event(game_state, Event.TABLE_SHORT,
                     f'Only {players} connected. The room closes in 10 minutes '
                     f'unless {MIN_PLAYERS} players are back.')
        return True, False
    if now - game_state.short_handed_since >= CLOSE_AFTER_SECONDS:
        return changed, True
    if game_state.short_handed_warnings < 2 and now - game_state.short_handed_since >= SECOND_WARNING_SECONDS:
        game_state.short_handed_warnings = 2
        record_event(game_state, Event.TABLE_SHORT,
                     f'Still only {players} connected. The room closes in 5 minutes '
                     f'unless {MIN_PLAYERS} players are back.')
        changed = True
    return changed, False
