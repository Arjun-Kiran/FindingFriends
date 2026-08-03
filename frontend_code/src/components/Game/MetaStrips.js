import { SUIT_SYMBOLS, ordinal } from '../../constants/cards';
import { PHASE } from '../../constants/phases';

const nameOf = (players, uuid) => {
    const player = players.find(p => p.uuid === uuid);
    return player ? player.name : uuid;
};

/** The friend cards the alpha called, shown once the calling phase is over. */
export const CalledCardsStrip = ({ view }) => {
    const called = view.friend_calling_cards || [];
    if (called.length === 0 || view.game_event_state === PHASE.CALL_FRIENDS) return null;

    return (
        <div className="meta-strip">
            <strong>Called Cards:</strong>{' '}
            {called.map((cc, idx) => (
                <span key={idx}>
                    {idx > 0 && ', '}
                    {ordinal(cc.order)} {cc.rank} of {SUIT_SYMBOLS[cc.suit] || cc.suit}
                </span>
            ))}
        </div>
    );
};

export const RevealedFriendsStrip = ({ view }) => {
    const revealed = view.revealed_friends || [];
    if (revealed.length === 0) return null;

    const players = view.player_list || [];
    return (
        <div className="meta-strip is-friends">
            <strong>Revealed Friends:</strong>{' '}
            {revealed.map((uuid, idx) => (
                <span key={uuid}>{idx > 0 && ', '}{nameOf(players, uuid)}</span>
            ))}
        </div>
    );
};

export const ScoresBar = ({ view }) => {
    const scores = view.players_round_score || {};
    if (Object.keys(scores).length === 0 || view.game_event_state !== PHASE.ROUND_STARTED) return null;

    return (
        <div className="scores-bar">
            {(view.player_list || []).map(player => (
                <span key={player.uuid}>
                    {player.name}: {scores[player.uuid] || 0} pts
                </span>
            ))}
        </div>
    );
};
