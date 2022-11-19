from uuid import uuid4
from flask import Flask

from Game.Components.GameState import GameState
from Game.Views.GameStateView import game_state_str
from Game.Views.PlayerView import player_view_state_str
from Game.Components.Player import Player
from Game.Systems.GameStateSystem import add_player, add_deck_to_game, deal_to_players



app = Flask(__name__)

@app.route("/")
def hello_world():
    gs = GameState()
    return "<p>Finding Friends Backend</p>"


@app.route("/create")
def create_game():
    gs = GameState()
    return f'<p>{gs}</p>'


@app.route("/join")
def join_game():
    gs = GameState()
    return f'<p>Join Game</p>'


@app.route("/game")
def game_session():
    return f'<p>Game Session</p>'

