from typing import List, Dict
from Game.Components.Card import Card
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

SUIT_STR = {
                Suit.HEART: 'HEART',
                  Suit.CLUB: 'CLUB',
                  Suit.DIAMOND: 'DIAMOND',
                  Suit.SPADE: 'SPADE',
                  Suit.SMALL: 'SMALL',
                  Suit.BIG: 'BIG'}

RANK_STR =  {
                Rank.ACE: 'ACE',
                  Rank.TWO: '2',
                  Rank.THREE: '3',
                  Rank.FOUR: '4',
                  Rank.FIVE: '5',
                  Rank.SIX:  '6',
                  Rank.SEVEN: '7',
                  Rank.EIGHT: '8',
                  Rank.NINE: '9',
                  Rank.TEN:  '10',
                  Rank.JACK: 'JOKER',
                  Rank.QUEEN: 'QUEEN',
                  Rank.KING: 'KING',
                  Rank.JOKER: 'JOKER'
            }

def card_emoji_str(card: Card) -> str:
    return '{rank}{suit}'.format(suit=SUIT_EMOJI[card.suit],
                                rank=RANK_EMOJI[card.rank])


def card_list_to_emoji_str_list(list_card: List[Card]) -> List[str]:
    return [card_emoji_str(c) for c in list_card]


def card_to_dict(card: Card) -> Dict:
    return {'rank': RANK_STR[card.rank],
            'suit': SUIT_STR[card.suit]}

def card_list_to_dict_list(list_card: List[Card]) -> List[Dict]:
    return [card_to_dict(card) for card in list_card]
