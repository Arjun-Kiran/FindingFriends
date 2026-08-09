import { SOCKET_EVENTS } from '../../../api/events';

/* The alpha discards exactly kitty_size cards; everyone else watches. */
export const handRules = (view) => (view.is_alpha ? { max: view.kitty_size || 0 } : null);

const KittyExchange = ({ view, emit, selection }) => {
    if (!view.is_alpha) {
        return <div className="info-panel waiting">Waiting for alpha to exchange kitty cards...</div>;
    }

    const kittySize = view.kitty_size || 0;
    const hand = view.player_hand || [];
    const ready = selection.count === kittySize;

    const confirm = () => emit(SOCKET_EVENTS.KITTY_EXCHANGE, {
        discarded_cards: selection.indices.map(idx => ({ suit: hand[idx].suit, rank: hand[idx].rank })),
    });

    return (
        <div className="info-panel action">
            <h4>Kitty Exchange</h4>
            <p>The kitty ({kittySize} cards) has been added to your hand. Select {kittySize} cards to discard face-down.</p>
            <p className="selection-count">Selected: {selection.count} / {kittySize}</p>
            {ready && <button className="btn btn-primary" onClick={confirm}>Confirm Discard</button>}
        </div>
    );
};

export default KittyExchange;
