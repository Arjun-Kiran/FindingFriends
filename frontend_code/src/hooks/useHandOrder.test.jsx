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

/* The server sends the hand in whatever order the engine holds it — laying it
   out is entirely the client's job now — so an untouched hand still has to
   arrive readable. */
test('a hand nobody has arranged arrives sorted', () => {
    const { result } = arrange(HAND, { ...AT_THE_TABLE, trump: EIGHTS_AND_DIAMONDS });

    expect(shown(result, HAND)).toEqual(['KING:SPADE', 'ACE:HEART', 'TWO:CLUB']);
});

test('and re-sorts itself when a card is dealt into it', () => {
    const { result, rerender } = arrange(HAND, { ...AT_THE_TABLE, trump: EIGHTS_AND_DIAMONDS });
    const afterKitty = [...HAND, c('ACE', 'SPADE')];

    rerender({ cards: afterKitty });

    expect(shown(result, afterKitty))
        .toEqual(['ACE:SPADE', 'KING:SPADE', 'ACE:HEART', 'TWO:CLUB']);
});

/* Once the player has said where they want a card, nothing may quietly tidy it
   somewhere else. */
test('but stops sorting itself the moment the player arranges it', () => {
    const { result, rerender } = arrange(HAND, { ...AT_THE_TABLE, trump: EIGHTS_AND_DIAMONDS });
    act(() => result.current.move(0, 3));

    const afterKitty = [...HAND, c('ACE', 'SPADE')];
    rerender({ cards: afterKitty });

    // The dealt card goes on the end, and the player's own order is untouched.
    expect(shown(result, afterKitty))
        .toEqual(['ACE:HEART', 'TWO:CLUB', 'KING:SPADE', 'ACE:SPADE']);
});

test('sorting lays out trumps first, then suits', () => {
    const { result } = arrange(HAND, { ...AT_THE_TABLE, trump: EIGHTS_AND_DIAMONDS });

    act(() => result.current.sort());

    expect(shown(result, HAND)).toEqual(['KING:SPADE', 'ACE:HEART', 'TWO:CLUB']);
});

test('a dragged card stays where it was put', () => {
    const { result } = arrange(HAND);

    act(() => result.current.move(2, 0));

    expect(shown(result, HAND)).toEqual(['TWO:CLUB', 'KING:SPADE', 'ACE:HEART']);
});

test('an arrangement the player made is what a reload sorts nothing over', () => {
    const first = arrange(HAND, { ...AT_THE_TABLE, trump: EIGHTS_AND_DIAMONDS });
    act(() => first.result.current.move(0, 3));
    first.unmount();

    const { result } = arrange(HAND, { ...AT_THE_TABLE, trump: EIGHTS_AND_DIAMONDS });

    expect(shown(result, HAND)).toEqual(['ACE:HEART', 'TWO:CLUB', 'KING:SPADE']);
});

/* The two reasons the arrangement is stored as cards rather than positions. */
describe('an arrangement outlives the hand it was made on', () => {
    test('playing a card leaves the rest where the player put them', () => {
        const { result, rerender } = arrange(HAND);
        act(() => result.current.move(2, 0));

        const afterPlaying = [c('TWO', 'CLUB'), c('KING', 'SPADE')];
        rerender({ cards: afterPlaying });

        expect(shown(result, afterPlaying)).toEqual(['TWO:CLUB', 'KING:SPADE']);
    });

    test('and so does a reload', () => {
        const first = arrange(HAND);
        act(() => first.result.current.move(2, 0));
        first.unmount();

        const { result } = arrange(HAND);

        expect(shown(result, HAND)).toEqual(['TWO:CLUB', 'KING:SPADE', 'ACE:HEART']);
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

        expect(shown(result, HAND)).toEqual(['KING:SPADE', 'ACE:HEART', 'TWO:CLUB']);
    });

    test('another player in the same game starts fresh', () => {
        const mine = arrange(HAND);
        act(() => mine.result.current.move(2, 0));
        mine.unmount();

        const { result } = arrange(HAND, { ...AT_THE_TABLE, playerUuid: 'uuid-bob' });

        expect(shown(result, HAND)).toEqual(['KING:SPADE', 'ACE:HEART', 'TWO:CLUB']);
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

        expect(shown(result, HAND)).toEqual(['KING:SPADE', 'ACE:HEART', 'TWO:CLUB']);
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

        expect(shown(result, HAND)).toEqual(['TWO:CLUB', 'KING:SPADE', 'ACE:HEART']);
        expect(localStorage.length).toBe(0);
    });
});
