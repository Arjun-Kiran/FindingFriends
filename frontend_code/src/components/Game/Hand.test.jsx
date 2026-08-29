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

/* A card's face cannot show that it is a trump: with fives trump, the 5 of
   spades is a trump and the ace of spades is not, and both are printed the
   same way. The mark is the only thing saying so. */
describe('the trump mark', () => {
    const FIVES_AND_HEARTS = { rank: 'FIVE', suit: 'HEART' };

    test('sits above the trump-rank card and not its plain neighbour', () => {
        render(<Hand
            cards={[c('FIVE', 'SPADE'), c('ACE', 'SPADE')]}
            selection={noSelection()}
            trump={FIVES_AND_HEARTS}
        />);

        const marked = [...document.querySelectorAll('.hand-card')]
            .map(node => Boolean(node.querySelector('.trump-marker')));

        expect(marked).toEqual([true, false]);
    });

    test('covers the trump suit and both jokers as well', () => {
        render(<Hand
            cards={[c('TWO', 'HEART'), c('JOKER', 'SMALL'), c('KING', 'CLUB')]}
            selection={noSelection()}
            trump={FIVES_AND_HEARTS}
        />);

        expect(document.querySelectorAll('.trump-marker')).toHaveLength(2);
    });

    /* Before trump is declared the jokers are the only trumps there are — not
       a special case to suppress, just a very short list. */
    test('marks only the jokers before trump is declared', () => {
        render(<Hand
            cards={[c('JOKER', 'BIG'), c('ACE', 'SPADE')]}
            selection={noSelection()}
            trump={{ rank: null, suit: null }}
        />);

        expect(document.querySelectorAll('.trump-marker')).toHaveLength(1);
    });

    test('is announced rather than left as decoration', () => {
        render(<Hand cards={[c('TWO', 'HEART')]} selection={noSelection()} trump={FIVES_AND_HEARTS} />);

        expect(screen.getByLabelText('Trump card')).toBeInTheDocument();
    });
});

describe('highlighting what can be played', () => {
    const ringed = () =>
        [...document.querySelectorAll('.hand-card')].map(node => node.classList.contains('is-playable'));

    const turnOn = async () =>
        userEvent.click(screen.getByRole('button', { name: 'Highlight playable' }));

    beforeEach(() => localStorage.clear());

    test('is off until the player asks for it', () => {
        renderHand({ playable: [true, false, false] });

        expect(ringed()).toEqual([false, false, false]);
        expect(screen.getByRole('button', { name: 'Highlight playable' }))
            .toHaveAttribute('aria-pressed', 'false');
    });

    test('rings the cards the server says can be played', async () => {
        renderHand({ playable: [true, false, false] });

        await turnOn();

        expect(ringed()).toEqual([true, false, false]);
    });

    test('rings the card, not the position it was dragged to', async () => {
        renderHand({ playable: [true, false, false], order: [2, 1, 0] });

        await turnOn();

        // The 2♣ is the playable one, and it now sits last on screen.
        expect(ringed()).toEqual([false, false, true]);
    });

    /* Leading a trick makes every card legal. Ringing the whole hand green
       would be a lot of colour to say nothing at all. */
    test('draws nothing when every card is playable anyway', async () => {
        renderHand({ playable: [true, true, true] });

        await turnOn();

        expect(ringed()).toEqual([false, false, false]);
    });

    test('draws nothing when it is not your turn and the server sent no hint', async () => {
        renderHand({ playable: [] });

        await turnOn();

        expect(ringed()).toEqual([false, false, false]);
    });

    /* A hint one push out of step with the hand would ring the wrong cards,
       which is worse than ringing none. */
    test('ignores a hint that does not match the hand it arrived with', async () => {
        renderHand({ playable: [true, false] });

        await turnOn();

        expect(ringed()).toEqual([false, false, false]);
    });

    test('the choice outlives the page', async () => {
        const first = renderHand({ playable: [true, false, false] });
        await turnOn();
        first.unmount();

        renderHand({ playable: [true, false, false] });

        expect(ringed()).toEqual([true, false, false]);
    });
});
