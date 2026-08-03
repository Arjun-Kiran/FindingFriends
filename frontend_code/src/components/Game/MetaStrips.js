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

/* Card points belong to a team, so teammates share one total — but a team total
 * would give away who is on which side. While friends are still hidden, points
 * are shown per player; once everyone has revealed themselves by playing a
 * called card, the display switches to the shared team totals. */
export const ScoresBar = ({ view }) => {
    if (view.game_event_state !== PHASE.ROUND_STARTED) return null;

    if (!view.all_friends_found) {
        const scores = view.players_round_score || {};
        return (
            <div className="scores-bar">
                {(view.player_list || []).map(player => (
                    <span key={player.uuid}>
                        {player.name}: {scores[player.uuid] || 0} pts
                    </span>
                ))}
            </div>
        );
    }

    return (
        <div className="scores-bar">
            <span className="team-score is-mine">
                Your team ({view.on_alpha_team ? 'Alpha Team' : 'Defenders'}): {view.my_team_points || 0} pts
            </span>
            <span className="team-score">Alpha Team: {view.alpha_team_points || 0} pts</span>
            <span className="team-score">Defenders: {view.defender_team_points || 0} pts</span>
        </div>
    );
};
