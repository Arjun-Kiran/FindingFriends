import { LEVEL_LABELS } from '../../../constants/cards';
import { SOCKET_EVENTS } from '../../../api/events';
import { Avatar, Icon } from '../../Emoji';
import { RESULT_EMOJI, TEAM_EMOJI } from '../../../constants/emoji';

const WINNER_TEXT = {
    trump_maker: { text: 'Alpha Team wins!', className: 'is-trump-maker', emoji: RESULT_EMOJI.WINNER },
    defender: { text: 'Defenders win!', className: 'is-defender', emoji: RESULT_EMOJI.WINNER },
    none: { text: 'Draw - no one advances.', className: 'is-draw', emoji: RESULT_EMOJI.DRAW },
};

const RoundSummary = ({ view, emit }) => {
    const players = view.player_list || [];
    const levels = view.player_levels || {};
    const scores = view.players_round_score || {};
    const promoted = view.round_promoted_players || [];
    const outcome = WINNER_TEXT[view.round_winner_side];

    const findPlayer = (uuid) => players.find(p => p.uuid === uuid);
    const nameOf = (uuid) => {
        const player = findPlayer(uuid);
        return player ? player.name : uuid;
    };

    return (
        <div className="result-card">
            <h3>Round Over!</h3>
            <p>{view.on_alpha_team ? 'You were on the Alpha team.' : 'You were on the Defender team.'}</p>
            <p>
                Defender points: <strong>{view.round_defender_points || 0}</strong>
                {' — '}
                {outcome && (
                    <span className={outcome.className}>
                        <Icon emoji={outcome.emoji} label={outcome.text} />{outcome.text}
                    </span>
                )}
            </p>

            {view.round_promotion_levels > 0 && (
                <p>
                    <Icon emoji={RESULT_EMOJI.PROMOTION} label="Level up" />
                    <strong>+{view.round_promotion_levels} level{view.round_promotion_levels > 1 ? 's' : ''}</strong> for:{' '}
                    {promoted.map((uuid, idx) => (
                        <span key={uuid}>
                            {idx > 0 && ', '}
                            <Avatar player={findPlayer(uuid)} />{' '}{nameOf(uuid)}
                        </span>
                    ))}
                </p>
            )}

            <h4>Team Points</h4>
            <div className="team-totals">
                <span className="team-score">
                    <Icon emoji={TEAM_EMOJI.ALPHA} label="Alpha team" />
                    <span className="score-text">Alpha Team: {view.alpha_team_points || 0} pts</span>
                </span>
                <span className="team-score">
                    <Icon emoji={TEAM_EMOJI.DEFENDER} label="Defenders" />
                    <span className="score-text">Defenders: {view.defender_team_points || 0} pts</span>
                </span>
            </div>

            <h4>Player Levels</h4>
            <div className="level-chips">
                {players.map(player => (
                    <span
                        key={player.uuid}
                        className={`level-chip${promoted.includes(player.uuid) ? ' promoted' : ''}`}
                    >
                        <Avatar player={player} />{' '}{player.name}: Lv{' '}
                        {LEVEL_LABELS[levels[player.uuid]] || levels[player.uuid] || '?'}
                        {promoted.includes(player.uuid) && (
                            <Icon emoji={RESULT_EMOJI.PROMOTION} label="Promoted" />
                        )}
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
