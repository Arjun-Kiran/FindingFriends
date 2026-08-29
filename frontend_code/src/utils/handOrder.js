/* How the cards in your hand are arranged on screen.
 *
 * Display only — none of this decides what may be played. The server owns the
 * rules; this file owns the order they sit in.
 *
 * The one thing to understand before changing anything here: a card has no id.
 * The game is played with two decks, so a hand can hold two cards that are
 * identical in every respect, and the only handle on a particular card is its
 * position in the server's `player_hand` array. So an arrangement is stored two
 * ways, on purpose:
 *
 *   - as INDICES into the current hand, which is what the UI renders and what
 *     card selection is keyed on (see useCardSelection)
 *   - as KEYS ('ACE:HEART'), which is what survives a hand changing underneath
 *     it or a page reload, because indices mean nothing once the hand moves
 *
 * reconcile() is the bridge between the two.
 */

import { RANK_VALUES } from '../constants/cards';

/* Non-trump suits, in the order they sit on screen. Alternating colours so two
 * red suits never end up adjacent — the whole point of sorting a hand is being
 * able to see where one suit stops. */
export const SUIT_DISPLAY_ORDER = ['SPADE', 'HEART', 'CLUB', 'DIAMOND'];

/** How a card is written down so it can be found again in a different hand. */
export const cardKey = (card) => `${card.rank}:${card.suit}`;

/* Mirrors is_trump() in backend DecisionSystem.py. Duplicated rather than
 * fetched because it only ever decides where a card is drawn, and a hand that
 * re-sorted itself on a round trip would be worse than one that is briefly
 * wrong. Trump is null until it is declared, and then nothing is trump but the
 * jokers — which is correct, not a special case. */
export const isTrump = (trump, card) => {
    if (card.rank === 'JOKER') return true;
    const { suit = null, rank = null } = trump || {};
    return (suit !== null && card.suit === suit) || (rank !== null && card.rank === rank);
};

/* Mirrors card_value() in backend DecisionSystem.py: the trump suit runs
 * jokers, the trump card itself, the trump rank in the other suits, then the
 * trump suit high to low. Sorting on the same numbers the server ranks tricks
 * by means the hand reads in the order the cards actually beat each other. */
export const cardStrength = (trump, card) => {
    const { suit = null, rank = null } = trump || {};
    if (card.rank === 'JOKER') return card.suit === 'BIG' ? 500 : 400;
    if (rank !== null && card.rank === rank) {
        return suit !== null && card.suit === suit ? 300 : 200;
    }
    if (suit !== null && card.suit === suit) return 100 + (RANK_VALUES[card.rank] || 0);
    return RANK_VALUES[card.rank] || 0;
};

/* Trumps first as one block, then each suit. Cards the sort does not recognise
 * fall to the end rather than landing somewhere arbitrary in the middle. */
const suitGroup = (trump, card) => {
    if (isTrump(trump, card)) return 0;
    const position = SUIT_DISPLAY_ORDER.indexOf(card.suit);
    return position === -1 ? SUIT_DISPLAY_ORDER.length + 1 : position + 1;
};

/** The hand's indices in trump → suit → rank order. */
export const sortedOrder = (hand = [], trump = null) =>
    hand.map((_, index) => index).sort((a, b) => {
        const [left, right] = [hand[a], hand[b]];
        return (suitGroup(trump, left) - suitGroup(trump, right))
            // The trump rank in three off-suits is three equally strong cards;
            // without this they scatter instead of sitting together.
            || (cardStrength(trump, right) - cardStrength(trump, left))
            || (SUIT_DISPLAY_ORDER.indexOf(left.suit) - SUIT_DISPLAY_ORDER.indexOf(right.suit))
            || (a - b);
    });

/* An arrangement, written as keys, laid back over a hand as indices.
 *
 * Cards that have left the hand drop out and the gap closes; cards that were
 * not in the arrangement — a fresh deal, the kitty landing — go on the end,
 * where they are visible rather than buried mid-hand. Duplicates are handed out
 * first-come, which is the best that can be done when the two are the same
 * card: whichever way they are paired, the player sees the same thing.
 */
export const reconcile = (keys = [], hand = []) => {
    const unclaimed = new Map();
    hand.forEach((card, index) => {
        const key = cardKey(card);
        if (!unclaimed.has(key)) unclaimed.set(key, []);
        unclaimed.get(key).push(index);
    });

    const order = [];
    keys.forEach(key => {
        const queue = unclaimed.get(key);
        if (queue && queue.length) order.push(queue.shift());
    });

    const placed = new Set(order);
    hand.forEach((_, index) => {
        if (!placed.has(index)) order.push(index);
    });
    return order;
};

/* Move the card at `from` so it sits before position `to`.
 *
 * `to` is a gap, not a card: it runs 0..length, where length means "past the
 * last card". Dropping a card back into its own gap is a no-op rather than an
 * off-by-one. */
export const moveWithin = (order = [], from, to) => {
    if (from < 0 || from >= order.length) return order;
    if (to === from || to === from + 1) return order;

    const next = [...order];
    const [moved] = next.splice(from, 1);
    const target = Math.max(0, Math.min(to > from ? to - 1 : to, next.length));
    next.splice(target, 0, moved);
    return next;
};
