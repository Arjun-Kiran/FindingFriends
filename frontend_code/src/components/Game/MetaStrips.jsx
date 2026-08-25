import { SUIT_SYMBOLS, ordinal } from '../../constants/cards';
import { PHASE } from '../../constants/phases';
import { Avatar, Icon } from '../Emoji';
import { ROLE_EMOJI, RESULT_EMOJI, TEAM_EMOJI } from '../../constants/emoji';

const findPlayer = (players, uuid) => players.find(p => p.uuid === uuid);

const nameOf = (players, uuid) => {
    const player = findPlayer(players, uuid);
    return player ? player.name : uuid;
};

/** The friend cards the alpha called, shown once the calling phase is over. */
/* Each called card, and — once someone has played it — who that rule outed.
 *
 * With several called cards in play, knowing that three friends exist is much
 * less useful than knowing which rule each of them tripped, so the reveal is
 * shown against the rule rather than only in the friends list. */
export const CalledCardsStrip = ({ view }) => {
    const called = view.friend_calling_cards || [];
    if (called.length === 0 || view.game_event_state === PHASE.CALL_FRIENDS) return null;

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

export const RevealedFriendsStrip = ({ view }) => {
    const revealed = view.revealed_friends || [];
    if (revealed.length === 0) return null;

    const players = view.player_list || [];
    return (
        <div className="meta-strip is-friends">
            <strong>
                <Icon emoji={ROLE_EMOJI.FRIEND} label="Revealed friend" />Revealed Friends:
            </strong>{' '}
            {revealed.map((uuid, idx) => (
                <span key={uuid}>
                    {idx > 0 && ', '}
                    <Avatar player={findPlayer(players, uuid)} />{' '}{nameOf(players, uuid)}
                </span>
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
