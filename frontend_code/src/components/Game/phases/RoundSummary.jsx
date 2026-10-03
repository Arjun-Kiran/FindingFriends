import { LEVEL_LABELS } from '../../../constants/cards';
import { SOCKET_EVENTS } from '../../../api/events';
import { Avatar, Icon } from '../../Emoji';
import Card from '../../Card';
import { RESULT_EMOJI, TEAM_EMOJI } from '../../../constants/emoji';
import { TEAM_MARK, teamOf } from '../../../utils/teams';
import { useStoredToggle } from '../../../hooks/useStoredToggle';
import ScoringBreakdown from '../ScoringBreakdown';

const WINNER_TEXT = {
    trump_maker: { text: 'Alpha Team wins!', className: 'is-trump-maker', emoji: RESULT_EMOJI.WINNER },
    attacker: { text: 'Attackers win!', className: 'is-attacker', emoji: RESULT_EMOJI.WINNER },
    none: { text: 'Draw - no one advances.', className: 'is-draw', emoji: RESULT_EMOJI.DRAW },
};

const RoundSummary = ({ view, emit }) => {
    /* Folded away by default — most rounds you only want the result. Kept
     * across rounds and sessions, so a player working out how the ladder
     * behaves does not have to open it again every time. */
    const [showScoring, toggleScoring] = useStoredToggle('ff.showScoringBreakdown', false);
    const players = view.player_list || [];
    const levels = view.player_levels || {};
    const scores = view.players_round_score || {};
    const promoted = view.round_promoted_players || [];
    const outcome = WINNER_TEXT[view.round_winner_side];
    const kitty = view.kitty_cards || [];
    const kittyCardPoints = view.kitty_card_points || [];

    /* The round is over, so the sides are settled: the alpha and every friend
     * who revealed themselves, and everyone else attacked. A called card never
     * played found nobody — which is how the server scored it too. */
    const teamMark = (player) => TEAM_MARK[teamOf({
        playerUuid: player.uuid,
        alphaUuid: view.alpha_uuid,
        revealedFriends: view.revealed_friends || [],
        allFriendsFound: true,
    })];

    const findPlayer = (uuid) => players.find(p => p.uuid === uuid);
    const host = findPlayer(view.host_uuid);
    const nameOf = (uuid) => {
        const player = findPlayer(uuid);
        return player ? player.name : uuid;
    };

    /* Where the kitty's points went, in a sentence. Every number comes from
     * the server, which scored the round with them — nothing is summed here. */
    const kittyOutcome = () => {
        const points = view.kitty_points || 0;
        const taker = view.last_trick_winner_uuid;
        if (!view.kitty_counted) {
            return 'The round was ended as a draw, so the kitty was not counted.';
        }
        if (points === 0) {
            return 'There were no points in the kitty.';
        }
        const who = (
            <>
                <Avatar player={findPlayer(taker)} />{' '}<strong>{nameOf(taker)}</strong>
            </>
        );
        if (view.kitty_points_awarded > 0) {
            return (
                <>
                    {who} attacked and took the last trick, so the kitty's {points} points
                    count double: <strong>+{view.kitty_points_awarded} to the Attackers</strong>.
                </>
            );
        }
        return (
            <>
                {who} was on the Alpha Team and took the last trick, so the kitty's{' '}
                {points} points <strong>go to nobody</strong>.
            </>
        );
    };

    return (
        <div className="result-card">
            <h3>Round Over!</h3>
            {!view.is_watcher && (
                <p>{view.on_alpha_team ? 'You were on the Alpha team.' : 'You were on the Attacker team.'}</p>
            )}
            <p>
                Attacker points: <strong>{view.round_attacker_points || 0}</strong>
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

            {/* HR-11: the server works out who is next, so this can never name
              * someone the deal then passes over. Absent once the game is won. */}
            {view.next_alpha_uuid && (
                <p className="next-alpha">
                    Next alpha:{' '}
                    <Avatar player={findPlayer(view.next_alpha_uuid)} />{' '}
                    <strong>{nameOf(view.next_alpha_uuid)}</strong>
                    {view.next_alpha_uuid === view.uuid && ' (you)'}
                </p>
            )}

            <h4>Team Points</h4>
            <div className="team-totals is-centered">
                <span className="team-score">
                    <Icon emoji={TEAM_EMOJI.ALPHA} label="Alpha team" />
                    <span className="score-text">Alpha Team: {view.alpha_team_points || 0} pts</span>
                </span>
                <span className="team-score">
                    <Icon emoji={TEAM_EMOJI.ATTACKER} label="Attackers" />
                    <span className="score-text">Attackers: {view.attacker_team_points || 0} pts</span>
                </span>
            </div>

            <div className="scoring-toggle">
                <button
                    type="button"
                    className="btn btn-secondary btn-inline"
                    onClick={toggleScoring}
                    aria-expanded={showScoring}
                    aria-controls="scoring-breakdown"
                >
                    {showScoring ? 'Hide how scoring works' : 'Show how scoring works'}
                </button>
            </div>
            {showScoring && (
                <div id="scoring-breakdown">
                    <ScoringBreakdown view={view} />
                </div>
            )}

            <h4>Player Levels</h4>
            <div className="level-chips">
                {players.map(player => (
                    <span
                        key={player.uuid}
                        className={`level-chip${promoted.includes(player.uuid) ? ' promoted' : ''}`}
                    >
                        <Avatar player={player} />
                        {teamMark(player) && (
                            <Icon emoji={teamMark(player).emoji} label={teamMark(player).label} />
                        )}
                        {' '}{player.name}: Lv{' '}
                        {LEVEL_LABELS[levels[player.uuid]] || levels[player.uuid] || '?'}
                        {promoted.includes(player.uuid) && (
                            <Icon emoji={RESULT_EMOJI.PROMOTION} label="Promoted" />
                        )}
                        {' '}({scores[player.uuid] || 0} pts)
                    </span>
                ))}
            </div>

            {kitty.length > 0 && (
                <>
                    <h4>Kitty</h4>
                    <p className="kitty-outcome">{kittyOutcome()}</p>
                    {/* Point cards are lifted, outlined and labelled with what
                      * they are worth; the rest are dimmed. The label carries it
                      * on its own — the outline is only there to draw the eye. */}
                    <div className="kitty-cards">
                        {kitty.map((card, idx) => {
                            const points = kittyCardPoints[idx] || 0;
                            return (
                                <div
                                    key={idx}
                                    className={`kitty-card${points ? ' is-point-card' : ''}`}
                                >
                                    <Card card={card} selected={false} />
                                    {points > 0 && (
                                        <span className="kitty-card-points">+{points}</span>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </>
            )}

            {view.hosting ? (
                <button className="btn btn-orange btn-spaced" onClick={() => emit(SOCKET_EVENTS.NEXT_ROUND)}>
                    Start Next Round
                </button>
            ) : (
                /* Named, as the lobby names them — "the host" leaves everyone
                 * looking round the table to work out who they are waiting on.
                 * Nameless only if the host is not in the player list, which
                 * happens on the render before the first state arrives. */
                <p className="lobby-status">
                    {host
                        ? `Waiting for host (${host.name}) to start the next round...`
                        : 'Waiting for the host to start the next round...'}
                </p>
            )}
        </div>
    );
};

export default RoundSummary;
