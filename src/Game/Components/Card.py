from dataclasses import dataclass
from typing import List
from Game.Modules.CardConstants import Suit, Rank


SUIT_EMOJI = {Suit.HEART: '♥️',
                  Suit.CLUB: '♣️',
                  Suit.DIAMOND: '♦️',
                  Suit.SPADE: '♠️',
                  Suit.SMALL: 'S',
                  Suit.BIG: 'B'}

RANK_EMOJI = {Rank.ACE: 'A',
                  Rank.TWO: '2',
                  Rank.THREE: '3',
                  Rank.FOUR: '4',
                  Rank.FIVE: '5',
                  Rank.SIX:  '6',
                  Rank.SEVEN: '7',
                  Rank.EIGHT: '8',
                  Rank.NINE: '9',
                  Rank.TEN:  '10',
                  Rank.JACK: 'J',
                  Rank.QUEEN: 'Q',
                  Rank.KING: 'K',
                  Rank.JOKER: '🃏'}


@dataclass
class Card():
    suit: Suit
    rank: Rank


def card_str(card: Card) -> str:
    return '{rank}{suit}'.format(suit=SUIT_EMOJI[card.suit],
                                rank=RANK_EMOJI[card.rank])


def card_list_to_str_list(list_card: List[Card]) -> List[str]:
    return [card_str(c) for c in list_card]
