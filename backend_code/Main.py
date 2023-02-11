from uuid import uuid4
from typing import Dict
import time
import hashlib
from flask import Flask, jsonify, Response
from flask import request, redirect
from flask_socketio import SocketIO, emit

from flask_cors import CORS

from Game.Components.GameState import GameState
from Game.Session.Words import generate_word_session
from Game.Views.GameStateView import game_state_str
from Game.Views.PlayerView import player_view_state, PlayerView
from Game.Components.Player import Player
from Game.Modules.EventEnum import GameEventState
from Game.Systems.GameStateSystem import add_player, add_deck_to_game, deal_to_players, generate_player
from Database.database import build_game_state_table, upsert_game_state_in_db, get_game_state_in_db, get_game_update_time_in_db

app = Flask(__name__)
CORS(app,resources={r"/*":{"origins":"*"}})
socketio = SocketIO(app,cors_allowed_origins="*")
# socketio = SocketIO(app)

build_game_state_table()

MOCK_REDIS_CACHE: Dict[str, GameState] = dict()
SITE_URL = "http://127.0.0.1:5000"

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


@app.route("/poll/<game_code>")
def poll_session(game_code: str):
    # server side event
    def get_is_updated():
        hash_time = ''
        while True:
            # need to replace this with gevent.sleep
            time.sleep(1)
            timestamp = get_game_update_time_in_db(game_code)
            temp_hash_time = hash_timestamp(timestamp)
            if temp_hash_time != hash_time:
                hash_time = temp_hash_time
                yield f'data: {hash_time} \n\n'
    
    return Response(get_is_updated(), mimetype='text/event-stream')


def hash_timestamp(timestamp):
    sha = hashlib.sha1(timestamp)
    return sha.hexdigest()


def update_redis_cache(game_state: GameState):
    game_code = game_state.game_code.lower()
    upsert_game_state_in_db(game_code, game_state.dict(), True)


def get_redis_cache(game_code) -> GameState:
    output = get_game_state_in_db(game_code.lower())
    print(output)
    return GameState(**output)


if __name__ == "__main__":
    socketio.run(app)
