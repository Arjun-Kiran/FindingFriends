from uuid import uuid4
from typing import Dict, Tuple

import hashlib
from flask import Flask, jsonify, Response
from flask import request, redirect
from flask_socketio import SocketIO, emit, join_room, leave_room


from Game.Components.GameState import GameState
from Game.Session.Words import generate_word_session
from Game.Views.GameStateView import game_state_str
from Game.Views.PlayerView import player_view_state, PlayerView
from Game.Components.Player import Player
from Game.Modules.EventEnum import Event, GameEventState
from Game.Systems.EventSystem import record_event
from Game.Views.CardView import card_list_to_emoji_str_list, SUIT_EMOJI, RANK_EMOJI
from Game.Systems.GameStateSystem import add_player, add_deck_to_game, deal_to_players, generate_player, set_player_as_alpha, set_player_as_leading_player, set_game_state_trump, find_player, set_winning_player_of_round, next_person_turn, reset_round, is_round_over, remove_player, set_player_avatar, play_cards_into_active_pile, clear_active_pile
from Game.Systems.DeckSystem import number_of_decks, number_of_card_to_deal
from Game.Systems.TeamSystem import number_of_cards_to_call_friends, check_friend_card_played
from Game.Systems.DecisionSystem import beatable_components, single_card_lead_decision, identical_set_lead_decision, sequence_identical_set_lead_decision, leading_group_of_top_decision, determine_leading_play, legal_cards_to_play, validate_multi_card_play, is_trump
from Game.Systems.PointSystem import calculate_rounds_points, point_card_pile, calculate_level_promotion, max_alpha_team_size, advance_level, rank_from_value, alpha_team_uuids, defender_team_uuids, team_round_points
from Game.Components.GameState import DeclareCallingCard, DeclareTrump
from Game.Modules.CardConstants import Suit, Rank
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

# Maps socket session ID -> (game_code, player_uuid)
SID_TO_PLAYER: Dict[str, Tuple[str, str]] = dict()


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


def validate_player(game_code: str, player_uuid: str) -> tuple:
    """Validate that a player belongs to a game.

    Returns (game_state, error) where error is None or a dict with a 'code' and
    a 'message'. Codes 'game_not_found' and 'player_not_found' mean the client's
    session is dead rather than its request being wrong."""
    if not game_code:
        return None, {'code': 'missing_game_code', 'message': 'missing game_code'}
    if not player_uuid:
        return None, {'code': 'missing_player_uuid', 'message': 'missing player_uuid'}
    try:
        gs = get_redis_cache(game_code)
    except GameNotFoundError as e:
        return None, {'code': 'game_not_found', 'message': str(e)}
    except Exception as e:
        log.exception("Failed to load game %s: %s", game_code, e)
        return None, {'code': 'load_failed', 'message': 'Could not load that game'}
    if player_uuid not in gs.player_dict:
        return None, {'code': 'player_not_found', 'message': 'You are no longer part of this game'}
    return gs, None


SESSION_INVALID_CODES = ('game_not_found', 'player_not_found')


def emit_validation_error(error: dict):
    """Emit a validation failure, routing dead sessions to 'session_invalid'."""
    if error['code'] in SESSION_INVALID_CODES:
        emit_session_invalid(error['code'], error['message'])
        return
    emit('error', {'message': error['message']})


@app.route("/")
def hello_world():
    return '''Hello, backend is alive.'''


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
    gs = get_redis_cache(game_code.lower())

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
    update_redis_cache(new_gs)
    game_link = f'/game/{game_code.lower()}/player/{new_player.uuid}'
    return jsonify({
        'game_link': game_link,
        'new_player_uuid': new_player.uuid,
        'nick_name': nick_name
    })


@app.route("/game/<game_code>/player/<player_uuid>")
def game_session(game_code: str, player_uuid: str):
    game_state = get_redis_cache(game_code)
    if player_uuid not in game_state.player_dict:
        return jsonify({
            'error': 'player_not_found',
            'message': 'You are no longer part of this game'
        }), 404
    player_view = player_view_state(game_state, player_uuid, connected_player_uuids(game_code))
    return jsonify(player_view.to_json_dict())


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
        game_code, player_uuid = SID_TO_PLAYER[sid]
        del SID_TO_PLAYER[sid]
        try:
            gs = get_redis_cache(game_code)
        except GameNotFoundError:
            # Session was already invalidated; nothing left to clean up.
            log.info("Client disconnected: %s", sid)
            return
        except Exception as e:
            log.warning("Could not load game %s on disconnect: %s", game_code, e)
            log.info("Client disconnected: %s", sid)
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
                record_event(gs, Event.PLAYER_DISCONNECTED, f'{name} lost connection', player_uuid)
                update_redis_cache(gs)
        except Exception as e:
            log.exception("Error handling player disconnect: %s", e)
    log.info("Client disconnected: %s", sid)


@socketio.on('leave_lobby')
def handle_leave_lobby(data):
    game_code = data.get('game_code', '').lower()
    player_uuid = data.get('player_uuid', '')
    gs, err = validate_player(game_code, player_uuid)
    if err:
        emit_validation_error(err)
        return

    if gs.game_event_state != GameEventState.WAITING_FOR_PLAYERS_TO_JOIN:
        emit('error', {'message': 'Can only leave the lobby before the game starts'})
        return

    remove_player(gs, player_uuid)
    try:
        leave_room(game_code)
    except Exception:
        pass

    if len(gs.player_order) == 0:
        upsert_game_state_in_db(game_code, gs.model_dump(mode='json'), False)
        return

    update_redis_cache(gs)


@socketio.on('leave_game')
def handle_leave_game(data):
    """A player deliberately leaves, in the lobby or mid-game.

    Distinct from a dropped connection on purpose. A disconnect holds the seat
    and the table waits for them to come back; someone who left is not coming
    back, and the others deserve to be told which of the two happened.

    The seat is still held mid-game — the hand is dealt and turn order depends
    on them, so removing the player would break the round.
    """
    from flask import request as flask_request
    game_code = data.get('game_code', '').lower()
    player_uuid = data.get('player_uuid', '')

    gs, err = validate_player(game_code, player_uuid)
    if err:
        emit_validation_error(err)
        return

    # Forget the socket before anything else: the disconnect that follows a
    # player closing the tab would otherwise announce "lost connection" on top
    # of "left the game".
    SID_TO_PLAYER.pop(flask_request.sid, None)

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
        log.info("Player %s left %s mid-game, holding their seat", player_uuid, game_code)
        record_event(gs, Event.PLAYER_LEFT,
                     f'{player_name(gs, player_uuid)} left the game', player_uuid)

    update_redis_cache(gs)


@socketio.on('join')
def handle_join(data):
    """Client asks to join a game's room so it receives updates for that game.

    Expected data: { 'game_code': '<code>', 'player_uuid': '<uuid>' }
    """
    try:
        from flask import request as flask_request
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')
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

        if player_uuid and player_uuid not in gs.player_dict:
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

        # Track which socket belongs to which player
        if player_uuid:
            SID_TO_PLAYER[flask_request.sid] = (game_code, player_uuid)

        try:
            if returning:
                log.info("Player %s reconnected to %s", player_uuid, game_code)
                record_event(gs, Event.PLAYER_RECONNECTED, f'{player_name(gs, player_uuid)} reconnected',
                             player_uuid)
                update_redis_cache(gs)
            elif player_uuid:
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
def handle_choose_avatar(data):
    """Player picks the animal emoji that stands for them at the table.

    Expected data: { 'game_code': '<code>', 'player_uuid': '<uuid>', 'avatar': '<emoji>' }

    Lobby only. Once cards are dealt the avatar is how everyone reads the
    players bar, the scoreboards and the trick pile, so letting someone swap
    identity mid-hand would make the table unreadable.
    """
    try:
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')
        avatar = data.get('avatar', '')

        gs, err = validate_player(game_code, player_uuid)
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


@socketio.on('start_game')
def handle_start_game(data):
    """Host starts the game. Builds deck, deals cards, picks alpha.

    Expected data: { 'game_code': '<code>', 'player_uuid': '<uuid>' }
    """
    try:
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')

        gs, err = validate_player(game_code, player_uuid)
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

        # Host is the first alpha player
        set_player_as_alpha(gs, player_uuid)
        set_player_as_leading_player(gs, player_uuid)

        enter_alpha_phase(gs, GameEventState.WAITING_ON_ALPHA_CHOOSE_TRUMP)
        gs.can_start_game = False

        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_start_game: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('declare_trump')
def handle_declare_trump(data):
    """Alpha player declares trump suit by selecting a card from their hand.

    Expected data: { 'game_code': '<code>', 'player_uuid': '<uuid>', 'suit': '<SUIT>', 'rank': '<RANK>' }
    The rank must match the alpha player's current level.
    """
    try:
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')
        suit_str = data.get('suit', '')
        rank_str = data.get('rank', '')

        gs, err = validate_player(game_code, player_uuid)
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

        # Hidding this logic for now since we are allowing free choice of trump for testing purposes, but we may want to enforce it later
        if 1 != 1:
            # Validate: the rank must match the alpha player's level
            alpha_level = gs.player_levels.get(player_uuid, Rank.TWO.value)
            if declared_rank.value != alpha_level:
                emit('error', {'message': f'You must declare a card matching your level ({alpha_level})'})
                return

            # Validate: the alpha must hold a card with this suit+rank
            hand = gs.players_and_hand.get(player_uuid, [])
            has_card = any(c.suit == declared_suit and c.rank == declared_rank for c in hand)
            if not has_card:
                emit('error', {'message': 'You do not hold a card with that suit and rank'})
                return

        # Set trump
        set_game_state_trump(gs, declared_suit, declared_rank)
        record_event(
            gs, Event.TRUMP_DECLARED,
            f'{player_name(gs, player_uuid)} declared {SUIT_EMOJI[declared_suit]} as trump',
            player_uuid,
        )
        enter_alpha_phase(gs, GameEventState.WAITING_ON_ALPHA_FRIEND_CARD_CHOICE)

        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_declare_trump: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('call_friends')
def handle_call_friends(data):
    """Alpha player calls friend cards to determine secret partners.

    Expected data: {
        'game_code': '<code>',
        'player_uuid': '<uuid>',
        'calling_cards': [{'suit': '<SUIT>', 'rank': '<RANK>', 'order': <int>}, ...]
    }
    """
    try:
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')
        calling_cards_data = data.get('calling_cards', [])

        gs, err = validate_player(game_code, player_uuid)
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

            # Called cards must not be trumps
            if suit == gs.declare_trump.suit or rank == gs.declare_trump.rank:
                emit('error', {'message': f'Called cards must not be trumps: {rank.value} of {suit.value}'})
                return

            if order < 1:
                emit('error', {'message': 'Order must be at least 1'})
                return

            calling_cards.append(DeclareCallingCard(suit=suit, rank=rank, order=order))

        gs.friend_calling_cards = calling_cards
        # The called cards are public — the whole table needs to know what to
        # watch for, and CalledCardsStrip shows them anyway.
        record_event(
            gs, Event.FRIENDS_CALLED,
            f'{player_name(gs, player_uuid)} called '
            f'{", ".join(calling_card_str(cc) for cc in calling_cards)}',
            player_uuid,
        )
        enter_alpha_phase(gs, GameEventState.WAITING_ON_ALPHA_KITTY_SORT)

        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_call_friends: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('kitty_exchange')
def handle_kitty_exchange(data):
    """Alpha player exchanges kitty cards — takes the kitty into hand, discards same number.

    Expected data: {
        'game_code': '<code>',
        'player_uuid': '<uuid>',
        'discarded_cards': [{'suit': '<SUIT>', 'rank': '<RANK>'}, ...]
    }
    """
    try:
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')
        discarded_data = data.get('discarded_cards', [])

        gs, err = validate_player(game_code, player_uuid)
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
                emit('error', {'message': f'Card not in hand: {dc.rank.value} of {dc.suit.value}'})
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

        # Set alpha as leading player for first trick and start the round
        set_player_as_leading_player(gs, player_uuid)
        gs.game_event_state = GameEventState.ROUND_STARTED

        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_kitty_exchange: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('next_round')
def handle_next_round(data):
    """Host starts the next round after a round ends.

    Expected data: { 'game_code': '<code>', 'player_uuid': '<uuid>' }
    """
    try:
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')

        gs, err = validate_player(game_code, player_uuid)
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

        num_players = len(gs.player_order)

        # Rotate alpha: next player after current alpha in player_order
        current_alpha_uuid = gs.current_alpha_player.player_uuid
        current_alpha_idx = 0
        for i, p in enumerate(gs.player_order):
            if p.uuid == current_alpha_uuid:
                current_alpha_idx = i
                break
        next_alpha_idx = (current_alpha_idx + 1) % num_players
        next_alpha_uuid = gs.player_order[next_alpha_idx].uuid

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

        enter_alpha_phase(gs, GameEventState.WAITING_ON_ALPHA_CHOOSE_TRUMP)

        update_redis_cache(gs)
    except Exception as e:
        log.exception("Error in handle_next_round: %s", e)
        emit('error', {'message': str(e)})


@socketio.on('play_cards')
def handle_play_cards(data):
    """Player plays one or more cards during a trick.

    Expected data: {
        'game_code': '<code>',
        'player_uuid': '<uuid>',
        'cards': [{'suit': '<SUIT>', 'rank': '<RANK>'}, ...]
    }
    Also supports legacy single-card format:
        'card': {'suit': '<SUIT>', 'rank': '<RANK>'}
    """
    try:
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')

        # Support both 'cards' (list) and 'card' (single) formats
        cards_data = data.get('cards', [])
        if not cards_data and 'card' in data:
            cards_data = [data['card']]

        gs, err = validate_player(game_code, player_uuid)
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

        # Parse played cards
        played_cards = []
        for cd in cards_data:
            try:
                played_cards.append(Card(suit=parse_suit(cd['suit']), rank=parse_rank(cd['rank'])))
            except (ValueError, KeyError):
                emit('error', {'message': f'Invalid card: {cd}'})
                return

        if not played_cards:
            emit('error', {'message': 'No cards provided'})
            return

        hand = gs.players_and_hand.get(player_uuid, [])
        _, player_obj = find_player(gs, player_uuid)
        trump = {'suit': gs.declare_trump.suit, 'rank': gs.declare_trump.rank}
        is_leading = len(gs.leading_hand_of_subround) == 0

        # Leading player: validate card count is sensible (1+ cards, all same suit)
        if is_leading:
            if len(played_cards) > 1:
                if not validate_multi_card_play(gs, player_obj, played_cards):
                    # Says that the claim was false, never which part of it or
                    # who holds the answer — that would turn a rejected lead
                    # into a way of reading the other hands.
                    if beatable_components(gs, player_obj, played_cards):
                        emit('error', {'message': 'Those are not all top cards — '
                                                  'something in that suit beats part of this lead'})
                    else:
                        emit('error', {'message': 'Invalid combination of cards to lead'})
                    return
        else:
            # Following player: must play same number as leading hand
            expected_count = len(gs.leading_hand_of_subround)
            if len(played_cards) != expected_count:
                emit('error', {'message': f'Must play exactly {expected_count} card(s)'})
                return

        # Validate: all cards must be in player's hand
        temp_hand = list(hand)
        card_indices = []
        for pc in played_cards:
            found = False
            for i, hc in enumerate(temp_hand):
                if hc.suit == pc.suit and hc.rank == pc.rank:
                    card_indices.append(i)
                    temp_hand.pop(i)
                    found = True
                    break
            if not found:
                emit('error', {'message': f'Card not in your hand: {pc.rank.value} of {pc.suit.value}'})
                return

        # For single-card following plays, validate suit following
        if not is_leading and len(played_cards) == 1:
            legal_cards = legal_cards_to_play(gs, player_obj)
            is_legal = any(lc.suit == played_cards[0].suit and lc.rank == played_cards[0].rank for lc in legal_cards)
            if not is_legal:
                emit('error', {'message': 'You must follow suit if you can'})
                return

        # For multi-card following plays, validate suit following and set matching
        if not is_leading and len(played_cards) > 1:
            if not validate_multi_card_play(gs, player_obj, played_cards):
                emit('error', {'message': 'You must follow suit and play matching sets if able'})
                return

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

        record_event(
            gs, Event.HAND_PLAY,
            f'{player_name(gs, player_uuid)} played {" ".join(card_list_to_emoji_str_list(played_cards))}',
            player_uuid,
        )

        # If this is the leading play, set it
        if is_leading:
            gs.leading_hand_of_subround = list(played_cards)
            set_winning_player_of_round(gs, player_uuid)

        # Check friend card, announcing anyone this play just outed.
        for revealed_uuid in check_friend_card_played(gs, player_uuid, played_cards):
            record_event(
                gs, Event.FRIEND_REVEALED,
                f'{player_name(gs, revealed_uuid)} has joined the alpha team',
                revealed_uuid,
            )

        # Determine if this play beats the current winner
        if not is_leading:
            leading_hand = gs.leading_hand_of_subround
            winning_uuid = gs.winning_player_of_round.player_uuid

            # Find winning player's cards in the active pile by position
            leading_idx = gs.leading_player.index
            num_players = len(gs.player_order)
            num_cards_per_play = len(leading_hand)
            winning_play_cards = None

            for trick_pos in range(len(gs.cards_in_active_pile) // num_cards_per_play):
                player_idx_in_order = (leading_idx + trick_pos) % num_players
                if gs.player_order[player_idx_in_order].uuid == winning_uuid:
                    start = trick_pos * num_cards_per_play
                    winning_play_cards = gs.cards_in_active_pile[start:start + num_cards_per_play]
                    break

            if winning_play_cards is not None:
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
            record_event(
                gs, Event.TRICK_WON,
                f'{player_name(gs, trick_winner_uuid)} won the trick',
                trick_winner_uuid,
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
    _, defender_points = team_round_points(gs)

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
    winning_side, promotion_levels = calculate_level_promotion(
        num_packs, defender_points, alpha_actual, alpha_max
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


def broadcast_player_views(game_state: GameState):
    """Send each connected player their own filtered PlayerView."""
    game_code = game_state.game_code.lower()
    connected = connected_player_uuids(game_code)
    for sid, (gc, player_uuid) in list(SID_TO_PLAYER.items()):
        if gc == game_code and player_uuid in game_state.player_dict:
            try:
                pv = player_view_state(game_state, player_uuid, connected)
                socketio.emit('game_stats', pv.to_json_dict(), room=sid)
            except Exception as e:
                log.exception("Failed to emit player view to %s: %s", player_uuid, e)


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
