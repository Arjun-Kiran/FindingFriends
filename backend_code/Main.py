import functools
import os
import random
import threading
import time
from uuid import uuid4
from typing import Dict, Set, Tuple

import hashlib
from flask import Flask, jsonify, Response
from flask import request, redirect, send_from_directory
from werkzeug.exceptions import NotFound
from flask_socketio import SocketIO, emit, join_room, leave_room


from Game.Components.GameState import GameState
from Game.Session.Words import generate_word_session
from Game.Views.GameStateView import game_state_str
from Game.Views.PlayerView import player_view_state, watcher_view_state, PlayerView
from Game.Components.Player import Player
from Game.Modules.EventEnum import Event, GameEventState
from Game.Systems.EventSystem import record_event
from Game.Views.CardView import card_emoji_str, card_list_to_emoji_str_list, SUIT_EMOJI, RANK_EMOJI
from Game.Systems.GameStateSystem import add_player, add_deck_to_game, deal_to_players, generate_player, set_player_as_alpha, set_player_as_leading_player, set_game_state_trump, find_player, set_winning_player_of_round, next_person_turn, reset_round, is_round_over, remove_player, set_player_avatar, play_cards_into_active_pile, clear_active_pile, cards_played_by, issue_token, seat_for_token, watcher_for_token
from Game.Systems.SeatSystem import add_watcher, remove_watcher, seat_vacated, seat_reclaimed, volunteer, ask_to_join, approve_request, decline_request, withdraw_request, pass_host, end_round_as_draw, round_held_up, prepare_next_round, sweep
from Game.Systems.DeckSystem import number_of_decks, number_of_card_to_deal
from Game.Systems.TeamSystem import number_of_cards_to_call_friends, check_friend_card_played, friend_reveal_announcement
from Game.Systems.DecisionSystem import explain_illegal_play, single_card_lead_decision, identical_set_lead_decision, sequence_identical_set_lead_decision, leading_group_of_top_decision, determine_leading_play, name_leading_play, is_trump
from Game.Systems.PointSystem import calculate_rounds_points, point_card_pile, promotion_for_round, max_alpha_team_size, advance_level, rank_from_value, alpha_team_uuids, defender_team_uuids, team_round_points
from pydantic import ValidationError
from Game.Components.GameState import AlphaDeclarationOrder, DeclareCallingCard, DeclareTrump, GameSettings
from Game.Modules.CardConstants import Suit, Rank, NONJOKERNUMBERS
from Game.Components.Card import Card
from Database.database import build_game_state_table, upsert_game_state_in_db, get_game_state_in_db
from logging_config import configure_logging, get_logger

configure_logging()
log = get_logger(__name__)

app = Flask(__name__)
# async_mode='threading' rather than eventlet: eventlet is deprecated upstream
# ("maintained in bugfix mode... we strongly recommend against using it"), and
# it required eventlet.monkey_patch() before any stdlib import — a global patch
# that had to run first in every entry point, tests included. Threading mode
# needs no patching and serves websockets through simple-websocket. One worker
# with threads is ample for a table of 5-12; note broadcast_player_views reads
# the in-process SID_TO_PLAYER, so the worker count must stay at 1 either way.
#
# Heartbeat: the defaults (25s interval, 20s timeout) mean a connection that
# dies without a clean close — a dropped network, a slept laptop, a killed
# process — goes unnoticed for up to 45 seconds, and nobody at the table is
# told anything during that window. A closed browser tab is detected instantly
# either way; this is only about the ungraceful cases, which are the common
# ones in real play.
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading',
                    ping_interval=10, ping_timeout=10)


build_game_state_table()

MOCK_REDIS_CACHE: Dict[str, GameState] = dict()
SITE_URL = "http://127.0.0.1:5050"

# Maps socket session ID -> (game_code, player_uuid). Only a join that showed a
# seat's token sets it, and it is how every socket action learns who is acting
# (validate_player) — never from a uuid in the payload.
SID_TO_PLAYER: Dict[str, Tuple[str, str]] = dict()

# The header a browser sends its seat token in over HTTP. See game_session.
PLAYER_TOKEN_HEADER = 'X-Player-Token'

# One lock per game. Every handler loads the game from the database, changes it
# and saves it back, and handlers run on threads — so two handlers for the same
# game could load the same state, and whichever saved second would silently
# throw the first one's change away. Re-entrant because a handler holding it
# calls helpers that may take it again.
_GAME_LOCKS: Dict[str, threading.RLock] = dict()
_GAME_LOCKS_GUARD = threading.Lock()


def game_lock(game_code) -> threading.RLock:
    """The lock every change to this game is made under."""
    key = str(game_code or '').lower()
    with _GAME_LOCKS_GUARD:
        if key not in _GAME_LOCKS:
            _GAME_LOCKS[key] = threading.RLock()
        return _GAME_LOCKS[key]


def one_change_at_a_time(handler):
    """Run a socket handler holding the lock of the game its payload names."""
    @functools.wraps(handler)
    def locked(*args):
        data = args[0] if args else None
        game_code = data.get('game_code', '') if isinstance(data, dict) else ''
        with game_lock(game_code):
            return handler(*args)
    return locked


def now() -> float:
    """The time HR-8's countdowns run on. A function so tests can move it."""
    return time.time()


# HR-8's countdowns — a dropped player's minute, the host handing over, a table
# left short — move on whether or not anyone does anything, so one background
# task sweeps every game that has had a socket in it, once a second.
SWEEP_INTERVAL_SECONDS = 1
WATCHED_GAMES: Set[str] = set()
_sweeper_started = False
_SWEEPER_GUARD = threading.Lock()


def watch_for_timeouts(game_code: str):
    """Include this game in the sweep, starting the sweeper if it is not running.

    Not under test: tests call sweep_game themselves, with a clock they move."""
    global _sweeper_started
    WATCHED_GAMES.add(game_code.lower())
    if app.config.get('TESTING'):
        return
    with _SWEEPER_GUARD:
        if _sweeper_started:
            return
        _sweeper_started = True
    socketio.start_background_task(_sweep_forever)


def _sweep_forever():
    while True:
        socketio.sleep(SWEEP_INTERVAL_SECONDS)
        sweep_all()


def sweep_all():
    for game_code in list(WATCHED_GAMES):
        try:
            sweep_game(game_code)
        except Exception as e:
            log.exception("Sweep failed for %s: %s", game_code, e)


def sweep_game(game_code: str):
    """Move one game's countdowns on to now, and tell the table if anything changed."""
    with game_lock(game_code):
        try:
            gs = get_redis_cache(game_code)
        except GameNotFoundError:
            WATCHED_GAMES.discard(game_code)
            return
        changed, close = sweep(gs, now(), connected_player_uuids(game_code))
        if close:
            close_room(gs)
        elif changed:
            update_redis_cache(gs)


class GameNotFoundError(Exception):
    """Raised when a game code has no active session stored."""

    def __init__(self, game_code: str):
        self.game_code = game_code
        super().__init__(f'Game not found: {game_code}')


@app.errorhandler(GameNotFoundError)
def handle_game_not_found(error: GameNotFoundError):
    return jsonify({'error': 'game_not_found', 'message': str(error)}), 404


def parse_suit(value) -> Suit:
    """Parse a suit from a name string ('SPADE') or integer value (0x20)."""
    if isinstance(value, str):
        return Suit[value]
    return Suit(value)


def parse_rank(value) -> Rank:
    """Parse a rank from a name string ('TWO') or integer value (1)."""
    if isinstance(value, str):
        return Rank[value]
    return Rank(value)


def player_name(game_state: GameState, player_uuid: str) -> str:
    """Display name for a player, falling back to something printable."""
    player = game_state.player_dict.get(player_uuid)
    return str(player.name) if player else 'A player'


# Each phase the alpha has to act in, and how the wait is described. Kept as a
# table so entering a phase and announcing it cannot drift apart — the trump
# phase in particular is entered from two different handlers.
WAITING_ON_ALPHA = {
    GameEventState.WAITING_ON_ALPHA_CHOOSE_TRUMP: (
        Event.WAITING_ON_ALPHA_CHOOSE_TRUMP, 'is choosing the trump suit...'),
    GameEventState.WAITING_ON_ALPHA_FRIEND_CARD_CHOICE: (
        Event.WAITING_ON_ALPHA_FRIEND_CARD_CHOICE, 'is calling friend cards...'),
    GameEventState.WAITING_ON_ALPHA_KITTY_SORT: (
        Event.WAITING_ON_ALPHA_KITTY_SORT, 'is picking cards for the kitty...'),
}


def enter_alpha_phase(game_state: GameState, phase: GameEventState):
    """Move into a phase the alpha has to act in, announcing who is holding
    everyone up. Always use this rather than assigning game_event_state."""
    game_state.game_event_state = phase
    event_type, doing = WAITING_ON_ALPHA[phase]
    alpha_uuid = game_state.current_alpha_player.player_uuid
    record_event(game_state, event_type,
                 f'{player_name(game_state, alpha_uuid)} {doing}', alpha_uuid)


_TRUMP = GameEventState.WAITING_ON_ALPHA_CHOOSE_TRUMP
_FRIENDS = GameEventState.WAITING_ON_ALPHA_FRIEND_CARD_CHOICE
_KITTY = GameEventState.WAITING_ON_ALPHA_KITTY_SORT

# HR-7: the house rule picks one of these (GameSettings.alpha_declaration_order).
ALPHA_PHASE_ORDERS = {
    AlphaDeclarationOrder.TRUMP_FRIENDS_KITTY: (_TRUMP, _FRIENDS, _KITTY),
    AlphaDeclarationOrder.TRUMP_KITTY_FRIENDS: (_TRUMP, _KITTY, _FRIENDS),
    AlphaDeclarationOrder.KITTY_TRUMP_FRIENDS: (_KITTY, _TRUMP, _FRIENDS),
}


def alpha_step_done(game_state: GameState, phase: GameEventState) -> bool:
    """Whether the alpha has already done this step this round."""
    if phase == _TRUMP:
        return game_state.declare_trump.suit is not None
    if phase == _FRIENDS:
        return bool(game_state.friend_calling_cards)
    return not game_state.cards_in_deck


def advance_alpha_phase(game_state: GameState):
    """Move the alpha on to their next opening step, or, once all three are
    done, start the round with the alpha leading the first trick.

    Called at the deal and after each step. The next step is the first one in
    the table's order not yet done, read off the round itself rather than off
    the phase just left — so a game saved under a different order still
    finishes every step rather than skipping one."""
    order = ALPHA_PHASE_ORDERS[game_state.settings.alpha_declaration_order]
    remaining = [phase for phase in order if not alpha_step_done(game_state, phase)]
    if remaining:
        enter_alpha_phase(game_state, remaining[0])
        return
    set_player_as_leading_player(game_state, game_state.current_alpha_player.player_uuid)
    game_state.game_event_state = GameEventState.ROUND_STARTED


def calling_card_str(calling_card) -> str:
    """A called card as the table reads it: '2nd A♠️'."""
    order = calling_card.order
    # Orders only ever run 1-4, so no need to special-case 11th/12th/13th.
    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(order, 'th')
    return f'{order}{suffix} {RANK_EMOJI[calling_card.rank]}{SUIT_EMOJI[calling_card.suit]}'


def emit_session_invalid(reason: str, message: str):
    """Tell one client its saved session is gone so it can return to the home screen.

    Sent instead of a plain 'error' whenever the game or the player behind a
    request no longer exists — a generic error banner leaves the browser stuck
    on a game that the server has forgotten (e.g. after a server restart)."""
    emit('session_invalid', {'reason': reason, 'message': message})


def validate_member(game_code: str) -> tuple:
    """Load a game and work out who is acting in it: a player or a watcher.

    Returns (game_state, uuid, error) where error is None or a dict with a
    'code' and a 'message'. Codes 'game_not_found' and 'player_not_found' mean
    the client's session is dead rather than its request being wrong.

    Who is acting is whoever this socket joined as, never a uuid in the
    payload: every player's uuid is on every screen, so a uuid proves nothing.
    The token shown at join does, and handle_join is the only place that binds
    a socket to anyone."""
    if not game_code:
        return None, None, {'code': 'missing_game_code', 'message': 'missing game_code'}
    try:
        gs = get_redis_cache(game_code)
    except GameNotFoundError as e:
        return None, None, {'code': 'game_not_found', 'message': str(e)}
    except Exception as e:
        log.exception("Failed to load game %s: %s", game_code, e)
        return None, None, {'code': 'load_failed', 'message': 'Could not load that game'}
    bound = SID_TO_PLAYER.get(request.sid)
    if bound is None or bound[0] != game_code.lower():
        # Not treated as a dead session. After a reconnect the client sends its
        # join first, but the server can pick up an action queued behind it
        # before the join lands — sending the player home for that would be far
        # worse than asking them to try again.
        return None, None, {'code': 'not_joined', 'message': 'Still connecting to the game — try that again.'}
    if bound[1] not in gs.player_dict and bound[1] not in gs.watchers:
        return None, None, {'code': 'player_not_found', 'message': 'You are no longer part of this game'}
    return gs, bound[1], None


def validate_player(game_code: str) -> tuple:
    """validate_member, for what only someone with a seat may do.

    A watcher is refused without being sent home: they are welcome to go on
    watching, they just cannot play."""
    gs, member_uuid, err = validate_member(game_code)
    if err:
        return None, None, err
    if member_uuid in gs.watchers:
        return None, None, {'code': 'watching',
                            'message': 'You are watching this game. Ask the host for a seat to play.'}
    return gs, member_uuid, None


SESSION_INVALID_CODES = ('game_not_found', 'player_not_found')


def emit_validation_error(error: dict):
    """Emit a validation failure, routing dead sessions to 'session_invalid'."""
    if error['code'] in SESSION_INVALID_CODES:
        emit_session_invalid(error['code'], error['message'])
        return
    emit('error', {'message': error['message']})


# Where `npm run build` puts the SPA. In production one origin serves the page,
# the API and the socket, so gunicorn hands out these files itself rather than
# putting a second server in front of them. Absolute, because gunicorn's working
# directory is not guaranteed to be backend_code/.
FRONTEND_DIST = os.path.abspath(os.environ.get(
    'FRONTEND_DIST',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend_code', 'dist'),
))


def frontend_build_present() -> bool:
    """True when there is a build to serve.

    Checked per request rather than once at import: in development there is no
    build, and a developer who runs `npm run build` should not have to restart
    the server for it to be picked up.
    """
    return os.path.isfile(os.path.join(FRONTEND_DIST, 'index.html'))


def send_index():
    """The SPA shell, which must never be cached.

    The asset filenames are content-hashed and can be cached forever, but
    index.html is what points at them. Cache it and a returning player keeps
    loading a build whose hashed assets no longer exist.
    """
    response = send_from_directory(FRONTEND_DIST, 'index.html')
    response.headers['Cache-Control'] = 'no-cache'
    return response


@app.route("/")
def hello_world():
    if frontend_build_present():
        return send_index()
    # No build: this is a dev backend, and vite is serving the page on :3000.
    return '''Hello, backend is alive.'''


@app.route("/<path:asset_path>")
def frontend_asset(asset_path: str):
    """Serve a built asset, falling back to the SPA shell.

    Only reached when no API route matched. Werkzeug ranks a static rule such
    as /create above this catch-all regardless of definition order, so the API
    cannot be shadowed by a file of the same name — there is a test for that.

    send_from_directory resolves through safe_join, so a traversal attempt
    (../../etc/passwd) raises NotFound rather than escaping FRONTEND_DIST.
    """
    if not frontend_build_present():
        raise NotFound()
    try:
        response = send_from_directory(FRONTEND_DIST, asset_path)
    except NotFound:
        # A client-side route, not a missing file. Hand back the shell and let
        # the app render it.
        return send_index()
    if asset_path.startswith('assets/'):
        # Content-hashed by vite, so a given URL's bytes never change.
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response


@app.route("/create")
def create_game():
    gs = GameState()
    gs.session = str(uuid4())
    gs.game_code = generate_word_session(3).lower()
    gs.game_event_state = GameEventState.WAITING_FOR_PLAYERS_TO_JOIN
    update_redis_cache(game_state=gs)
    join_link = f'/join/{gs.game_code}'
    return jsonify({
        'game_code': gs.game_code.lower(),
        'join_link': join_link
    })


@app.route("/join")
def join_game():
    if len(request.args) == 0:
        return f'''
        <form action="/join">
            <label for="gamecode">Game Code:</label>
            <input type="text" id="gamecode" name="gamecode"><br><br>
            <input type="submit" value="Submit">
        </form>
        '''
    game_code: str = request.args.get('gamecode','')
    return redirect(f'/join/{game_code.lower()}', code=302)


@app.route("/join/<game_code>")
def join_game_with_session_id(game_code):
    # Under the game's lock: two players joining at once would otherwise both
    # load the lobby before either saved, and one of them would vanish.
    with game_lock(game_code):
        return _join_game(game_code.lower())


def _join_game(game_code: str):
    gs = get_redis_cache(game_code)

    if gs.game_event_state != GameEventState.WAITING_FOR_PLAYERS_TO_JOIN:
        return jsonify({
            'error': 'game_in_progress',
            'message': 'Game is not accepting new players'
        }), 409

    nick_name = request.args.get('nick_name')
    if not nick_name:
        return jsonify({
            'error': 'missing_nick_name',
            'message': 'A nickname is required to join'
        }), 400

    new_player = generate_player(name=nick_name)
    new_gs = add_player(gs, new_player)
    # The only time this token is ever sent. Everything the player does from
    # here on is taken on its say-so, so it goes to them and nobody else.
    player_token = issue_token(new_gs, str(new_player.uuid))
    update_redis_cache(new_gs)
    return jsonify({
        'game_link': f'/game/{game_code}/player',
        'new_player_uuid': new_player.uuid,
        'player_token': player_token,
        'nick_name': nick_name
    })


@app.route("/watch/<game_code>")
def watch_game(game_code):
    """Watch a game, in the lobby or mid-game (HR-8).

    Returns a token as /join does. It acts for a watcher rather than a seat —
    until the host hands that watcher a seat, when the same token starts acting
    for it."""
    with game_lock(game_code):
        gs = get_redis_cache(game_code)
        nick_name = request.args.get('nick_name')
        if not nick_name:
            return jsonify({
                'error': 'missing_nick_name',
                'message': 'A nickname is required to watch'
            }), 400
        if gs.game_event_state == GameEventState.GAME_ENDED:
            return jsonify({
                'error': 'game_over',
                'message': 'That game is over'
            }), 409
        watcher, player_token = add_watcher(gs, nick_name, now())
        update_redis_cache(gs)
        watch_for_timeouts(gs.game_code)
        return jsonify({
            'watcher_uuid': watcher.uuid,
            'player_token': player_token,
            'nick_name': nick_name
        })


@app.route("/game/<game_code>/player")
def game_session(game_code: str):
    """The caller's own view of the game: a player's with their hand, or a
    watcher's with none.

    The token rides in a header rather than the URL: a URL ends up in server
    logs and browser history, and this one would open a player's hand to anyone
    who read either."""
    game_state = get_redis_cache(game_code)
    token = request.headers.get(PLAYER_TOKEN_HEADER, '')
    connected = connected_player_uuids(game_code)
    player_uuid = seat_for_token(game_state, token)
    if player_uuid:
        return jsonify(player_view_state(game_state, player_uuid, connected, now()).to_json_dict())
    watcher_uuid = watcher_for_token(game_state, token)
    if watcher_uuid:
        return jsonify(watcher_view_state(game_state, watcher_uuid, connected, now()).to_json_dict())
    return jsonify({
        'error': 'player_not_found',
        'message': 'You are no longer part of this game'
    }), 404


@socketio.on('message')
def handle_message(message):
    log.debug("Received message from client")


@socketio.on('connect')
def handle_connect():
    log.info("Client connected")


@socketio.on('disconnect')
def handle_disconnect():
    from flask import request as flask_request
    sid = flask_request.sid
    if sid in SID_TO_PLAYER:
        game_code, player_uuid = SID_TO_PLAYER.pop(sid)
        with game_lock(game_code):
            player_disconnected(game_code, player_uuid)
    log.info("Client disconnected: %s", sid)


def player_disconnected(game_code: str, player_uuid: str):
    """Deal with a socket going away. Call holding the game's lock.

    `player_uuid` is whoever the socket acted for — a seat or a watcher."""
    try:
        gs = get_redis_cache(game_code)
    except GameNotFoundError:
        # Session was already invalidated; nothing left to clean up.
        return
    except Exception as e:
        log.warning("Could not load game %s on disconnect: %s", game_code, e)
        return
    if player_uuid in connected_player_uuids(game_code):
        # Another tab of theirs is still open, so they have not gone anywhere.
        return
    if player_uuid in gs.watchers:
        # A watcher who is not here cannot be handed a seat, so any offer of
        # theirs goes. They are still a watcher, and can ask again when back.
        if withdraw_request(gs, player_uuid):
            update_redis_cache(gs)
        else:
            broadcast_player_views(gs)
        return
    try:
        if gs.game_event_state == GameEventState.WAITING_FOR_PLAYERS_TO_JOIN:
            remove_player(gs, player_uuid)
            if len(gs.player_order) == 0:
                upsert_game_state_in_db(game_code, gs.model_dump(mode='json'), False)
                log.info("Last player disconnected, invalidating session %s", game_code)
                return
            update_redis_cache(gs)
        else:
            # Mid-game the seat is held: the hand is already dealt and the
            # turn order depends on them, so dropping the player would break
            # the round. Announce it instead, so the others can see who
            # they are waiting on rather than watching a game that has
            # silently stopped.
            log.info("Player %s dropped mid-game in %s, holding their seat", player_uuid, game_code)
            name = player_name(gs, player_uuid)
            # HR-8: their minute to come back starts now.
            seat_vacated(gs, player_uuid, now())
            record_event(gs, Event.PLAYER_DISCONNECTED, f'{name} lost connection', player_uuid)
            update_redis_cache(gs)
    except Exception as e:
        log.exception("Error handling player disconnect: %s", e)


@socketio.on('leave_lobby')
@one_change_at_a_time
def handle_leave_lobby(data):
    game_code = data.get('game_code', '').lower()
    gs, player_uuid, err = validate_member(game_code)
    if err:
        emit_validation_error(err)
        return

    if player_uuid in gs.watchers:
        leave_as_watcher(gs, player_uuid)
        return

    if gs.game_event_state != GameEventState.WAITING_FOR_PLAYERS_TO_JOIN:
        emit('error', {'message': 'Can only leave the lobby before the game starts'})
        return

    remove_player(gs, player_uuid)
    # The seat is gone, so this socket no longer acts for anyone.
    SID_TO_PLAYER.pop(request.sid, None)
    try:
        leave_room(game_code)
    except Exception:
        pass

    if len(gs.player_order) == 0:
        upsert_game_state_in_db(game_code, gs.model_dump(mode='json'), False)
        return

    update_redis_cache(gs)


@socketio.on('leave_game')
@one_change_at_a_time
def handle_leave_game(data):
    """A player deliberately leaves, in the lobby or mid-game — or a watcher
    stops watching.

    Distinct from a dropped connection on purpose. A disconnect gives the
    player a minute to come back; someone who left is not coming back, and the
    others deserve to be told which of the two happened.

    Mid-game the seat stays in the round — the hand is dealt and turn order
    depends on it — but it is open at once (HR-8): a watcher can take it over,
    or the host can end the round as a draw.
    """
    game_code = data.get('game_code', '').lower()

    gs, player_uuid, err = validate_member(game_code)
    if err:
        emit_validation_error(err)
        return

    if player_uuid in gs.watchers:
        leave_as_watcher(gs, player_uuid)
        return

    # Forget the player's sockets before anything else, every tab and not just
    # this one: the disconnect that follows closing the tab would otherwise
    # announce "lost connection" on top of "left the game", and a tab left open
    # must not go on acting for a seat its player has given up.
    unbind_sockets(game_code, player_uuid)

    try:
        leave_room(game_code)
    except Exception:
        pass

    if gs.game_event_state == GameEventState.WAITING_FOR_PLAYERS_TO_JOIN:
        # Nothing dealt yet, so the seat can actually go. remove_player records
        # the departure itself.
        remove_player(gs, player_uuid)
        if len(gs.player_order) == 0:
            upsert_game_state_in_db(game_code, gs.model_dump(mode='json'), False)
            log.info("Last player left lobby, invalidating session %s", game_code)
            return
    else:
        log.info("Player %s left %s mid-game, opening their seat", player_uuid, game_code)
        record_event(gs, Event.PLAYER_LEFT,
                     f'{player_name(gs, player_uuid)} left the game', player_uuid)
        was_host = bool(gs.hosting_player) and str(gs.hosting_player.uuid) == player_uuid
        seat_vacated(gs, player_uuid, now(), left=True)
        if was_host:
            # HR-8: a host who presses Leave hands over at once.
            pass_host(gs, connected_player_uuids(game_code))

    update_redis_cache(gs)


@socketio.on('join')
@one_change_at_a_time
def handle_join(data):
    """Client asks to join a game's room so it receives updates for that game.

    Expected data: { 'game_code': '<code>', 'player_token': '<token>' }

    The token is what binds this socket to a seat: from here on every action it
    sends is taken as that player's (validate_player). With no token at all the
    socket only gets the public headline.
    """
    try:
        from flask import request as flask_request
        game_code = data.get('game_code', '').lower()
        player_token = data.get('player_token', '')
        if not game_code:
            emit('error', {'message': 'missing game_code'})
            return

        # Load before joining the room: a client whose game is gone gets told to
        # reset rather than sitting in a room that will never receive updates.
        try:
            gs = get_redis_cache(game_code)
        except GameNotFoundError as e:
            emit_session_invalid('game_not_found', str(e))
            return

        player_uuid = seat_for_token(gs, player_token)
        watcher_uuid = '' if player_uuid else watcher_for_token(gs, player_token)
        member_uuid = player_uuid or watcher_uuid
        # A token that acts for nobody here, or a bare uuid from a browser that
        # saved its session before tokens existed. Either way there is nobody
        # this client can prove it is, so it goes home rather than sitting in a
        # game it cannot act in.
        if not member_uuid and (player_token or data.get('player_uuid')):
            emit_session_invalid('player_not_found', 'You are no longer part of this game')
            return

        # Was this player away before this socket arrived? Checked before the
        # sid is registered, and only counts mid-game: in the lobby every join
        # is a first join, not a return.
        returning = (
            player_uuid
            and gs.game_event_state != GameEventState.WAITING_FOR_PLAYERS_TO_JOIN
            and player_uuid not in connected_player_uuids(game_code)
        )

        join_room(game_code)

        # Track which socket belongs to whom: a seat, or a watcher.
        if member_uuid:
            SID_TO_PLAYER[flask_request.sid] = (game_code, member_uuid)
            watch_for_timeouts(game_code)

        try:
            if returning:
                log.info("Player %s reconnected to %s", player_uuid, game_code)
                # Back before anyone took the seat over, so it is theirs again
                # and any volunteers for it go back to watching (HR-8).
                seat_reclaimed(gs, player_uuid)
                record_event(gs, Event.PLAYER_RECONNECTED, f'{player_name(gs, player_uuid)} reconnected',
                             player_uuid)
                update_redis_cache(gs)
            elif member_uuid:
                # Broadcast rather than reply: this client needs the state, and
                # everyone else needs their disconnected list refreshed.
                broadcast_player_views(gs)
            else:
                emit('game_stats', {'game_event_state': gs.game_event_state.value, 'number_of_players': len(gs.player_order)})
        except Exception as e:
            log.exception("Could not build game state for %s: %s", game_code, e)
    except Exception as e:
        log.exception("Error in handle_join: %s", e)


@socketio.on('choose_avatar')
@one_change_at_a_time
def handle_choose_avatar(data):
    """Player picks the animal emoji that stands for them at the table.

    Expected data: { 'game_code': '<code>', 'avatar': '<emoji>' }

    Lobby only. Once cards are dealt the avatar is how everyone reads the
    players bar, the scoreboards and the trick pile, so letting someone swap
    identity mid-hand would make the table unreadable.
    """
    try:
        game_code = data.get('game_code', '').lower()
        avatar = data.get('avatar', '')

        gs, player_uuid, err = validate_player(game_code)
        if err:
            emit_validation_error(err)
            return

        if gs.game_event_state != GameEventState.WAITING_FOR_PLAYERS_TO_JOIN:
            emit('error', {'message': 'Avatars can only be changed in the lobby'})
            return

        if not set_player_avatar(gs, player_uuid, avatar):
            # Either not one of ours, or someone else claimed it first — the
            # picker greys out taken avatars, but two players can still tap the
            # same one before either update lands.
            emit('error', {'message': 'That avatar is not available'})
            return

        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_choose_avatar: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('update_settings')
@one_change_at_a_time
def handle_update_settings(data):
    """Host changes the house rules.

    Expected data: { 'game_code': '<code>',
                     'settings': { '<name>': <bool or option value>, ... } }

    Lobby only, and the host only. These change how a hand is scored, who gets
    to act, or what the table is allowed to see, so letting them move once
    cards are dealt would change the rules under players who had already
    decided what to keep — and hide_scores_until_round_end would be worse than
    that, since a host who could flip it mid-round would have a peek at the
    totals nobody else gets.

    Sent as a whole settings object rather than one key at a time: the lobby
    shows them all together, and a partial update would let two clicks in
    quick succession land in either order and disagree about the rest.
    """
    try:
        game_code = data.get('game_code', '').lower()
        requested = data.get('settings', {})

        gs, player_uuid, err = validate_player(game_code)
        if err:
            emit_validation_error(err)
            return

        if gs.game_event_state != GameEventState.WAITING_FOR_PLAYERS_TO_JOIN:
            emit('error', {'message': 'The rules can only be changed in the lobby'})
            return

        if str(gs.hosting_player.uuid) != player_uuid:
            emit('error', {'message': 'Only the host can change the rules'})
            return

        if not isinstance(requested, dict):
            emit('error', {'message': 'Invalid settings'})
            return

        # Built from the known fields rather than from whatever arrived, so an
        # unknown or mistyped key is dropped instead of being stored and
        # silently ignored for the rest of the game.
        known = GameSettings.model_fields.keys()
        unknown = [key for key in requested if key not in known]
        if unknown:
            emit('error', {'message': f'Unknown setting: {unknown[0]}'})
            return

        # Switches are coerced to a bool as before; a setting that is a choice
        # (alpha_declaration_order) is left to the model to check, so a value
        # outside its options is refused rather than stored.
        merged = {}
        for name in known:
            value = requested.get(name, getattr(gs.settings, name))
            is_switch = GameSettings.model_fields[name].annotation is bool
            merged[name] = bool(value) if is_switch else value
        try:
            gs.settings = GameSettings(**merged)
        except ValidationError:
            emit('error', {'message': 'Invalid settings'})
            return

        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_update_settings: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('set_starting_level')
@one_change_at_a_time
def handle_set_starting_level(data):
    """Host sets the level a player starts the game on.

    For a table picking up a game it did not finish in one sitting: the new
    game starts everyone on Two, and this puts each player back where they
    left off. Per player, because by the time a game is abandoned the levels
    have moved apart.

    Expected data: { 'game_code': '<code>',
                     'target_uuid': '<uuid>', 'level': <int> }

    `level` is the Rank enum VALUE, as player_levels holds it — 1 is Two and
    13 is Ace. Written straight into player_levels, which is where a player's
    level lives for the rest of the game; nothing at the start of the game
    resets it.

    Lobby only, and the host only. Once the cards are dealt a level decides
    what a player may declare as trump and how far they are from winning, so
    moving it mid-game would be moving the finish line.
    """
    try:
        game_code = data.get('game_code', '').lower()
        target_uuid = data.get('target_uuid', '')
        level = data.get('level')

        gs, player_uuid, err = validate_player(game_code)
        if err:
            emit_validation_error(err)
            return

        if gs.game_event_state != GameEventState.WAITING_FOR_PLAYERS_TO_JOIN:
            emit('error', {'message': 'Starting levels can only be changed in the lobby'})
            return

        if str(gs.hosting_player.uuid) != player_uuid:
            emit('error', {'message': 'Only the host can change starting levels'})
            return

        if target_uuid not in gs.player_dict:
            emit('error', {'message': 'That player is not in this game'})
            return

        # bool is an int in Python, and True would otherwise pass as Two.
        rank = next((r for r in NONJOKERNUMBERS if r.value == level), None)
        if isinstance(level, bool) or rank is None:
            emit('error', {'message': 'A starting level has to be a rank from Two to Ace'})
            return

        if gs.player_levels.get(target_uuid) == rank.value:
            return

        gs.player_levels[target_uuid] = rank.value
        # Said out loud: a level is a head start, and the rest of the table
        # should see the host hand one out rather than find out mid-game.
        record_event(
            gs, Event.STARTING_LEVEL_SET,
            f'{player_name(gs, target_uuid)} will start on level {RANK_EMOJI[rank]}',
            target_uuid,
        )
        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_set_starting_level: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('start_game')
@one_change_at_a_time
def handle_start_game(data):
    """Host starts the game. Builds deck, deals cards, picks alpha.

    Expected data: { 'game_code': '<code>' }
    """
    try:
        game_code = data.get('game_code', '').lower()

        gs, player_uuid, err = validate_player(game_code)
        if err:
            emit_validation_error(err)
            return

        # Validate: game must be in waiting state
        if gs.game_event_state != GameEventState.WAITING_FOR_PLAYERS_TO_JOIN:
            emit('error', {'message': 'Game is not in a state to start'})
            return

        # Validate: only the host can start
        if str(gs.hosting_player.uuid) != player_uuid:
            emit('error', {'message': 'Only the host can start the game'})
            return

        # Validate: need minimum players
        if not gs.can_start_game:
            emit('error', {'message': 'Not enough players to start (need 5+)'})
            return

        # Build and deal
        num_players = len(gs.player_order)
        deck_count = number_of_decks(num_players)
        cards_per_person = number_of_card_to_deal(num_players)

        add_deck_to_game(gs, deck_count)
        deal_to_players(gs, cards_per_person)
        # Remaining cards in cards_in_deck are the kitty

        # The first alpha is drawn from the table unless the host has turned the
        # draw off, in which case the host takes it. The draw is on by default
        # (HR-9). Only the FIRST alpha: after this the seat passes by the rules,
        # so a random draw here decides who starts, not who keeps it.
        first_alpha = (str(random.choice(gs.player_order).uuid)
                       if gs.settings.random_first_alpha else player_uuid)
        set_player_as_alpha(gs, first_alpha)
        set_player_as_leading_player(gs, first_alpha)
        if first_alpha != player_uuid:
            record_event(
                gs, Event.GAME_STARTED,
                f'{player_name(gs, first_alpha)} was drawn as the first alpha',
                first_alpha,
            )

        advance_alpha_phase(gs)
        gs.can_start_game = False

        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_start_game: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('declare_trump')
@one_change_at_a_time
def handle_declare_trump(data):
    """Alpha player declares trump suit by selecting a card from their hand.

    Expected data: { 'game_code': '<code>', 'suit': '<SUIT>', 'rank': '<RANK>' }
    The rank must match the alpha player's current level.
    """
    try:
        game_code = data.get('game_code', '').lower()
        suit_str = data.get('suit', '')
        rank_str = data.get('rank', '')

        gs, player_uuid, err = validate_player(game_code)
        if err:
            emit_validation_error(err)
            return

        # Validate: must be in trump declaration phase
        if gs.game_event_state != GameEventState.WAITING_ON_ALPHA_CHOOSE_TRUMP:
            emit('error', {'message': 'Not in trump declaration phase'})
            return

        # Validate: only the alpha can declare
        if gs.current_alpha_player.player_uuid != player_uuid:
            emit('error', {'message': 'Only the alpha player can declare trump'})
            return

        # Parse suit and rank
        try:
            declared_suit = parse_suit(suit_str)
            declared_rank = parse_rank(rank_str)
        except ValueError:
            emit('error', {'message': f'Invalid suit or rank: {suit_str}, {rank_str}'})
            return

        # The standard rule: trump is your own level, in a suit you are holding.
        # A host can lift it in the lobby (GameSettings.free_trump_choice).
        if not gs.settings.free_trump_choice:
            alpha_level = gs.player_levels.get(player_uuid, Rank.TWO.value)
            level_name = rank_from_value(alpha_level).name.title()
            if declared_rank.value != alpha_level:
                emit('error', {'message': f'Trump has to be your own level. '
                                          f'You are on {level_name}s, so name a {level_name}.'})
                return

            hand = gs.players_and_hand.get(player_uuid, [])
            at_level = [card for card in hand if card.rank == declared_rank]
            # An alpha holding none of their level still has to name a trump, so
            # any suit will do — which is what the trump picker already offers
            # them. The rule only bites when there is a real choice to make.
            if at_level and not any(card.suit == declared_suit for card in at_level):
                emit('error', {'message': f'You are not holding that {level_name}. '
                                          f'Trump has to be a card in your hand.'})
                return

        # Set trump
        set_game_state_trump(gs, declared_suit, declared_rank)
        record_event(
            gs, Event.TRUMP_DECLARED,
            f'{player_name(gs, player_uuid)} declared {SUIT_EMOJI[declared_suit]} as trump',
            player_uuid,
            clause=f'declared {SUIT_EMOJI[declared_suit]} as trump',
        )
        advance_alpha_phase(gs)

        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_declare_trump: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('call_friends')
@one_change_at_a_time
def handle_call_friends(data):
    """Alpha player calls friend cards to determine secret partners.

    Expected data: {
        'game_code': '<code>',
        'calling_cards': [{'suit': '<SUIT>', 'rank': '<RANK>', 'order': <int>}, ...]
    }
    """
    try:
        game_code = data.get('game_code', '').lower()
        calling_cards_data = data.get('calling_cards', [])

        gs, player_uuid, err = validate_player(game_code)
        if err:
            emit_validation_error(err)
            return

        # Validate: must be in friend calling phase
        if gs.game_event_state != GameEventState.WAITING_ON_ALPHA_FRIEND_CARD_CHOICE:
            emit('error', {'message': 'Not in friend calling phase'})
            return

        # Validate: only the alpha can call friends
        if gs.current_alpha_player.player_uuid != player_uuid:
            emit('error', {'message': 'Only the alpha player can call friends'})
            return

        # Validate: correct number of calling cards
        num_players = len(gs.player_order)
        expected_count = number_of_cards_to_call_friends(num_players)
        if len(calling_cards_data) != expected_count:
            emit('error', {'message': f'Must call exactly {expected_count} friend cards, got {len(calling_cards_data)}'})
            return

        # Parse and validate each calling card
        calling_cards = []
        for cc in calling_cards_data:
            try:
                suit = parse_suit(cc['suit'])
                rank = parse_rank(cc['rank'])
                order = int(cc['order'])
            except (ValueError, KeyError) as e:
                emit('error', {'message': f'Invalid calling card: {cc}'})
                return

            # Called cards must not be trumps, unless the table has agreed
            # otherwise in the lobby (GameSettings.trumps_can_be_called).
            if not gs.settings.trumps_can_be_called:
                if suit == gs.declare_trump.suit or rank == gs.declare_trump.rank:
                    # Named as the card, not as the enum behind it. This read
                    # "13 of 16" until a player hit it and could not tell which
                    # of the cards they had named was the problem, or why.
                    named = card_emoji_str(Card(rank=rank, suit=suit))
                    emit('error', {'message': f'Called cards must not be trumps: {named}'})
                    return

            if order < 1:
                emit('error', {'message': 'Order must be at least 1'})
                return

            # Named twice, this would be one card doing two rules' work: the
            # first play to match it satisfies both at once, so the second
            # friend could never be found and all_friends_found would never
            # come true. Two copies of the SAME card are fine and are what the
            # order is for — the 1st and the 2nd Ace of Clubs are two cards.
            already = next((cc for cc in calling_cards
                            if (cc.suit, cc.rank, cc.order) == (suit, rank, order)), None)
            if already:
                emit('error', {'message': f'You have called the '
                                          f'{calling_card_str(already)} twice. Each friend '
                                          f'has to be found by a different card.'})
                return

            calling_cards.append(DeclareCallingCard(suit=suit, rank=rank, order=order))

        gs.friend_calling_cards = calling_cards
        # The called cards are public — the whole table needs to know what to
        # watch for, and CalledCardsStrip shows them anyway.
        called_str = ', '.join(calling_card_str(cc) for cc in calling_cards)
        record_event(
            gs, Event.FRIENDS_CALLED,
            f'{player_name(gs, player_uuid)} called {called_str}',
            player_uuid,
            clause=f'called {called_str}',
        )
        advance_alpha_phase(gs)

        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_call_friends: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('kitty_exchange')
@one_change_at_a_time
def handle_kitty_exchange(data):
    """Alpha player exchanges kitty cards — takes the kitty into hand, discards same number.

    Expected data: {
        'game_code': '<code>',
        'discarded_cards': [{'suit': '<SUIT>', 'rank': '<RANK>'}, ...]
    }
    """
    try:
        game_code = data.get('game_code', '').lower()
        discarded_data = data.get('discarded_cards', [])

        gs, player_uuid, err = validate_player(game_code)
        if err:
            emit_validation_error(err)
            return

        # Validate: must be in kitty sort phase
        if gs.game_event_state != GameEventState.WAITING_ON_ALPHA_KITTY_SORT:
            emit('error', {'message': 'Not in kitty exchange phase'})
            return

        # Validate: only the alpha
        if gs.current_alpha_player.player_uuid != player_uuid:
            emit('error', {'message': 'Only the alpha player can exchange kitty'})
            return

        kitty_size = len(gs.cards_in_deck)
        if len(discarded_data) != kitty_size:
            emit('error', {'message': f'Must discard exactly {kitty_size} cards, got {len(discarded_data)}'})
            return

        # Parse discarded cards
        discarded_cards = []
        for dc in discarded_data:
            try:
                discarded_cards.append(Card(suit=parse_suit(dc['suit']), rank=parse_rank(dc['rank'])))
            except (ValueError, KeyError):
                emit('error', {'message': f'Invalid card: {dc}'})
                return

        # Add kitty to alpha's hand
        hand = gs.players_and_hand.get(player_uuid, [])
        hand.extend(gs.cards_in_deck)
        gs.cards_in_deck = []

        # Remove discarded cards from hand
        remaining_hand = list(hand)
        for dc in discarded_cards:
            found = False
            for i, hc in enumerate(remaining_hand):
                if hc.suit == dc.suit and hc.rank == dc.rank:
                    remaining_hand.pop(i)
                    found = True
                    break
            if not found:
                emit('error', {'message': f'Card not in hand: {card_emoji_str(Card(rank=dc.rank, suit=dc.suit))}'})
                return

        gs.players_and_hand[player_uuid] = remaining_hand
        gs.card_out_of_play = discarded_cards

        # Count only, never the cards themselves: what the alpha buried is
        # private, and naming it would hand the defenders the round.
        record_event(
            gs, Event.KITTY_DISCARDED,
            f'{player_name(gs, player_uuid)} put {len(discarded_cards)} '
            f'card{"" if len(discarded_cards) == 1 else "s"} in the kitty',
            player_uuid,
        )

        advance_alpha_phase(gs)

        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_kitty_exchange: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('next_round')
@one_change_at_a_time
def handle_next_round(data):
    """Host starts the next round after a round ends.

    Expected data: { 'game_code': '<code>' }
    """
    try:
        game_code = data.get('game_code', '').lower()

        gs, player_uuid, err = validate_player(game_code)
        if err:
            emit_validation_error(err)
            return

        # Validate: must be in round ended state
        if gs.game_event_state != GameEventState.ROUND_ENDED:
            emit('error', {'message': 'Not in round-ended state'})
            return

        # Validate: only host can advance
        if str(gs.hosting_player.uuid) != player_uuid:
            emit('error', {'message': 'Only the host can start the next round'})
            return

        # HR-8: open seats nobody took leave the table and approved watchers
        # join it, before the deal. The alpha passes to the next seat in turn,
        # settled before either so that neither changes who it is.
        next_alpha_uuid, problem = prepare_next_round(gs, now())
        if problem:
            emit('error', {'message': problem})
            return
        num_players = len(gs.player_order)

        # Clear round state
        gs.cards_in_deck = []
        clear_active_pile(gs)
        gs.card_in_discard_pile = []
        gs.card_out_of_play = []
        gs.leading_hand_of_subround = []
        gs.current_hand_played = []
        gs.friend_calling_cards = []
        gs.current_friends_of_alpha = []
        gs.all_friends_found = False
        gs.last_trick_winner = ''
        gs.round_winner_side = ''
        gs.round_defender_points = 0
        gs.round_promotion_levels = 0
        gs.round_promoted_players = []
        gs.declare_trump = DeclareTrump(rank=None, suit=None)

        # Reset scores for the new round
        for uuid in gs.players_round_score:
            gs.players_round_score[uuid] = 0

        # Clear hands
        for uuid in gs.players_and_hand:
            gs.players_and_hand[uuid] = []

        # Build and deal new deck
        deck_count = number_of_decks(num_players)
        cards_per_person = number_of_card_to_deal(num_players)
        add_deck_to_game(gs, deck_count)
        deal_to_players(gs, cards_per_person)

        # Set new alpha
        set_player_as_alpha(gs, next_alpha_uuid)
        set_player_as_leading_player(gs, next_alpha_uuid)

        advance_alpha_phase(gs)

        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_next_round: %s", e)
        emit('error', {'message': str(e)})


def leave_as_watcher(gs: GameState, watcher_uuid: str):
    """A watcher stops watching. Nothing at the table depends on them."""
    game_code = gs.game_code.lower()
    unbind_sockets(game_code, watcher_uuid)
    try:
        leave_room(game_code)
    except Exception:
        pass
    remove_watcher(gs, watcher_uuid)
    update_redis_cache(gs)


def host_only(game_code: str, what: str) -> tuple:
    """validate_player, and only the host may go on. Emits any refusal itself.

    Returns (game_state, host_uuid), or (None, None) when refused."""
    gs, player_uuid, err = validate_player(game_code)
    if err:
        emit_validation_error(err)
        return None, None
    if not gs.hosting_player or str(gs.hosting_player.uuid) != player_uuid:
        emit('error', {'message': f'Only the host can {what}'})
        return None, None
    return gs, player_uuid


@socketio.on('volunteer_for_seat')
@one_change_at_a_time
def handle_volunteer_for_seat(data):
    """A watcher offers to take over a seat whose player dropped or left (HR-8).

    Expected data: { 'game_code': '<code>', 'seat_uuid': '<seat uuid>' }

    Only an offer: the host's approval is what seats them."""
    try:
        game_code = data.get('game_code', '').lower()
        gs, watcher_uuid, err = validate_member(game_code)
        if err:
            emit_validation_error(err)
            return
        problem = volunteer(gs, watcher_uuid, data.get('seat_uuid', ''))
        if problem:
            emit('error', {'message': problem})
            return
        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_volunteer_for_seat: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('ask_to_join')
@one_change_at_a_time
def handle_ask_to_join(data):
    """A watcher asks to play as an extra player from the next round (HR-8).

    Expected data: { 'game_code': '<code>' }"""
    try:
        game_code = data.get('game_code', '').lower()
        gs, watcher_uuid, err = validate_member(game_code)
        if err:
            emit_validation_error(err)
            return
        problem = ask_to_join(gs, watcher_uuid)
        if problem:
            emit('error', {'message': problem})
            return
        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_ask_to_join: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('withdraw_seat_request')
@one_change_at_a_time
def handle_withdraw_seat_request(data):
    """A watcher takes back their offer or their request to join.

    Expected data: { 'game_code': '<code>' }"""
    try:
        game_code = data.get('game_code', '').lower()
        gs, watcher_uuid, err = validate_member(game_code)
        if err:
            emit_validation_error(err)
            return
        if withdraw_request(gs, watcher_uuid):
            update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_withdraw_seat_request: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('approve_seat_request')
@one_change_at_a_time
def handle_approve_seat_request(data):
    """Host approves a watcher's request to play (HR-8). The approval is final.

    Expected data: { 'game_code': '<code>', 'watcher_uuid': '<uuid>',
                     'level': <Rank value, for a joiner only> }

    A volunteer takes their seat on the spot, even if its player has time left
    to come back; the sockets move with the seat. A joiner is seated when the
    next round starts, on `level`."""
    try:
        game_code = data.get('game_code', '').lower()
        gs, _ = host_only(game_code, 'approve a request to play')
        if gs is None:
            return
        watcher_uuid = data.get('watcher_uuid', '')
        problem, seat_uuid, former_uuid = approve_request(gs, watcher_uuid, now(), data.get('level'))
        if problem:
            emit('error', {'message': problem})
            return
        if seat_uuid:
            # Anyone still holding the seat's socket is a watcher now; then the
            # volunteer's sockets take the seat. In that order, or the second
            # would sweep the volunteer straight back out.
            rebind_sockets(game_code, seat_uuid, former_uuid)
            rebind_sockets(game_code, watcher_uuid, seat_uuid)
        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_approve_seat_request: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('decline_seat_request')
@one_change_at_a_time
def handle_decline_seat_request(data):
    """Host turns a watcher's request down. They go on watching.

    Expected data: { 'game_code': '<code>', 'watcher_uuid': '<uuid>' }"""
    try:
        game_code = data.get('game_code', '').lower()
        gs, _ = host_only(game_code, 'decline a request to play')
        if gs is None:
            return
        problem = decline_request(gs, data.get('watcher_uuid', ''))
        if problem:
            emit('error', {'message': problem})
            return
        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_decline_seat_request: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('end_round_as_draw')
@one_change_at_a_time
def handle_end_round_as_draw(data):
    """Host ends a round an empty seat is holding up, as a draw (HR-8).

    Expected data: { 'game_code': '<code>' }

    Only while a seat is actually open — at once for a player who pressed
    Leave, after a minute for one who lost connection. Until then the table is
    still giving them their chance to come back."""
    try:
        game_code = data.get('game_code', '').lower()
        gs, _ = host_only(game_code, 'end the round')
        if gs is None:
            return
        if not round_held_up(gs, now()):
            emit('error', {'message': 'The round can only be ended as a draw while a seat is empty.'})
            return
        end_round_as_draw(gs)
        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_end_round_as_draw: %s", e)
        emit('error', {'message': str(e)})


def problem_with_play(gs: GameState, player_uuid: str, cards_data) -> tuple:
    """Parse a requested play and say what is wrong with it, if anything.

    Returns (cards, reason): reason is None for a legal play, otherwise a
    sentence for the player. Shared by play_cards, which refuses on it, and
    check_play, which only reports it — so a play the check calls legal is
    exactly a play the server will take. Says nothing about whose turn it is;
    each caller decides that for itself."""
    played_cards = []
    for cd in cards_data:
        try:
            played_cards.append(Card(suit=parse_suit(cd['suit']), rank=parse_rank(cd['rank'])))
        except (ValueError, KeyError, TypeError):
            return [], f'Invalid card: {cd}'

    if not played_cards:
        return [], 'No cards provided'

    # All cards must be in the player's hand, counted so a pair needs two copies.
    temp_hand = list(gs.players_and_hand.get(player_uuid, []))
    for pc in played_cards:
        match = next((i for i, hc in enumerate(temp_hand)
                      if hc.suit == pc.suit and hc.rank == pc.rank), None)
        if match is None:
            return played_cards, f'{card_emoji_str(pc)} is not in your hand.'
        temp_hand.pop(match)

    # Every rule about what may be played, in one place, phrased for the
    # player rather than as a bare rejection. Runs after the cards are known
    # to be in hand, so the explanation can talk about the real hand.
    _, player_obj = find_player(gs, player_uuid)
    return played_cards, explain_illegal_play(gs, player_obj, played_cards)


@socketio.on('check_play')
def handle_check_play(data):
    """Say whether a play would be legal, without playing it.

    Lets a player pick their answer to a trick before their turn comes round
    and find out now, rather than when it is too late to think again. The
    answer only goes back to the player who asked.

    Only a follow can be checked ahead of the turn. Whether a follow is legal
    depends on nothing but the lead and the player's own hand, and neither
    moves until they play — so a check made early still holds when the turn
    arrives. A lead is different: a group of top cards is judged against what
    everyone else holds, and nobody knows they are leading until the trick
    before is won.

    Expected data: {
        'game_code': '<code>',
        'cards': [{'suit': '<SUIT>', 'rank': '<RANK>'}, ...],
        'request_id': <anything, echoed back so the client can drop stale answers>
    }
    Replies with 'play_check': {'request_id', 'legal': bool, 'message': str}
    """
    try:
        game_code = data.get('game_code', '').lower()
        request_id = data.get('request_id')

        gs, player_uuid, err = validate_player(game_code)
        if err:
            emit_validation_error(err)
            return

        def answer(reason):
            emit('play_check', {
                'request_id': request_id,
                'legal': reason is None,
                'message': reason or '',
            })

        if gs.game_event_state != GameEventState.ROUND_STARTED:
            answer('Not in a playing phase')
            return

        my_turn = gs.current_player.player_uuid == player_uuid
        if not my_turn:
            if not gs.leading_hand_of_subround:
                answer('Nothing has been led yet — wait for the lead before picking an answer.')
                return
            if player_uuid in gs.active_pile_player_uuids:
                answer('You have already played to this trick.')
                return

        _, reason = problem_with_play(gs, player_uuid, data.get('cards', []))
        answer(reason)
    except Exception as e:
        log.exception("Error in handle_check_play: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('play_cards')
@one_change_at_a_time
def handle_play_cards(data):
    """Player plays one or more cards during a trick.

    Expected data: {
        'game_code': '<code>',
        'cards': [{'suit': '<SUIT>', 'rank': '<RANK>'}, ...]
    }
    Also supports legacy single-card format:
        'card': {'suit': '<SUIT>', 'rank': '<RANK>'}
    """
    try:
        game_code = data.get('game_code', '').lower()

        # Support both 'cards' (list) and 'card' (single) formats
        cards_data = data.get('cards', [])
        if not cards_data and 'card' in data:
            cards_data = [data['card']]

        gs, player_uuid, err = validate_player(game_code)
        if err:
            emit_validation_error(err)
            return

        # Validate: must be in round started phase
        if gs.game_event_state != GameEventState.ROUND_STARTED:
            emit('error', {'message': 'Not in a playing phase'})
            return

        # Validate: it must be this player's turn
        current_uuid = gs.player_order[gs.current_player.index].uuid
        if current_uuid != player_uuid:
            emit('error', {'message': 'It is not your turn'})
            return

        played_cards, reason = problem_with_play(gs, player_uuid, cards_data)
        if reason:
            emit('error', {'message': reason})
            return

        hand = gs.players_and_hand.get(player_uuid, [])
        trump = {'suit': gs.declare_trump.suit, 'rank': gs.declare_trump.rank}
        is_leading = len(gs.leading_hand_of_subround) == 0

        # Remove cards from hand (work backwards to avoid index shifting)
        remaining_hand = list(hand)
        for pc in played_cards:
            for i, hc in enumerate(remaining_hand):
                if hc.suit == pc.suit and hc.rank == pc.rank:
                    remaining_hand.pop(i)
                    break
        gs.players_and_hand[player_uuid] = remaining_hand

        # Add cards to active pile, recorded against the player who played them
        play_cards_into_active_pile(gs, player_uuid, played_cards)
        gs.current_hand_played = played_cards

        # Only a lead of more than one card is worth interrupting for, and only
        # the lead: a tractor sets the shape everyone else now has to answer,
        # where the same cards played fourth into a decided trick are just a
        # play. Singles are the ordinary case and name_leading_play skips them.
        play_shape = name_leading_play(trump, played_cards) if is_leading else ''
        record_event(
            gs, Event.HAND_PLAY,
            f'{player_name(gs, player_uuid)} played {" ".join(card_list_to_emoji_str_list(played_cards))}',
            player_uuid,
            clause=f'led with {play_shape}' if play_shape else '',
        )

        # If this is the leading play, set it
        if is_leading:
            gs.leading_hand_of_subround = list(played_cards)
            set_winning_player_of_round(gs, player_uuid)

        # Check friend card, announcing anyone this play just outed — including
        # a double jump and the alpha playing a card they called themselves.
        for revealed_uuid in check_friend_card_played(gs, player_uuid, played_cards):
            message, clause = friend_reveal_announcement(
                gs, revealed_uuid, player_name(gs, revealed_uuid))
            record_event(gs, Event.FRIEND_REVEALED, message, revealed_uuid, clause=clause)

        # Determine if this play beats the current winner
        if not is_leading:
            leading_hand = gs.leading_hand_of_subround
            winning_uuid = gs.winning_player_of_round.player_uuid

            winning_play_cards = cards_played_by(gs, winning_uuid)

            if winning_play_cards:
                # Use the appropriate decision function based on play type
                play_type = determine_leading_play(trump, leading_hand)
                beats_winner = False

                if play_type == 'single':
                    beats_winner = single_card_lead_decision(trump, leading_hand[0], winning_play_cards[0], played_cards[0])
                elif play_type == 'identical_set':
                    beats_winner = identical_set_lead_decision(trump, leading_hand, winning_play_cards, played_cards)
                elif play_type == 'identical_sequence':
                    beats_winner = sequence_identical_set_lead_decision(trump, leading_hand, winning_play_cards, played_cards)
                elif play_type == 'group_of_top':
                    beats_winner = leading_group_of_top_decision(trump, leading_hand, winning_play_cards, played_cards)

                if beats_winner:
                    set_winning_player_of_round(gs, player_uuid)

        # Advance to next player's turn
        continue_trick, next_player = next_person_turn(gs)

        if continue_trick:
            gs.current_player.player_uuid = next_player.uuid
            update_redis_cache(gs)
        else:
            trick_winner_uuid = gs.winning_player_of_round.player_uuid
            gs.last_trick_winner = trick_winner_uuid
            # Read before calculate_rounds_points and reset_round, which clear
            # the pile these come out of.
            winning_cards = ' '.join(
                card_list_to_emoji_str_list(cards_played_by(gs, trick_winner_uuid)))
            won_with = f' with {winning_cards}' if winning_cards else ''
            # What the trick was worth: every point in the pile, not just the
            # winner's own cards — taking a trick takes the lot.
            #
            # Said out loud even when hide_scores_until_round_end is on. That
            # rule withholds the running totals; it does not censor what just
            # happened on a table everyone was watching. These cards were face
            # up and anyone could add them up, so the only thing hiding this
            # would achieve is making players do arithmetic they can already do.
            #
            # A trick worth nothing says nothing. Most tricks are worth nothing,
            # and "(0 points)" on each of them is noise that would bury the ones
            # that matter. No singular case: card points only come in fives.
            points_won = point_card_pile(gs.cards_in_active_pile)
            worth = f' ({points_won} points)' if points_won else ''
            record_event(
                gs, Event.TRICK_WON,
                f'{player_name(gs, trick_winner_uuid)} won the trick{won_with}{worth}',
                trick_winner_uuid,
                clause=f'won the trick{won_with}{worth}',
            )
            calculate_rounds_points(gs)

            if is_round_over(gs):
                handle_end_of_round(gs)
            else:
                reset_round(gs)

            update_redis_cache(gs)

    except Exception as e:
        log.exception("Error in handle_play_cards: %s", e)
        emit('error', {'message': str(e)})


def handle_end_of_round(gs: GameState):
    """Calculate final round scores, promote levels, check game-over."""
    num_players = len(gs.player_order)

    # Determine teams and their shared point totals
    alpha_team = alpha_team_uuids(gs)
    defender_team = defender_team_uuids(gs)
    alpha_points, defender_points = team_round_points(gs)

    # If defenders won the last trick, kitty points count double
    if gs.last_trick_winner in defender_team and gs.card_out_of_play:
        kitty_points = point_card_pile(gs.card_out_of_play)
        defender_points += kitty_points * 2
        gs.players_round_score[gs.last_trick_winner] = gs.players_round_score.get(gs.last_trick_winner, 0) + kitty_points * 2

    # Move remaining active pile to discard
    gs.card_in_discard_pile.extend(gs.cards_in_active_pile)
    clear_active_pile(gs)
    gs.leading_hand_of_subround = []
    gs.current_hand_played = []

    # Calculate level promotion
    num_packs = number_of_decks(num_players)
    alpha_max = max_alpha_team_size(num_players)
    alpha_actual = len(alpha_team)
    # HR-6: more points wins, by one level, unless the table chose the scaled
    # ladder. defender_points has the doubled kitty in it by now.
    winning_side, promotion_levels = promotion_for_round(
        num_packs, alpha_points, defender_points, alpha_actual, alpha_max,
        scaled=gs.settings.scaled_level_promotion,
    )

    gs.round_winner_side = winning_side
    gs.round_defender_points = defender_points
    gs.round_promotion_levels = promotion_levels
    gs.round_promoted_players = []

    # Apply promotions
    game_over = False
    if winning_side == 'trump_maker' and promotion_levels > 0:
        for uuid in alpha_team:
            current_val = int(gs.player_levels.get(uuid, Rank.TWO.value))
            new_val, passed_ace = advance_level(current_val, promotion_levels)
            gs.player_levels[uuid] = rank_from_value(new_val).value
            gs.round_promoted_players.append(uuid)
            if passed_ace:
                gs.game_winner = uuid
                game_over = True
    elif winning_side == 'defender' and promotion_levels > 0:
        for uuid in defender_team:
            current_val = int(gs.player_levels.get(uuid, Rank.TWO.value))
            new_val, passed_ace = advance_level(current_val, promotion_levels)
            gs.player_levels[uuid] = rank_from_value(new_val).value
            gs.round_promoted_players.append(uuid)
            if passed_ace:
                gs.game_winner = uuid
                game_over = True

    if game_over:
        gs.game_event_state = GameEventState.GAME_ENDED
    else:
        gs.game_event_state = GameEventState.ROUND_ENDED


def connected_player_uuids(game_code: str) -> set:
    """Players of this game that currently hold a live socket.

    Derived from SID_TO_PLAYER rather than stored on the game, so it cannot go
    stale: a dropped socket is gone from the map before anything reads it, and a
    server restart starts from an honest empty state."""
    game_code = game_code.lower()
    return {uuid for gc, uuid in SID_TO_PLAYER.values() if gc == game_code}


def rebind_sockets(game_code: str, from_uuid: str, to_uuid: str):
    """Make every socket acting for one uuid act for another. '' unbinds them."""
    game_code = game_code.lower()
    for sid, (gc, uuid) in list(SID_TO_PLAYER.items()):
        if gc == game_code and uuid == from_uuid:
            if to_uuid:
                SID_TO_PLAYER[sid] = (gc, to_uuid)
            else:
                del SID_TO_PLAYER[sid]


def unbind_sockets(game_code: str, uuid: str):
    rebind_sockets(game_code, uuid, '')


def close_room(game_state: GameState):
    """Shut a game down for good and send everyone in it home (HR-8)."""
    game_code = game_state.game_code.lower()
    log.info("Closing %s: too long with fewer than 5 players connected", game_code)
    upsert_game_state_in_db(game_code, game_state.model_dump(mode='json'), False)
    socketio.emit('session_invalid', {
        'reason': 'room_closed',
        'message': 'This room closed after 10 minutes with fewer than 5 players connected.',
    }, room=game_code)
    for sid, (gc, _) in list(SID_TO_PLAYER.items()):
        if gc == game_code:
            del SID_TO_PLAYER[sid]
    WATCHED_GAMES.discard(game_code)


def broadcast_player_views(game_state: GameState):
    """Send everyone connected their own view: a player theirs, a watcher the table's."""
    game_code = game_state.game_code.lower()
    connected = connected_player_uuids(game_code)
    at = now()
    for sid, (gc, member_uuid) in list(SID_TO_PLAYER.items()):
        if gc != game_code:
            continue
        try:
            if member_uuid in game_state.player_dict:
                view = player_view_state(game_state, member_uuid, connected, at)
            elif member_uuid in game_state.watchers:
                view = watcher_view_state(game_state, member_uuid, connected, at)
            else:
                continue
            socketio.emit('game_stats', view.to_json_dict(), room=sid)
        except Exception as e:
            log.exception("Failed to emit view to %s: %s", member_uuid, e)


def update_redis_cache(game_state: GameState):
    game_code = game_state.game_code.lower()
    upsert_game_state_in_db(game_code, game_state.model_dump(mode='json'), True)
    try:
        broadcast_player_views(game_state)
    except Exception as e:
        log.exception("Failed to emit game_stats for %s: %s", game_code, e)


def get_redis_cache(game_code) -> GameState:
    game_code = game_code.lower()
    output = get_game_state_in_db(game_code)
    if output is None:
        raise GameNotFoundError(game_code)
    return GameState(**output)


if __name__ == "__main__":
    socketio.run(app, port=5050)
