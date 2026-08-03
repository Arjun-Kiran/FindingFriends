import { LEVEL_LABELS } from '../../../constants/cards';
import { SOCKET_EVENTS } from '../../../api/events';

const WINNER_TEXT = {
    trump_maker: { text: 'Trump makers win!', className: 'is-trump-maker' },
    defender: { text: 'Defenders win!', className: 'is-defender' },
    none: { text: 'Draw - no one advances.', className: 'is-draw' },
};

const RoundSummary = ({ view, emit }) => {
    const players = view.player_list || [];
    const levels = view.player_levels || {};
    const scores = view.players_round_score || {};
    const promoted = view.round_promoted_players || [];
    const outcome = WINNER_TEXT[view.round_winner_side];

    const nameOf = (uuid) => {
        const player = players.find(p => p.uuid === uuid);
        return player ? player.name : uuid;
    };

    return (
        <div className="result-card">
            <h3>Round Over!</h3>
            <p>{view.on_alpha_team ? 'You were on the Alpha team.' : 'You were on the Defender team.'}</p>
            <p>
                Defender points: <strong>{view.round_defender_points || 0}</strong>
                {' — '}
                {outcome && <span className={outcome.className}>{outcome.text}</span>}
            </p>

            {view.round_promotion_levels > 0 && (
                <p>
                    <strong>+{view.round_promotion_levels} level{view.round_promotion_levels > 1 ? 's' : ''}</strong> for:{' '}
                    {promoted.map((uuid, idx) => (
                        <span key={uuid}>{idx > 0 && ', '}{nameOf(uuid)}</span>
                    ))}
                </p>
            )}

            <h4>Player Levels</h4>
            <div className="level-chips">
                {players.map(player => (
                    <span
                        key={player.uuid}
                        className={`level-chip${promoted.includes(player.uuid) ? ' promoted' : ''}`}
                    >
                        {player.name}: Lv {LEVEL_LABELS[levels[player.uuid]] || levels[player.uuid] || '?'}
                        {' '}({scores[player.uuid] || 0} pts)
                    </span>
                ))}
            </div>

            {view.hosting ? (
                <button className="btn btn-orange btn-spaced" onClick={() => emit(SOCKET_EVENTS.NEXT_ROUND)}>
                    Start Next Round
                </button>
            ) : (
                <p className="lobby-status">Waiting for the host to start the next round...</p>
            )}
        </div>
    );
};

export default RoundSummary;
