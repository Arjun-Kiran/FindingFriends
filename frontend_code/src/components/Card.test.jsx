import { render, screen } from '@testing-library/react';
import Card from './Card';
import { JOKER_MARKS, SUIT_COLORS, SUIT_SYMBOLS } from '../constants/cards';

const renderCard = (rank, suit, props = {}) =>
    render(<Card card={{ rank, suit }} {...props} />);

test('a normal card shows its rank and suit', () => {
    renderCard('ACE', 'HEART');

    const card = screen.getByTitle(`A ${SUIT_SYMBOLS.HEART}`);
    expect(card).toHaveTextContent('A');
    expect(card).toHaveTextContent(SUIT_SYMBOLS.HEART);
});

/* The dedicated joker codepoints rendered as tofu on some platforms, so the
   jokers are written out instead. These pin that they stay text. */
describe('jokers', () => {
    test('both jokers read JK with a clown beside them', () => {
        renderCard('JOKER', 'BIG');

        expect(screen.getByTitle('Big Joker')).toHaveTextContent('JK🤡');
    });

    /* The big joker beats the small one, so which is which is a play decision.
       It used to be carried by colour alone — red against navy — which a
       red-green colourblind player cannot read at all. */
    test('the two jokers are told apart by shape, not colour', () => {
        const { unmount } = renderCard('JOKER', 'BIG');
        expect(screen.getByTitle('Big Joker')).toHaveTextContent('▲');
        unmount();

        renderCard('JOKER', 'SMALL');
        expect(screen.getByTitle('Small Joker')).toHaveTextContent('▼');
    });

    test('and the two marks are never the same glyph', () => {
        expect(JOKER_MARKS.BIG).not.toBe(JOKER_MARKS.SMALL);
    });

    /* Colour still runs alongside, for whoever can use it. */
    test('colour still backs the shape up', () => {
        renderCard('JOKER', 'BIG');

        expect(screen.getByTitle('Big Joker')).toHaveStyle({ color: SUIT_COLORS.BIG });
    });

    /* Colour is the only visual difference between them, so the name has to be
       available as text somewhere. */
    test('each joker is named rather than left to colour alone', () => {
        renderCard('JOKER', 'SMALL');

        expect(screen.getByTitle('Small Joker')).toBeInTheDocument();
        expect(screen.queryByTitle(/^ JK/)).not.toBeInTheDocument();
    });

    test('no joker renders a dedicated playing-card codepoint', () => {
        renderCard('JOKER', 'BIG');

        // U+1F0CF / U+1F0BF — the glyphs that did not render.
        expect(screen.getByTitle('Big Joker').textContent).not.toMatch(/[\u{1F0A0}-\u{1F0FF}]/u);
    });
});
