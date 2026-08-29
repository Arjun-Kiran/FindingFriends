import { beforeEach, describe, expect, test } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useHandOrder } from './useHandOrder';
import { cardKey } from '../utils/handOrder';

const c = (rank, suit) => ({ rank, suit });
const AT_THE_TABLE = { gameCode: 'below-adopt-havoc', playerUuid: 'uuid-alice' };
const EIGHTS_AND_DIAMONDS = { rank: 'EIGHT', suit: 'DIAMOND' };

const HAND = [c('TWO', 'CLUB'), c('ACE', 'HEART'), c('KING', 'SPADE')];

/** What the player sees, left to right. */
const shown = (result, hand) => result.current.order.map(index => cardKey(hand[index]));

const arrange = (hand, options = AT_THE_TABLE) =>
    renderHook(({ cards }) => useHandOrder(cards, options), { initialProps: { cards: hand } });

beforeEach(() => localStorage.clear());

test('a hand nobody has arranged is left in the order it was dealt', () => {
    const { result } = arrange(HAND);

    expect(result.current.order).toEqual([0, 1, 2]);
});

test('sorting lays out trumps first, then suits', () => {
    const { result } = arrange(HAND, { ...AT_THE_TABLE, trump: EIGHTS_AND_DIAMONDS });

    act(() => result.current.sort());

    expect(shown(result, HAND)).toEqual(['KING:SPADE', 'ACE:HEART', 'TWO:CLUB']);
});

test('a dragged card stays where it was put', () => {
    const { result } = arrange(HAND);

    act(() => result.current.move(2, 0));

    expect(shown(result, HAND)).toEqual(['KING:SPADE', 'TWO:CLUB', 'ACE:HEART']);
});

/* The two reasons the arrangement is stored as cards rather than positions. */
describe('an arrangement outlives the hand it was made on', () => {
    test('playing a card leaves the rest where the player put them', () => {
        const { result, rerender } = arrange(HAND);
        act(() => result.current.move(2, 0));

        const afterPlaying = [c('TWO', 'CLUB'), c('KING', 'SPADE')];
        rerender({ cards: afterPlaying });

        expect(shown(result, afterPlaying)).toEqual(['KING:SPADE', 'TWO:CLUB']);
    });

    test('and so does a reload', () => {
        const first = arrange(HAND);
        act(() => first.result.current.move(2, 0));
        first.unmount();

        const { result } = arrange(HAND);

        expect(shown(result, HAND)).toEqual(['KING:SPADE', 'TWO:CLUB', 'ACE:HEART']);
    });
});

/* An arrangement is one player's view of one game. Leaking it across either
   would put a stranger's layout on your cards. */
describe('whose arrangement it is', () => {
    test('another game at the same table starts fresh', () => {
        const mine = arrange(HAND);
        act(() => mine.result.current.move(2, 0));
        mine.unmount();

        const { result } = arrange(HAND, { ...AT_THE_TABLE, gameCode: 'a-different-game' });

        expect(result.current.order).toEqual([0, 1, 2]);
    });

    test('another player in the same game starts fresh', () => {
        const mine = arrange(HAND);
        act(() => mine.result.current.move(2, 0));
        mine.unmount();

        const { result } = arrange(HAND, { ...AT_THE_TABLE, playerUuid: 'uuid-bob' });

        expect(result.current.order).toEqual([0, 1, 2]);
    });
});

/* Storage throws in a private window and when the quota is full. A hand in
   dealt order is still a perfectly playable hand, so none of that is fatal. */
describe('when the browser will not remember anything', () => {
    test('a corrupt saved arrangement is discarded rather than rendered', () => {
        localStorage.setItem(
            `findingFriendsHandOrder:${AT_THE_TABLE.gameCode}:${AT_THE_TABLE.playerUuid}`,
            'not json',
        );

        const { result } = arrange(HAND);

        expect(result.current.order).toEqual([0, 1, 2]);
    });

    test('a hand still sorts when storage refuses to save it', () => {
        const setItem = localStorage.setItem;
        localStorage.setItem = () => { throw new Error('QuotaExceededError'); };

        try {
            const { result } = arrange(HAND, { ...AT_THE_TABLE, trump: EIGHTS_AND_DIAMONDS });
            act(() => result.current.sort());

            expect(shown(result, HAND)).toEqual(['KING:SPADE', 'ACE:HEART', 'TWO:CLUB']);
        } finally {
            localStorage.setItem = setItem;
        }
    });

    test('no game to scope it to means the arrangement is simply not saved', () => {
        const { result } = arrange(HAND, { gameCode: '', playerUuid: '' });

        act(() => result.current.move(2, 0));

        expect(shown(result, HAND)).toEqual(['KING:SPADE', 'TWO:CLUB', 'ACE:HEART']);
        expect(localStorage.length).toBe(0);
    });
});
