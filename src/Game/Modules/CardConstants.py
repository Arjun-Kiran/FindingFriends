from enum import Enum, unique

@unique
class Suit(Enum):
    NONE = 0x00
    CLUB = 0x10
    SPADE = 0x20
    HEART = 0x30
    DIAMOND = 0x40
    TRUMP = 0x50
    SMALL = 0xe0
    BIG = 0xf0



@unique
class Rank(Enum):
    TWO = 0x01
    THREE = 0x02
    FOUR = 0x03
    FIVE = 0x04
    SIX = 0x05
    SEVEN = 0x06
    EIGHT = 0x07
    NINE = 0x08
    TEN = 0x09
    JACK = 0x0a
    QUEEN = 0x0b
    KING = 0x0c
    ACE = 0x0d
    TRUMP = 0x0e
    JOKER = 0x0f


# Suits
CLUB = 'CLUB'
SPADE = 'SPADE'
HEART = 'HEART'
DIAMOND = 'DIAMOND'
BIG = 'BIG'
SMALL = 'SMALL'
CARDSUITS = [Suit.CLUB, Suit.SPADE, Suit.HEART, Suit.DIAMOND]
JOKERSUITS = [Suit.SMALL, Suit.BIG]

# Numbers
TWO = 'TWO'
THREE = 'THREE'
FOUR = 'FOUR'
FIVE = 'FIVE'
SIX = 'SIX'
SEVEN = 'SEVEN'
EIGHT = 'EIGHT'
NINE = 'NINE'
TEN = 'TEN'
JACK = 'JACK'
QUEEN = 'QUEEN'
KING = 'KING'
ACE = 'ACE'
JOKER = 'JOKER'
NONJOKERNUMBERS = [Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX, Rank.SEVEN, Rank.EIGHT, Rank.NINE, Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING, Rank.ACE]
NUMBERS = NONJOKERNUMBERS + [Rank.JOKER]
