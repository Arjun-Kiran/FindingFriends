import { useEffect, useState } from 'react';
import { NON_TRUMP_SUITS, RANK_OPTIONS, SUIT_SYMBOLS } from '../../../constants/cards';
import { SOCKET_EVENTS } from '../../../api/events';

const DEFAULT_CALL = { suit: 'CLUB', rank: 'ACE' };

/** How a row is written down for comparison — the whole identity of a card. */
const identityOf = (call) => `${call.suit}:${call.rank}:${call.order}`;

/* Which rows name a card some earlier row already named.
 *
 * The same card twice is one card doing two rules' work: the first play to
 * match it satisfies both at once, so the second friend can never be found.
 * The server refuses it; this is so the alpha sees which row is the problem
 * rather than a sentence about a card they have to go hunting for.
 */
const duplicateRows = (calls) => {
    const seen = new Set();
    return calls.map(call => {
        const identity = identityOf(call);
        const repeated = seen.has(identity);
        seen.add(identity);
        return repeated;
    });
};

const FriendCalling = ({ view, emit }) => {
    const count = view.num_friends_to_call || 0;
    const [callingCards, setCallingCards] = useState([]);

    /* Each row starts on a different copy — 1st, 2nd, 3rd — so the default is
     * a legal call. Starting them all on the 1st meant an alpha who simply
     * pressed Confirm named the same card twice. */
    useEffect(() => {
        setCallingCards(Array.from(
            { length: count },
            (_, index) => ({ ...DEFAULT_CALL, order: index + 1 }),
        ));
    }, [count]);

    const trumpSuit = view.declare_trump && view.declare_trump.suit;
    const trumpRank = view.declare_trump && view.declare_trump.rank;

    if (!view.is_alpha) {
        return (
            <div className="info-panel waiting">
                Trump: <strong>{SUIT_SYMBOLS[trumpSuit] || trumpSuit} {trumpRank}</strong>.
                {' '}Waiting for alpha to call friends...
            </div>
        );
    }

    /* Called cards must not be trumps — unless the table agreed otherwise in
     * the lobby. The server enforces the same rule either way; leaving trumps
     * out of the pickers when they are allowed would make the setting look
     * broken, since there would be no way to call one. */
    const trumpsAllowed = Boolean((view.settings || {}).trumps_can_be_called);
    const suitOptions = trumpsAllowed
        ? NON_TRUMP_SUITS
        : NON_TRUMP_SUITS.filter(suit => suit !== trumpSuit);
    const rankOptions = trumpsAllowed
        ? RANK_OPTIONS
        : RANK_OPTIONS.filter(rank => rank !== trumpRank);

    const repeated = duplicateRows(callingCards);
    const hasRepeat = repeated.some(Boolean);

    const update = (index, field, value) => {
        setCallingCards(previous => previous.map(
            (call, i) => (i === index ? { ...call, [field]: value } : call)
        ));
    };

    return (
        <div className="info-panel action-blue">
            <h4>Call {count} Friend Card{count > 1 ? 's' : ''}</h4>
            <p>
                Specify which cards will reveal your secret partners.
                {trumpsAllowed
                    ? ' This table allows trumps to be called.'
                    : ' Called cards must not be trumps.'}
            </p>

            {callingCards.map((call, idx) => (
                <div
                    key={idx}
                    className={`friend-call-row${repeated[idx] ? ' is-duplicate' : ''}`}
                >
                    <span className="friend-call-index">#{idx + 1}</span>
                    <select value={call.order} onChange={e => update(idx, 'order', parseInt(e.target.value, 10))}>
                        <option value={1}>1st</option>
                        <option value={2}>2nd</option>
                        <option value={3}>3rd</option>
                        <option value={4}>4th</option>
                    </select>
                    <select value={call.rank} onChange={e => update(idx, 'rank', e.target.value)}>
                        {rankOptions.map(rank => <option key={rank} value={rank}>{rank}</option>)}
                    </select>
                    <span>of</span>
                    <select value={call.suit} onChange={e => update(idx, 'suit', e.target.value)}>
                        {suitOptions.map(suit => (
                            <option key={suit} value={suit}>{SUIT_SYMBOLS[suit]} {suit}</option>
                        ))}
                    </select>
                </div>
            ))}

            {hasRepeat && (
                <p className="error-text">
                    Two of these name the same card. Each friend has to be found by a
                    different one — change the copy, or call another card.
                </p>
            )}

            <button
                className="btn btn-secondary"
                disabled={hasRepeat}
                onClick={() => emit(SOCKET_EVENTS.CALL_FRIENDS, { calling_cards: callingCards })}
            >
                Confirm Friend Cards
            </button>
        </div>
    );
};

export default FriendCalling;
