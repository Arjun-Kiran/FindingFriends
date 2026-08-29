import { useMemo, useState } from 'react';
import Card from '../Card';

/* Which gap the pointer is nearest: before this card, or after it. Dropping is
 * onto the space between two cards rather than onto a card, so that a card can
 * be placed at either end of the hand and not only between two others. */
const gapUnderPointer = (event, position) => {
    const box = event.currentTarget.getBoundingClientRect();
    return event.clientX >= box.left + box.width / 2 ? position + 1 : position;
};

/* The player's hand.
 *
 * `rules` comes from whichever phase is active (see phases/index.js) and is the
 * only thing that decides whether a card can be clicked. A phase that doesn't
 * involve picking cards returns null and the hand is inert.
 *
 * `order` is display order, as indices into `cards`. Everything the player
 * clicks is reported back in terms of the index a card has in the SERVER's
 * hand, never its position on screen — selection and every phase's payload are
 * keyed on that, so rearranging the hand cannot change which card gets played.
 * Rearranging is presentation and nothing else. */
const Hand = ({ cards = [], rules, selection, order, onMove, onSort }) => {
    const [drag, setDrag] = useState(null);
    const positions = useMemo(
        () => (order && order.length === cards.length ? order : cards.map((_, index) => index)),
        [order, cards]
    );

    const draggable = Boolean(onMove);
    const startDrag = (event, position) => {
        // Firefox refuses to start a drag unless something is on the clipboard.
        event.dataTransfer.setData('text/plain', String(position));
        event.dataTransfer.effectAllowed = 'move';
        setDrag({ from: position, to: position });
    };

    const dragOver = (event, position) => {
        if (!drag) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        const to = gapUnderPointer(event, position);
        if (to !== drag.to) setDrag({ ...drag, to });
    };

    const drop = (event) => {
        if (!drag) return;
        event.preventDefault();
        onMove(drag.from, drag.to);
        setDrag(null);
    };

    return (
        <div className="hand-area">
            <div className="hand-header">
                <h4>Your Hand ({cards.length} cards)</h4>
                {onSort && cards.length > 1 && (
                    <button
                        type="button"
                        className="btn-sort-hand"
                        onClick={onSort}
                        title="Arrange trumps first, then by suit and rank"
                    >
                        Sort
                    </button>
                )}
            </div>
            <div className="hand-cards" onDragOver={event => drag && event.preventDefault()} onDrop={drop}>
                {positions.map((cardIndex, position) => {
                    const card = cards[cardIndex];
                    const selectable = rules ? (rules.selectable ? rules.selectable(card, cardIndex) : true) : false;
                    const dimmed = rules && rules.dim ? rules.dim(card, cardIndex) : false;
                    const onClick = selectable
                        ? () => selection.toggle(cardIndex, { max: rules.max, single: rules.single })
                        : undefined;

                    const marks = [
                        dimmed ? 'is-ineligible' : '',
                        drag && drag.from === position ? 'is-dragging' : '',
                        drag && drag.to === position ? 'is-drop-before' : '',
                        // Only the last card can show the trailing gap; every
                        // other one is somebody else's leading gap.
                        drag && drag.to === positions.length && position === positions.length - 1
                            ? 'is-drop-after' : '',
                    ].filter(Boolean).join(' ');

                    return (
                        <div
                            key={cardIndex}
                            className={`hand-card${marks ? ` ${marks}` : ''}`}
                            draggable={draggable}
                            onDragStart={draggable ? event => startDrag(event, position) : undefined}
                            onDragOver={draggable ? event => dragOver(event, position) : undefined}
                            onDragEnd={draggable ? () => setDrag(null) : undefined}
                        >
                            <Card card={card} selected={selection.selected.has(cardIndex)} onClick={onClick} />
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default Hand;
