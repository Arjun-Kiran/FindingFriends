import { describe, expect, test } from 'vitest';
import { cardKey, cardStrength, isTrump, moveWithin, reconcile, sortedOrder } from './handOrder';

const c = (rank, suit) => ({ rank, suit });
const EIGHTS_AND_DIAMONDS = { rank: 'EIGHT', suit: 'DIAMOND' };
const keysOf = (hand, order) => order.map(index => cardKey(hand[index]));

/* Arranging a hand is presentation, but it has to agree with the rules about
   what a trump is — a hand that files the 8♠ under spades when eights are
   trump is telling the player something false about what they hold. */
describe('what counts as a trump', () => {
    test('the trump suit, the trump rank in any suit, and both jokers', () => {
        expect(isTrump(EIGHTS_AND_DIAMONDS, c('TWO', 'DIAMOND'))).toBe(true);
        expect(isTrump(EIGHTS_AND_DIAMONDS, c('EIGHT', 'SPADE'))).toBe(true);
        expect(isTrump(EIGHTS_AND_DIAMONDS, c('JOKER', 'BIG'))).toBe(true);
        expect(isTrump(EIGHTS_AND_DIAMONDS, c('ACE', 'SPADE'))).toBe(false);
    });

    test('before trump is declared only the jokers are trumps', () => {
        const undeclared = { rank: null, suit: null };

        expect(isTrump(undeclared, c('JOKER', 'SMALL'))).toBe(true);
        expect(isTrump(undeclared, c('ACE', 'SPADE'))).toBe(false);
    });
});

/* The order inside the trump block is the order the cards actually beat each
   other in — see card_value() in the backend's DecisionSystem. */
test('trumps rank jokers, the trump card, the off-suit trump ranks, then the suit', () => {
    const descending = [
        c('JOKER', 'BIG'), c('JOKER', 'SMALL'), c('EIGHT', 'DIAMOND'),
        c('EIGHT', 'SPADE'), c('ACE', 'DIAMOND'), c('TWO', 'DIAMOND'),
    ].map(card => cardStrength(EIGHTS_AND_DIAMONDS, card));

    expect(descending).toEqual([...descending].sort((a, b) => b - a));
});

describe('sorting a hand', () => {
    test('trumps come first as one block, then each suit high to low', () => {
        const hand = [
            c('THREE', 'SPADE'), c('JOKER', 'BIG'), c('ACE', 'SPADE'),
            c('EIGHT', 'CLUB'), c('KING', 'DIAMOND'),
        ];

        expect(keysOf(hand, sortedOrder(hand, EIGHTS_AND_DIAMONDS))).toEqual([
            'JOKER:BIG',      // trumps, in the order they beat each other:
            'EIGHT:CLUB',     // the trump RANK outranks the trump SUIT, so the
            'KING:DIAMOND',   // 8 of clubs files above the king of diamonds
            'ACE:SPADE',      // then the remaining suits
            'THREE:SPADE',
        ]);
    });

    test('the trump rank in the other suits sits together, not scattered', () => {
        const hand = [c('EIGHT', 'SPADE'), c('EIGHT', 'CLUB'), c('EIGHT', 'HEART')];
        const sorted = keysOf(hand, sortedOrder(hand, EIGHTS_AND_DIAMONDS));

        // Equally strong cards, so the tie is broken to keep suits adjacent.
        expect(sorted).toEqual(['EIGHT:SPADE', 'EIGHT:HEART', 'EIGHT:CLUB']);
    });

    test('two red suits never end up next to each other', () => {
        const hand = [
            c('ACE', 'HEART'), c('ACE', 'DIAMOND'), c('ACE', 'CLUB'), c('ACE', 'SPADE'),
        ];

        expect(keysOf(hand, sortedOrder(hand, null)))
            .toEqual(['ACE:SPADE', 'ACE:HEART', 'ACE:CLUB', 'ACE:DIAMOND']);
    });

    test('an undeclared trump still sorts by suit and rank', () => {
        const hand = [c('TWO', 'HEART'), c('ACE', 'HEART')];

        expect(keysOf(hand, sortedOrder(hand, { rank: null, suit: null })))
            .toEqual(['ACE:HEART', 'TWO:HEART']);
    });
});

/* An arrangement outlives the hand it was made on. These are the cases where
   the two disagree. */
describe('laying a saved arrangement back over a hand', () => {
    test('an empty arrangement leaves the hand in the order it was dealt', () => {
        const hand = [c('TWO', 'CLUB'), c('ACE', 'SPADE')];

        expect(reconcile([], hand)).toEqual([0, 1]);
    });

    test('cards that were played drop out and the gap closes', () => {
        const arranged = ['ACE:SPADE', 'KING:SPADE', 'TWO:CLUB'];
        const afterPlaying = [c('ACE', 'SPADE'), c('TWO', 'CLUB')];

        expect(keysOf(afterPlaying, reconcile(arranged, afterPlaying)))
            .toEqual(['ACE:SPADE', 'TWO:CLUB']);
    });

    test('cards the arrangement never saw go on the end, where they are visible', () => {
        const arranged = ['ACE:SPADE'];
        const afterKitty = [c('ACE', 'SPADE'), c('TWO', 'CLUB'), c('THREE', 'CLUB')];

        expect(keysOf(afterKitty, reconcile(arranged, afterKitty)))
            .toEqual(['ACE:SPADE', 'TWO:CLUB', 'THREE:CLUB']);
    });

    /* Two decks, so a hand can hold the same card twice and neither copy has
       an identity of its own. Both must still be placed exactly once. */
    test('a duplicated card is placed once per copy held', () => {
        const arranged = ['ACE:SPADE', 'TWO:CLUB', 'ACE:SPADE'];
        const hand = [c('ACE', 'SPADE'), c('ACE', 'SPADE'), c('TWO', 'CLUB')];

        expect(reconcile(arranged, hand).sort()).toEqual([0, 1, 2]);
    });

    test('one copy of a pair leaving still leaves the other in place', () => {
        const arranged = ['ACE:SPADE', 'TWO:CLUB', 'ACE:SPADE'];
        const hand = [c('ACE', 'SPADE'), c('TWO', 'CLUB')];

        expect(keysOf(hand, reconcile(arranged, hand))).toEqual(['ACE:SPADE', 'TWO:CLUB']);
    });

    test('an arrangement from a hand that is entirely gone is simply ignored', () => {
        const hand = [c('THREE', 'HEART')];

        expect(reconcile(['ACE:SPADE', 'KING:SPADE'], hand)).toEqual([0]);
    });
});

/* `to` is a gap between cards, running 0..length, not a card index — that is
   what lets a card be dropped at either end of the hand. */
describe('moving one card', () => {
    const order = [0, 1, 2, 3];

    test('rightwards, into a later gap', () => {
        expect(moveWithin(order, 0, 3)).toEqual([1, 2, 0, 3]);
    });

    test('leftwards, into an earlier gap', () => {
        expect(moveWithin(order, 3, 1)).toEqual([0, 3, 1, 2]);
    });

    test('to the very end', () => {
        expect(moveWithin(order, 0, 4)).toEqual([1, 2, 3, 0]);
    });

    test('to the very front', () => {
        expect(moveWithin(order, 2, 0)).toEqual([2, 0, 1, 3]);
    });

    test('dropped back into its own gap, which is not an off-by-one', () => {
        expect(moveWithin(order, 1, 1)).toEqual(order);
        expect(moveWithin(order, 1, 2)).toEqual(order);
    });

    test('a position that is not in the hand changes nothing', () => {
        expect(moveWithin(order, 9, 0)).toEqual(order);
    });
});
