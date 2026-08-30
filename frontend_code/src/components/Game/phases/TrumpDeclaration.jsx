import { useState } from 'react';
import {
    NON_TRUMP_SUITS, RANK_OPTIONS, SUIT_SYMBOLS, LEVEL_LABELS, RANK_LABELS,
    isCardAtLevel, isJokerSuit, rankNameForLevel,
} from '../../../constants/cards';
import { SOCKET_EVENTS } from '../../../api/events';

/** Has the table lifted the rule that trump is your own level? */
const freeChoice = (view) => Boolean((view.settings || {}).free_trump_choice);

/* Only the alpha picks a card, and only one matching their level.
 *
 * Under free choice the hand has nothing to say: trump need not be a card the
 * alpha holds at all, so it is named from pickers instead and the hand goes
 * inert rather than offering a choice that is no longer the one being made. */
export const handRules = (view) => {
    if (!view.is_alpha || freeChoice(view)) return null;
    return {
        single: true,
        selectable: (card) => isCardAtLevel(card, view.my_level),
        dim: (card) => !isCardAtLevel(card, view.my_level),
    };
};

/* Any suit, any rank — the whole point of the setting, so nothing here is
 * filtered by level or by what is in hand. */
const FreeTrumpPicker = ({ declare }) => {
    const [suit, setSuit] = useState(NON_TRUMP_SUITS[0]);
    const [rank, setRank] = useState(RANK_OPTIONS[0]);

    return (
        <>
            <p>This table lets you name any trump, whatever your level and whatever you hold.</p>
            <div className="friend-call-row">
                <select value={rank} onChange={e => setRank(e.target.value)}>
                    {RANK_OPTIONS.map(option => (
                        <option key={option} value={option}>{RANK_LABELS[option] || option}</option>
                    ))}
                </select>
                <span>of</span>
                <select value={suit} onChange={e => setSuit(e.target.value)}>
                    {NON_TRUMP_SUITS.map(option => (
                        <option key={option} value={option}>{SUIT_SYMBOLS[option]} {option}</option>
                    ))}
                </select>
            </div>
            <button className="btn btn-orange" onClick={() => declare(suit, rank)}>
                Declare {SUIT_SYMBOLS[suit]} {RANK_LABELS[rank] || rank} as Trump
            </button>
        </>
    );
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

    if (freeChoice(view)) {
        return (
            <div className="info-panel action">
                <h4>Declare Trump Suit</h4>
                <FreeTrumpPicker declare={declare} />
            </div>
        );
    }

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
