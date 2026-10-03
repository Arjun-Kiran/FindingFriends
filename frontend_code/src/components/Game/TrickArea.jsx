import Card from '../Card';
import { Avatar, Icon } from '../Emoji';
import { TEAM_MARK } from '../../utils/teams';
import { formatCountdown } from '../../utils/countdown';

/* The cards on the table for the current trick, one box per player's play,
 * with who played it named once underneath.
 *
 * `playedBy` is one uuid per card, in the same order as `cards`. A player's
 * cards arrive together, so a run of the same uuid is one play. A card with no
 * matching entry still renders, as a play of its own with no name — games
 * saved before the pile recorded who played what have cards but no
 * attribution, and a missing name beats a missing card.
 *
 * `winningUuid` is whoever is currently taking the trick; their box glows. It
 * moves as later plays beat earlier ones, and the play carries the words as a
 * tooltip — a glow says nothing to a reader being read to.
 *
 * `teamFor` says which side to show a player as, and is the same rule the
 * players bar uses — a side that is still a secret shows as nothing here too.
 * See utils/teams.js. It sits beside the name, once per play.
 *
 * `leadCount` is how many of the cards are the lead — the first play, since the
 * pile grows in play order — and `leadLabel` says what it asks for ('a pair in
 * clubs'). The lead's box is heavier than the rest and labelled in words: the
 * card winning may be a trump, and says nothing about what has to be followed.
 *
 * `clearing` is HR-10's finished trick waiting to be taken off the table, or
 * null — see utils/trick.js. The button goes here rather than in the panel
 * above because it acts on these cards, the same reason the play button sits
 * with the hand. */

/** The pile as plays: lists of card indices, the lead first when there is one. */
const playsOf = (cards, playedBy, leadSize) => {
    const plays = leadSize > 0 ? [cards.slice(0, leadSize).map((_, idx) => idx)] : [];
    for (let idx = leadSize; idx < cards.length; idx += 1) {
        const last = plays[plays.length - 1];
        const sameAsLast = last && idx - 1 >= leadSize && playedBy[idx] && playedBy[idx] === playedBy[idx - 1];
        if (sameAsLast) {
            last.push(idx);
        } else {
            plays.push([idx]);
        }
    }
    return plays;
};

const TrickArea = ({
    cards = [], playedBy = [], players = [], winningUuid = '', teamFor = () => '',
    clearing = null, onClear = null, leadCount = 0, leadLabel = '',
}) => {
    if (cards.length === 0) return null;

    const playerFor = (idx) => players.find(player => player.uuid === playedBy[idx]);
    const teamMark = (player) => TEAM_MARK[teamFor(player.uuid)];
    // Never more than is on the table. No lead recorded — a game saved before
    // it was kept — and nothing is drawn as the lead.
    const leadSize = Math.min(leadCount, cards.length);

    const renderPlay = (indices, playIdx) => {
        const first = indices[0];
        const player = playerFor(first);
        const isLead = leadSize > 0 && playIdx === 0;
        const isWinning = Boolean(winningUuid) && playedBy[first] === winningUuid;
        const mark = player && teamMark(player);
        const className = `trick-play${isLead ? ' is-lead' : ''}${isWinning ? ' is-winning' : ''}`;
        return (
            <div
                className={className}
                key={first}
                title={isWinning ? 'Winning the trick' : undefined}
            >
                {isLead && (
                    <span className="trick-play-label">
                        {leadLabel ? `Lead — ${leadLabel}` : 'Lead'}
                    </span>
                )}
                <div className="trick-play-cards">
                    {indices.map(idx => <Card key={idx} card={cards[idx]} selected={false} />)}
                </div>
                {player && (
                    <span className="trick-play-player" title={player.name}>
                        <Avatar player={player} />
                        <span className="trick-play-name">{player.name}</span>
                        {mark && <Icon emoji={mark.emoji} label={mark.label} />}
                    </span>
                )}
            </div>
        );
    };

    return (
        <div className="trick-area">
            <h4>{clearing ? 'Trick won' : 'Current Trick'}</h4>
            <div className="trick-cards">
                {playsOf(cards, playedBy, leadSize).map(renderPlay)}
            </div>

            {/* Only the winner is offered the button; everyone else is told
                who the table is waiting on, so a stopped board is never a
                mystery. The countdown is on both, because it is the answer to
                "how long is this going to sit here?" either way. */}
            {clearing && (
                <div className="trick-clear">
                    {clearing.mine && onClear ? (
                        <button className="btn btn-primary btn-inline" onClick={onClear}>
                            {`Clear the trick (${formatCountdown(clearing.secondsLeft)})`}
                        </button>
                    ) : (
                        <span className="trick-clear-wait" role="status">
                            {`Waiting for ${clearing.name} to clear the trick — `}
                            {formatCountdown(clearing.secondsLeft)}
                        </span>
                    )}
                </div>
            )}
        </div>
    );
};

export default TrickArea;
