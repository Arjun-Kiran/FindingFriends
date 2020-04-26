from enum import Enum, unique


@unique
class GameType(Enum):
    NO_GAME = 0
    SPADES = 1
    FINDING_FRIENDS = 2
