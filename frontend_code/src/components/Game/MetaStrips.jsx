import { SUIT_SYMBOLS, ordinal } from '../../constants/cards';
import { PHASE } from '../../constants/phases';
import { Avatar, Icon } from '../Emoji';
import { RESULT_EMOJI, TEAM_EMOJI } from '../../constants/emoji';

const findPlayer = (players, uuid) => players.find(p => p.uuid === uuid);

/* The friend cards the alpha called, and — once someone has played one — who
 * that rule outed. Shown after the calling phase, and only while a friend is
 * still hidden.
 *
 * While the hunt is on this is the only place a reveal is spelled out, which is
 * why a second strip listing revealed friends by name was cut: with several
 * called cards in play, knowing that three friends exist is much less useful
 * than knowing which rule each of them tripped. That rests on every revealed
 * friend being credited against some called card — pinned in the backend's
 * test_team_system.py, because a friend no rule named would appear nowhere.
 *
 * Once the last friend is out the row has nothing left to say. Every side is
 * public by then — the players bar colours every chip, each reveal was
 * announced as it happened, and the scores bar has switched to team totals —
 * so all that remains is a record of which card outed whom, which is history
 * rather than something anyone is still working out.
 */
export const CalledCardsStrip = ({ view }) => {
    const called = view.friend_calling_cards || [];
    if (called.length === 0
        || view.game_event_state === PHASE.CALL_FRIENDS
        || view.all_friends_found) return null;

    const players = view.player_list || [];

    return (
        <div className="meta-strip">
            <strong>Called Cards:</strong>{' '}
            {called.map((cc, idx) => {
                const revealed = findPlayer(players, cc.revealed_by);
                return (
                    <span key={idx} className={revealed ? 'called-card is-revealed' : 'called-card'}>
                        {idx > 0 && ', '}
                        {ordinal(cc.order)} {cc.rank} of {SUIT_SYMBOLS[cc.suit] || cc.suit}
                        {revealed && (
                            <span className="called-card-revealer">
                                {' ('}<Avatar player={revealed} />{' '}{revealed.name}{')'}
                            </span>
                        )}
                    </span>
                );
            })}
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
                        <Avatar player={player} />{' '}
                        <Icon emoji={RESULT_EMOJI.POINTS} label="points" />
                        {/* The label stays one unbroken string: an icon spliced
                            into it would split the text node and make the score
                            unreadable to a screen reader reading it straight. */}
                        <span className="score-text">
                            {player.name}: {scores[player.uuid] || 0} pts
                        </span>
                    </span>
                ))}
            </div>
        );
    }

    return (
        <div className="scores-bar">
            <span className="team-score is-mine">
                <Icon
                    emoji={view.on_alpha_team ? TEAM_EMOJI.ALPHA : TEAM_EMOJI.DEFENDER}
                    label={view.on_alpha_team ? 'Alpha team' : 'Defenders'}
                />
                <span className="score-text">
                    Your team ({view.on_alpha_team ? 'Alpha Team' : 'Defenders'}): {view.my_team_points || 0} pts
                </span>
            </span>
            <span className="team-score">
                <Icon emoji={TEAM_EMOJI.ALPHA} label="Alpha team" />
                <span className="score-text">Alpha Team: {view.alpha_team_points || 0} pts</span>
            </span>
            <span className="team-score">
                <Icon emoji={TEAM_EMOJI.DEFENDER} label="Defenders" />
                <span className="score-text">Defenders: {view.defender_team_points || 0} pts</span>
            </span>
        </div>
    );
};
