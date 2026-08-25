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
    # One player's play of one or more cards.
    HAND_PLAY = 'hand-play'
    TRICK_WON = 'trick-won'
    # The alpha's three set-up decisions.
    TRUMP_DECLARED = 'trump-declared'
    FRIENDS_CALLED = 'friends-called'
    KITTY_DISCARDED = 'kitty-discarded'
    # A player outed themselves as the alpha's friend by playing a called card.
    FRIEND_REVEALED = 'friend-revealed'


class EventItem(BaseModel):
    event: Event
    message: str
    time_stamp: str
    uuid: str
    # Who the event is about, when it is about somebody. Carried instead of
    # baking their avatar into the message so the UI can render the avatar as
    # an avatar — labelled, and the same glyph the players bar shows. Empty for
    # events that belong to the table rather than a player.
    player_uuid: str = ''


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

