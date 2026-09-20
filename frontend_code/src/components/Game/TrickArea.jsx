import Card from '../Card';
import { Avatar, Icon } from '../Emoji';
import { TEAM_MARK } from '../../utils/teams';

/* The cards on the table for the current trick, each under the avatar of the
 * player who played it.
 *
 * `playedBy` is one uuid per card, in the same order as `cards`. A card with no
 * matching entry still renders — games saved before the pile recorded who
 * played what have cards but no attribution, and a missing avatar beats a
 * missing card.
 *
 * `winningUuid` is whoever is currently taking the trick; their cards glow. It
 * moves as later plays beat earlier ones. The glow is on the card itself, so
 * nothing in the row shifts as the lead changes hands, and the play carries the
 * words as a tooltip — a glow says nothing to a reader being read to.
 *
 * `teamFor` says which side to show a player as, and is the same rule the
 * players bar uses — a side that is still a secret shows as nothing here too.
 * See utils/teams.js. The side sits above the card and the player below it, so
 * a glance down the row reads as sides-against-sides rather than as pairs of
 * glyphs that have to be told apart one play at a time. */
const TrickArea = ({
    cards = [], playedBy = [], players = [], winningUuid = '', teamFor = () => '',
}) => {
    if (cards.length === 0) return null;

    const playerFor = (idx) => players.find(player => player.uuid === playedBy[idx]);
    const teamMark = (player) => TEAM_MARK[teamFor(player.uuid)];

    return (
        <div className="trick-area">
            <h4>Current Trick</h4>
            <div className="trick-cards">
                {cards.map((card, idx) => {
                    const player = playerFor(idx);
                    const isWinning = Boolean(winningUuid) && playedBy[idx] === winningUuid;
                    return (
                        <div
                            className={`trick-play${isWinning ? ' is-winning' : ''}`}
                            key={idx}
                            title={isWinning ? 'Winning the trick' : undefined}
                        >
                            {/* Whose side this card was played for, where that
                                is public. Always rendered, empty while the side
                                is still a secret: a mark appearing the moment a
                                friend reveals themselves would otherwise shunt
                                every card in the row downwards. */}
                            <span className="trick-play-team">
                                {player && teamMark(player) && (
                                    <Icon
                                        emoji={teamMark(player).emoji}
                                        label={teamMark(player).label}
                                    />
                                )}
                            </span>
                            <Card card={card} selected={false} />
                            {player && (
                                <span className="trick-play-player" title={player.name}>
                                    <Avatar player={player} />
                                    {/* Enough of the name to tell two players
                                        apart at a glance; the full one is on
                                        the title, and on the chip above. */}
                                    <span className="trick-play-name">
                                        {player.name.slice(0, 3)}
                                    </span>
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
