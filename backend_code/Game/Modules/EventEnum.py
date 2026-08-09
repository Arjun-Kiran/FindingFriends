from pydantic import BaseModel, field_validator
from enum import Enum, unique
from uuid import UUID


@unique
class Event(str, Enum):
    PLAYER_JOINED = 'player-joined'
    PLAYER_LEFT = 'player-left'
    # Mid-game connection loss. Distinct from PLAYER_LEFT: the seat is held and
    # the player is expected back.
    PLAYER_DISCONNECTED = 'player-disconnected'
    PLAYER_RECONNECTED = 'player-reconnected'
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
    uuid: str


    @field_validator('uuid')
    @classmethod
    def convert_uuid_to_str(cls, v) -> str:
        if isinstance(v, UUID):
            return str(v)
        UUID(v, version=4)
        return str(v)


@unique
class GameEventState(str, Enum):
    NOT_AVAILABLE = 'not-available'
    WAITING_FOR_PLAYERS_TO_JOIN = 'waiting-for-player-to-join'
    GAME_STARTED = 'game-started'
    GAME_ENDED = 'game-ended'
    WAITING_ON_ALPHA_KITTY_SORT = 'waiting-on-alpha-kitty-sort'
    WAITING_ON_ALPHA_FRIEND_CARD_CHOICE = 'waiting-on-alpha-friend-card-choice'
    WAITING_ON_ALPHA_CHOOSE_TRUMP = 'waiting-on-alpha-choose-trump'
    ROUND_STARTED = 'round-started'
    ROUND_ENDED = 'round-ended'

