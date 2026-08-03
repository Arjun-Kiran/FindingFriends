import {
    NON_TRUMP_SUITS, SUIT_SYMBOLS, LEVEL_LABELS,
    isCardAtLevel, isJokerSuit, rankNameForLevel,
} from '../../../constants/cards';
import { SOCKET_EVENTS } from '../../../api/events';

/* Only the alpha picks a card, and only one matching their level. */
export const handRules = (view) => {
    if (!view.is_alpha) return null;
    return {
        single: true,
        selectable: (card) => isCardAtLevel(card, view.my_level),
        dim: (card) => !isCardAtLevel(card, view.my_level),
    };
};

const TrumpDeclaration = ({ view, emit, selection }) => {
    if (!view.is_alpha) {
        return <div className="info-panel waiting">Waiting for the alpha player to declare trump...</div>;
    }

    const hand = view.player_hand || [];
    const eligibleSuits = new Set(
        hand.filter(card => isCardAtLevel(card, view.my_level) && !isJokerSuit(card.suit))
            .map(card => card.suit)
    );

    const selectedCard = hand[selection.indices[0]];
    const declare = (suit, rank) => emit(SOCKET_EVENTS.DECLARE_TRUMP, { suit, rank });

    return (
        <div className="info-panel action">
            <h4>Declare Trump Suit</h4>
            <p>
                Your level is <strong>{LEVEL_LABELS[view.my_level] || view.my_level}</strong>.
                {' '}Click a matching card below to select a trump suit, then confirm.
            </p>

            {eligibleSuits.size === 0 && (
                <>
                    <p className="error-text">You have no cards matching your level. Pick any suit:</p>
                    <div className="suit-picker">
                        {NON_TRUMP_SUITS.map(suit => (
                            <button
                                key={suit}
                                className="suit-btn"
                                onClick={() => declare(suit, rankNameForLevel(view.my_level))}
                            >
                                {SUIT_SYMBOLS[suit]}
                            </button>
                        ))}
                    </div>
                </>
            )}

            {selectedCard && (
                <button className="btn btn-orange" onClick={() => declare(selectedCard.suit, selectedCard.rank)}>
                    Declare {SUIT_SYMBOLS[selectedCard.suit] || ''} as Trump
                </button>
            )}
        </div>
    );
};

export default TrumpDeclaration;
