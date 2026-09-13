import { describe, expect, test, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import FriendCalling from './FriendCalling';

/* The alpha naming the cards that will out their friends.
 *
 * The rows start on a default, and the pickers leave the trump out — so the
 * default and the options have to agree. When they do not, a row holds a card
 * its own dropdown does not offer, and an alpha who never touches that row
 * sends a card they were never shown.
 */
const view = (overrides = {}) => ({
    is_alpha: true,
    num_friends_to_call: 2,
    declare_trump: { suit: 'CLUB', rank: 'TWO' },
    settings: {},
    ...overrides,
});

const confirm = () => fireEvent.click(screen.getByRole('button', { name: /Confirm/ }));

const renderPanel = (overrides) => {
    const emit = vi.fn();
    render(<FriendCalling view={view(overrides)} emit={emit} />);
    return emit;
};

const sent = (emit) => emit.mock.calls[0][1].calling_cards;

describe('friend calling', () => {
    test('never starts a row on the trump suit', () => {
        // Clubs are trump, so no row may begin life holding a club — the suit
        // picker does not offer one, and the alpha has no way to see it there.
        const emit = renderPanel();

        confirm();

        expect(sent(emit).map(call => call.suit)).not.toContain('CLUB');
    });

    test('never starts a row on the trump rank', () => {
        const emit = renderPanel({ declare_trump: { suit: 'HEART', rank: 'ACE' } });

        confirm();

        expect(sent(emit).map(call => call.rank)).not.toContain('ACE');
    });

    test('every row sends a card its own picker offered', () => {
        const emit = renderPanel();

        confirm();

        const suits = [...screen.getAllByRole('combobox')]
            .filter(box => box.value && ['HEART', 'DIAMOND', 'SPADE', 'CLUB'].includes(box.value))
            .map(box => box.value);
        expect(suits).not.toContain('CLUB');
        sent(emit).forEach(call => expect(call.suit).not.toBe('CLUB'));
    });

    test('a trump suit the alpha may legally call is still offered', () => {
        // With the house rule on, the trump is allowed and must be reachable.
        const emit = renderPanel({ settings: { trumps_can_be_called: true } });

        confirm();

        expect(sent(emit)).toHaveLength(2);
    });

    test('the rows still name different copies of the card', () => {
        const emit = renderPanel();

        confirm();

        expect(sent(emit).map(call => call.order)).toEqual([1, 2]);
    });
});
