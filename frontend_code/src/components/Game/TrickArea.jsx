import Card from '../Card';
import { Avatar, Icon } from '../Emoji';
import { RESULT_EMOJI } from '../../constants/emoji';

/* The cards on the table for the current trick, each under the avatar of the
 * player who played it.
 *
 * `playedBy` is one uuid per card, in the same order as `cards`. A card with no
 * matching entry still renders — games saved before the pile recorded who
 * played what have cards but no attribution, and a missing avatar beats a
 * missing card.
 *
 * `winningUuid` is whoever is currently taking the trick; their cards get a
 * star above them. It moves as later plays beat earlier ones. */
const TrickArea = ({ cards = [], playedBy = [], players = [], winningUuid = '' }) => {
    if (cards.length === 0) return null;

    const playerFor = (idx) => players.find(player => player.uuid === playedBy[idx]);

    return (
        <div className="trick-area">
            <h4>Current Trick</h4>
            <div className="trick-cards">
                {cards.map((card, idx) => {
                    const player = playerFor(idx);
                    const isWinning = Boolean(winningUuid) && playedBy[idx] === winningUuid;
                    return (
                        <div className="trick-play" key={idx}>
                            {/* Always rendered, empty when not winning: an
                                appearing star would otherwise shunt every card
                                in the row downwards as the lead changes. */}
                            <span className="trick-play-winning">
                                {isWinning && (
                                    <Icon
                                        emoji={RESULT_EMOJI.WINNING_TRICK}
                                        label="Winning the trick"
                                    />
                                )}
                            </span>
                            <Card card={card} selected={false} />
                            {player && (
                                <span className="trick-play-player" title={player.name}>
                                    <Avatar player={player} />
                                </span>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default TrickArea;
