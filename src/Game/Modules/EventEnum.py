from enum import Enum, unique


@unique
class Event(Enum):
    PLAYER_JOINED = 'player_joined'
    GAME_STARTED = 'game_started'
    PLAYER_JUMPED = 'player_jumped'
    HAND_PLAY = 'hand_play'
