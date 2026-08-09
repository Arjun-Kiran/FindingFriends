import { useEffect, useState } from 'react';
import { NON_TRUMP_SUITS, RANK_OPTIONS, SUIT_SYMBOLS } from '../../../constants/cards';
import { SOCKET_EVENTS } from '../../../api/events';

const DEFAULT_CALL = { suit: 'CLUB', rank: 'ACE', order: 1 };

const FriendCalling = ({ view, emit }) => {
    const count = view.num_friends_to_call || 0;
    const [callingCards, setCallingCards] = useState([]);

    useEffect(() => {
        setCallingCards(Array.from({ length: count }, () => ({ ...DEFAULT_CALL })));
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

    // Called cards must not be trumps.
    const suitOptions = NON_TRUMP_SUITS.filter(suit => suit !== trumpSuit);
    const rankOptions = RANK_OPTIONS.filter(rank => rank !== trumpRank);

    const update = (index, field, value) => {
        setCallingCards(previous => previous.map(
            (call, i) => (i === index ? { ...call, [field]: value } : call)
        ));
    };

    return (
        <div className="info-panel action-blue">
            <h4>Call {count} Friend Card{count > 1 ? 's' : ''}</h4>
            <p>Specify which cards will reveal your secret partners. Called cards must not be trumps.</p>

            {callingCards.map((call, idx) => (
                <div key={idx} className="friend-call-row">
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

            <button
                className="btn btn-secondary"
                onClick={() => emit(SOCKET_EVENTS.CALL_FRIENDS, { calling_cards: callingCards })}
            >
                Confirm Friend Cards
            </button>
        </div>
    );
};

export default FriendCalling;
