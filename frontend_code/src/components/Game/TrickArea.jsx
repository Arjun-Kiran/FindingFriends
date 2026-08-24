import Card from '../Card';
import { Avatar } from '../Emoji';

/* The cards on the table for the current trick, each under the avatar of the
 * player who played it.
 *
 * `playedBy` is one uuid per card, in the same order as `cards`. A card with no
 * matching entry still renders — games saved before the pile recorded who
 * played what have cards but no attribution, and a missing avatar beats a
 * missing card. */
const TrickArea = ({ cards = [], playedBy = [], players = [] }) => {
    if (cards.length === 0) return null;

    const playerFor = (idx) => players.find(player => player.uuid === playedBy[idx]);

    return (
        <div className="trick-area">
            <h4>Current Trick</h4>
            <div className="trick-cards">
                {cards.map((card, idx) => {
                    const player = playerFor(idx);
                    return (
                        <div className="trick-play" key={idx}>
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
