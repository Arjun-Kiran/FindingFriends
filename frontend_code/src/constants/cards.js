/* Single source of truth for card presentation.
 *
 * The backend speaks two different dialects for the same concept, and keeping
 * them straight is the whole reason this file exists:
 *
 *   - a CARD's rank arrives as an enum NAME   -> card.rank === 'ACE'
 *   - a PLAYER's level arrives as an enum VALUE -> my_level === 13
 *
 * Never compare the two directly. Use isCardAtLevel() / rankNameForLevel().
 */

// [enum name, enum value, display label] — values mirror backend Rank in
// Game/Modules/CardConstants.py.
const RANKS = [
    ['TWO', 1, '2'],
    ['THREE', 2, '3'],
    ['FOUR', 3, '4'],
    ['FIVE', 4, '5'],
    ['SIX', 5, '6'],
    ['SEVEN', 6, '7'],
    ['EIGHT', 7, '8'],
    ['NINE', 8, '9'],
    ['TEN', 9, '10'],
    ['JACK', 10, 'J'],
    ['QUEEN', 11, 'Q'],
    ['KING', 12, 'K'],
    ['ACE', 13, 'A'],
    ['TRUMP', 14, ''],
    ['JOKER', 15, ''],
];

/** Enum name -> enum value. 'ACE' -> 13 */
export const RANK_VALUES = Object.fromEntries(RANKS.map(([name, value]) => [name, value]));

/** Enum name -> display label. 'ACE' -> 'A' */
export const RANK_LABELS = Object.fromEntries(RANKS.map(([name, , label]) => [name, label]));

/** Enum value -> display label. 13 -> 'A'. Use for player levels. */
export const LEVEL_LABELS = Object.fromEntries(RANKS.map(([, value, label]) => [value, label]));

/** Enum value -> enum name. 13 -> 'ACE' */
export const RANK_NAME_BY_VALUE = Object.fromEntries(RANKS.map(([name, value]) => [value, name]));

/** Ranks offered when calling friend cards, high to low. */
export const RANK_OPTIONS = [
    'ACE', 'KING', 'QUEEN', 'JACK', 'TEN',
    'NINE', 'EIGHT', 'SEVEN', 'SIX', 'FIVE',
    'FOUR', 'THREE', 'TWO',
];

export const SUIT_SYMBOLS = {
    HEART: '♥',
    DIAMOND: '♦',
    CLUB: '♣',
    SPADE: '♠',
    SMALL: 'Jk',
    BIG: 'JK',
};

export const SUIT_COLORS = {
    HEART: '#c0392b',
    DIAMOND: '#c0392b',
    CLUB: '#2c3e50',
    SPADE: '#2c3e50',
    SMALL: '#2c3e50',
    BIG: '#c0392b',
};

/** The four real suits. Jokers (SMALL/BIG) are deliberately excluded. */
export const NON_TRUMP_SUITS = ['HEART', 'DIAMOND', 'CLUB', 'SPADE'];

export const JOKER_SUITS = ['SMALL', 'BIG'];

export const isJokerSuit = (suit) => JOKER_SUITS.includes(suit);

/** Does this card match the player's current level? Bridges name vs. value. */
export const isCardAtLevel = (card, level) => RANK_VALUES[card.rank] === level;

/** The rank NAME for a level value, for sending back to the server. */
export const rankNameForLevel = (level) => RANK_NAME_BY_VALUE[level];

/** '1st', '2nd', '3rd', '4th'... for friend-call ordering. */
export const ordinal = (n) => {
    if (n === 1) return '1st';
    if (n === 2) return '2nd';
    if (n === 3) return '3rd';
    return `${n}th`;
};
