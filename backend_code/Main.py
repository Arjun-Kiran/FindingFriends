from uuid import uuid4
from typing import Dict, Tuple

import hashlib
import eventlet
eventlet.monkey_patch()
from flask import Flask, jsonify, Response
from flask import request, redirect
from flask_socketio import SocketIO, emit, join_room


from Game.Components.GameState import GameState
from Game.Session.Words import generate_word_session
from Game.Views.GameStateView import game_state_str
from Game.Views.PlayerView import player_view_state, PlayerView
from Game.Components.Player import Player
from Game.Modules.EventEnum import GameEventState
from Game.Systems.GameStateSystem import add_player, add_deck_to_game, deal_to_players, generate_player, set_player_as_alpha, set_player_as_leading_player, set_game_state_trump, find_player
from Game.Systems.DeckSystem import number_of_decks, number_of_card_to_deal
from Game.Modules.CardConstants import Suit, Rank
from Database.database import build_game_state_table, upsert_game_state_in_db, get_game_state_in_db, get_game_update_time_in_db

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')


build_game_state_table()

MOCK_REDIS_CACHE: Dict[str, GameState] = dict()
SITE_URL = "http://127.0.0.1:5000"

# Maps socket session ID -> (game_code, player_uuid)
SID_TO_PLAYER: Dict[str, Tuple[str, str]] = dict()

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
        return f'<p>Game is not accepting new players</p>'

    if gs:
        if len(request.args) == 0:
            return f'''<p>No Arguments</p>'''
        nick_name = request.args.get('nick_name')
        new_player = generate_player(name=nick_name)
        new_gs = add_player(gs, new_player)
        update_redis_cache(new_gs)
        game_link = f'/game/{game_code.lower()}/player/{new_player.uuid}'
        return jsonify({
            'game_link': game_link,
            'new_player_uuid': new_player.uuid,
            'nick_name': nick_name
        })
    return f'<p>Game Does Not Exists</p>'


@app.route("/game/<game_code>/player/<player_uuid>")
def game_session(game_code: str, player_uuid: str):
    game_state = get_redis_cache(game_code)
    player_view = player_view_state(game_state, player_uuid)
    return player_view.json()


@socketio.on('message')
def handle_message(message):
    print("Received message: " + message)


@socketio.on('connect')
def handle_connect():
    print("Client connected to WebSocket")


@socketio.on('disconnect')
def handle_disconnect():
    from flask import request as flask_request
    sid = flask_request.sid
    if sid in SID_TO_PLAYER:
        del SID_TO_PLAYER[sid]
    print(f"Client disconnected: {sid}")


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

        join_room(game_code)

        # Track which socket belongs to which player
        if player_uuid:
            SID_TO_PLAYER[flask_request.sid] = (game_code, player_uuid)

        # Send the current game state to the joining client (emit only to them)
        try:
            gs = get_redis_cache(game_code)
            if player_uuid and player_uuid in gs.player_dict:
                pv = player_view_state(gs, player_uuid)
                emit('game_stats', pv.dict())
            else:
                emit('game_stats', {'game_event_state': gs.game_event_state.value, 'number_of_players': len(gs.player_order)})
        except Exception as e:
            print(f"Could not fetch game state for {game_code}: {e}")
    except Exception as e:
        print(f"Error in handle_join: {e}")


@socketio.on('start_game')
def handle_start_game(data):
    """Host starts the game. Builds deck, deals cards, picks alpha.

    Expected data: { 'game_code': '<code>', 'player_uuid': '<uuid>' }
    """
    try:
        game_code = data.get('game_code', '').lower()
        player_uuid = data.get('player_uuid', '')

        gs = get_redis_cache(game_code)

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

        gs.game_event_state = GameEventState.WAITING_ON_ALPHA_CHOOSE_TRUMP
        gs.can_start_game = False

        update_redis_cache(gs)
    except Exception as e:
        print(f"Error in handle_start_game: {e}")
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

        gs = get_redis_cache(game_code)

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
            declared_suit = Suit(suit_str)
            declared_rank = Rank(rank_str)
        except ValueError:
            emit('error', {'message': f'Invalid suit or rank: {suit_str}, {rank_str}'})
            return

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
        gs.game_event_state = GameEventState.WAITING_ON_ALPHA_FRIEND_CARD_CHOICE

        update_redis_cache(gs)
    except Exception as e:
        print(f"Error in handle_declare_trump: {e}")
        emit('error', {'message': str(e)})


def broadcast_player_views(game_state: GameState):
    """Send each connected player their own filtered PlayerView."""
    game_code = game_state.game_code.lower()
    for sid, (gc, player_uuid) in SID_TO_PLAYER.items():
        if gc == game_code and player_uuid in game_state.player_dict:
            try:
                pv = player_view_state(game_state, player_uuid)
                socketio.emit('game_stats', pv.dict(), room=sid)
            except Exception as e:
                print(f"Failed to emit player view to {player_uuid}: {e}")


def update_redis_cache(game_state: GameState):
    game_code = game_state.game_code.lower()
    upsert_game_state_in_db(game_code, game_state.dict(), True)
    try:
        broadcast_player_views(game_state)
    except Exception as e:
        print(f"Failed to emit game_stats for {game_code}: {e}")


def get_redis_cache(game_code) -> GameState:
    output = get_game_state_in_db(game_code.lower())
    return GameState(**output)


if __name__ == "__main__":
    socketio.run(app)
