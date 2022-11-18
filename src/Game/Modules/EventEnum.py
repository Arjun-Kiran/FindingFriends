from pydantic import BaseModel
from enum import Enum, unique


@unique
class Event(Enum):
    PLAYER_JOINED = 'player-joined'
    GAME_STARTED = 'game-started'
    WAITING_ON_ALPHA_KITTY_SORT = 'waiting-on-alpha-kitty-sort'
    WAITING_ON_ALPHA_FRIEND_CARD_CHOICE = 'waiting-on-alpha-friend-card-choice'
    WAITING_ON_ALPHA_CHOOSE_TRUMP = 'waiting-on-alpha-choose-trump'
    ROUND_STARTED = 'round-started'
    ROUND_ENDED = 'round-ended'
    PLAYER_JUMPED = 'player-jumped'
    HAND_PLAY = 'hand-play'


class EventItem(BaseModel):
    event: Event
    message: str
    time_stamp: str

