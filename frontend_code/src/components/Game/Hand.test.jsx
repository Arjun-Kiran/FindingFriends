import { beforeEach, describe, expect, test, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Hand from './Hand';
import { SUIT_SYMBOLS } from '../../constants/cards';

const c = (rank, suit) => ({ rank, suit });
const HAND = [c('TWO', 'CLUB'), c('ACE', 'HEART'), c('KING', 'SPADE')];

const noSelection = () => ({ selected: new Set(), toggle: vi.fn() });

const renderHand = (props = {}) => {
    const selection = props.selection || noSelection();
    const utils = render(<Hand cards={HAND} selection={selection} {...props} />);
    return { ...utils, selection };
};

/** The rendered cards, left to right. */
const shownCards = () =>
    [...document.querySelectorAll('.playing-card')].map(node => node.getAttribute('title'));

/* jsdom gives every element a zero-sized box, so "past the midpoint" would
   always be true. Placing the cards by hand is what makes a drop land in a
   predictable gap. */
const layOutCards = () => {
    document.querySelectorAll('.hand-card').forEach((node, position) => {
        node.getBoundingClientRect = () => ({
            left: position * 60, width: 60, right: position * 60 + 60, top: 0, bottom: 84, height: 84,
        });
    });
};

/* jsdom has no DragEvent, so fireEvent builds a plain Event and drops clientX
   with it — and clientX is the whole question here. A MouseEvent named
   'dragover' is what a browser actually delivers, and it carries the pointer. */
const dragOverAt = (node, clientX, dataTransfer) => {
    const event = new MouseEvent('dragover', { bubbles: true, cancelable: true, clientX });
    event.dataTransfer = dataTransfer;
    fireEvent(node, event);
};

const dragCard = (from, { onto, side }) => {
    const cards = [...document.querySelectorAll('.hand-card')];
    layOutCards();
    const dataTransfer = { setData: vi.fn(), getData: vi.fn(), effectAllowed: '', dropEffect: '' };

    fireEvent.dragStart(cards[from], { dataTransfer });
    const box = cards[onto].getBoundingClientRect();
    dragOverAt(cards[onto], side === 'left' ? box.left + 5 : box.right - 5, dataTransfer);
    fireEvent.drop(document.querySelector('.hand-cards'), { dataTransfer });
};

describe('reading the hand', () => {
    test('cards are drawn in the given order, not the order the server sent', () => {
        renderHand({ order: [2, 0, 1] });

        expect(shownCards()).toEqual([
            `K ${SUIT_SYMBOLS.SPADE}`, `2 ${SUIT_SYMBOLS.CLUB}`, `A ${SUIT_SYMBOLS.HEART}`,
        ]);
    });

    test('with no arrangement it falls back to the order the server sent', () => {
        renderHand();

        expect(shownCards()).toEqual([
            `2 ${SUIT_SYMBOLS.CLUB}`, `A ${SUIT_SYMBOLS.HEART}`, `K ${SUIT_SYMBOLS.SPADE}`,
        ]);
    });

    /* An arrangement that is one push behind the hand would otherwise index
       past the end and render blanks. */
    test('an arrangement that does not match the hand is ignored, not applied', () => {
        renderHand({ order: [5, 6] });

        expect(shownCards()).toHaveLength(HAND.length);
    });
});

/* The whole safety property of rearranging: a card is reported by its position
   in the SERVER's hand, because that is what every phase turns into a payload.
   If this slips, players play cards they did not click. */
describe('what a click reports', () => {
    test('the card\'s server index, not where it sits on screen', async () => {
        const selection = noSelection();
        renderHand({ order: [2, 0, 1], rules: {}, selection });

        // Leftmost card on screen is the king — index 2 in the server's hand.
        await userEvent.click(screen.getByTitle(`K ${SUIT_SYMBOLS.SPADE}`));

        expect(selection.toggle).toHaveBeenCalledWith(2, { max: undefined, single: undefined });
    });

    test('selection highlights follow the card, not the position', () => {
        const selection = { selected: new Set([2]), toggle: vi.fn() };
        renderHand({ order: [2, 0, 1], rules: {}, selection });

        expect(screen.getByTitle(`K ${SUIT_SYMBOLS.SPADE}`)).toHaveClass('is-selected');
        expect(screen.getByTitle(`2 ${SUIT_SYMBOLS.CLUB}`)).not.toHaveClass('is-selected');
    });

    test('a phase that does not take cards leaves the hand unclickable', () => {
        renderHand({ rules: null });

        expect(document.querySelector('.playing-card.is-clickable')).toBeNull();
    });
});

describe('dragging a card somewhere else', () => {
    let onMove;

    beforeEach(() => { onMove = vi.fn(); });

    test('dropping on the left of a card puts it before that card', () => {
        renderHand({ onMove });

        dragCard(2, { onto: 0, side: 'left' });

        expect(onMove).toHaveBeenCalledWith(2, 0);
    });

    test('dropping on the right of a card puts it after that card', () => {
        renderHand({ onMove });

        dragCard(0, { onto: 2, side: 'right' });

        expect(onMove).toHaveBeenCalledWith(0, 3);
    });

    test('the card being carried is marked, so the hand does not look frozen', () => {
        renderHand({ onMove });
        layOutCards();

        fireEvent.dragStart(document.querySelectorAll('.hand-card')[1], {
            dataTransfer: { setData: vi.fn(), effectAllowed: '' },
        });

        expect(document.querySelectorAll('.hand-card')[1]).toHaveClass('is-dragging');
    });

    test('a hand with nowhere to report a move is not draggable at all', () => {
        renderHand();

        expect(document.querySelector('.hand-card[draggable="true"]')).toBeNull();
    });
});

describe('the sort button', () => {
    test('asks for a sort without touching the cards itself', async () => {
        const onSort = vi.fn();
        renderHand({ onSort });

        await userEvent.click(screen.getByRole('button', { name: 'Sort' }));

        expect(onSort).toHaveBeenCalledOnce();
        expect(shownCards()).toHaveLength(HAND.length);
    });

    /* Nothing to sort, and the button would sit over an empty row for the
       whole of the trick-taking endgame. */
    test('is absent when there is nothing to arrange', () => {
        render(<Hand cards={[c('ACE', 'HEART')]} selection={noSelection()} onSort={vi.fn()} />);

        expect(screen.queryByRole('button', { name: 'Sort' })).not.toBeInTheDocument();
    });
});
