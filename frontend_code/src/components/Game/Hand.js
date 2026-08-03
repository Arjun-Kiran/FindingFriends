import Card from '../Card';

/* The player's hand.
 *
 * `rules` comes from whichever phase is active (see phases/index.js) and is the
 * only thing that decides whether a card can be clicked. A phase that doesn't
 * involve picking cards returns null and the hand is inert. */
const Hand = ({ cards = [], rules, selection }) => (
    <div className="hand-area">
        <h4>Your Hand ({cards.length} cards)</h4>
        <div className="hand-cards">
            {cards.map((card, idx) => {
                const selectable = rules ? (rules.selectable ? rules.selectable(card, idx) : true) : false;
                const dimmed = rules && rules.dim ? rules.dim(card, idx) : false;
                const onClick = selectable
                    ? () => selection.toggle(idx, { max: rules.max, single: rules.single })
                    : undefined;

                return (
                    <div key={idx} className={`hand-card${dimmed ? ' is-ineligible' : ''}`}>
                        <Card card={card} selected={selection.selected.has(idx)} onClick={onClick} />
                    </div>
                );
            })}
        </div>
    </div>
);

export default Hand;
