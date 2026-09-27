import { RESULT_EMOJI } from '../../constants/emoji';
import { Icon } from '../Emoji';

/* How this round was scored, as the ladder it was scored against (HR-6).
 *
 * The rows come from the server, which reads them off the scoring function
 * itself — see PointSystem.scoring_bands. Nothing here works out a band or an
 * edge: a table on screen that disagrees with the engine would be worse than
 * showing no table at all, and the only way to be sure it cannot is not to
 * have a second copy of the rule.
 */

const SIDE_LABEL = {
    trump_maker: 'Alpha Team',
    attacker: 'Attackers',
    none: 'Nobody moves',
};

/** "0", "5–55", or "245+" for the open-ended last row. */
const spanOf = ({ low, high }) => {
    if (high === null || high === undefined) return `${low}+`;
    return high === low ? `${low}` : `${low}–${high}`;
};

const resultOf = ({ side, levels }) => (
    side === 'none' ? SIDE_LABEL.none : `${SIDE_LABEL[side] || side} +${levels}`
);

const holds = (band, points) => (
    points >= band.low && (band.high === null || band.high === undefined || points <= band.high)
);

const ScoringBreakdown = ({ view }) => {
    const bands = view.scoring_bands || [];
    const points = view.round_attacker_points || 0;
    const banded = !view.settings || view.settings.scaled_level_promotion !== false;

    /* Turned off in the lobby, the round is decided by comparing the two
     * totals instead, and the ladder below is not what happened. Saying so
     * beats showing a table that did not apply. */
    if (!banded) {
        return (
            <div className="scoring-breakdown">
                <p className="scoring-breakdown-intro">
                    This table plays without the bands: the side with more card points
                    wins the round and climbs <strong>exactly one level</strong>. An
                    exact tie moves nobody.
                </p>
                <p className="scoring-breakdown-intro">
                    Alpha Team {view.alpha_team_points || 0} pts, Attackers {points} pts.
                </p>
            </div>
        );
    }

    if (bands.length === 0) return null;

    return (
        <div className="scoring-breakdown">
            <p className="scoring-breakdown-intro">
                {view.num_decks} decks, {view.points_in_play} card points in play. Only
                the <strong>attackers&rsquo;</strong> points decide the round — the two
                sides always add up to the total, so naming one names the other.
            </p>
            <table className="scoring-table">
                <caption className="scoring-table-caption">
                    Attackers took <strong>{points}</strong> of {view.points_in_play}
                </caption>
                <thead>
                    <tr>
                        <th scope="col">Attackers&rsquo; points</th>
                        <th scope="col">Result</th>
                    </tr>
                </thead>
                <tbody>
                    {bands.map((band) => {
                        const current = holds(band, points);
                        return (
                            <tr
                                key={`${band.low}-${band.side}-${band.levels}`}
                                className={current ? 'is-this-round' : undefined}
                            >
                                <th scope="row">{spanOf(band)}</th>
                                <td>
                                    {resultOf(band)}
                                    {/* Marked three ways over, because one of
                                        them is a background tint and a tint is
                                        the one that some eyes will not get:
                                        the glyph and the words carry it. */}
                                    {current && (
                                        <span className="scoring-this-round">
                                            <Icon emoji={RESULT_EMOJI.POINTS} label="This round" />
                                            this round
                                        </span>
                                    )}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
            <p className="scoring-breakdown-note">
                A level is gained for going <em>past</em> a step, never for landing on
                it, and no round is worth more than three levels either way. The
                attackers&rsquo; total includes the kitty counted double when they take
                the last trick, which is why the last row has no upper end.
            </p>
        </div>
    );
};

export default ScoringBreakdown;
