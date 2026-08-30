import { Avatar, Icon } from '../Emoji';
import { ROLE_EMOJI, STATUS_EMOJI } from '../../constants/emoji';
import { TEAM_MARK } from '../../utils/teams';

const PlayersBar = ({
    players = [],
    currentPlayer,
    myUuid,
    disconnected = [],
    alphaUuid = '',
    /* Which side to show a player as. Passed in rather than worked out here,
     * so the chips and the trick area can never disagree — see utils/teams.js
     * for why that matters. */
    teamFor = () => '',
}) => (
    <div className="players-bar">
        {players.map((player, idx) => {
            const isCurrent = currentPlayer && currentPlayer.uuid === player.uuid;
            const isMe = player.uuid === myUuid;
            const isAlpha = alphaUuid && player.uuid === alphaUuid;
            // Their seat is held while they reconnect — say so, so a stalled
            // turn reads as "waiting for Bob" instead of "the game is broken".
            const isGone = disconnected.includes(player.uuid);
            const mark = TEAM_MARK[teamFor(player.uuid)];
            /* Who someone IS sits above the chip; what is happening TO them
             * stays inside it. A role is fixed for the round and reads as a
             * label over the seat, while a dropped connection or a turn in
             * progress belongs on the plate that is changing. */
            const roles = [
                /* No mark for "you" — the stripe on your own chip says it, and
                 * a stripe is there or it is not, which needs no colour telling
                 * apart from another colour. */
                isAlpha && <Icon key="alpha" emoji={ROLE_EMOJI.ALPHA} label="Alpha player" />,
                /* No separate mark for a revealed friend: revealing yourself
                 * IS joining the alpha team, so the swords already say it. One
                 * without a crown beside it is a friend. */
                mark && <Icon key="team" emoji={mark.emoji} label={mark.label} />,
            ].filter(Boolean);

            return (
                <div className="player-seat" key={player.uuid || idx}>
                    {/* Omitted rather than left empty: the bar bottom-aligns
                      * the chips, so a player with no role simply has nothing
                      * above theirs rather than a reserved blank. */}
                    {roles.length > 0 && <span className="player-roles">{roles}</span>}
                    <div
                        className={`player-chip${isCurrent ? ' is-current' : ''}${isMe ? ' is-me' : ''}${isGone ? ' is-disconnected' : ''}`}
                        title={isGone ? `${player.name} lost connection` : undefined}
                    >
                        <Avatar player={player} />
                        <span className="player-chip-name">{player.name}</span>
                        {isGone && <Icon emoji={STATUS_EMOJI.DISCONNECTED} label="Lost connection" />}
                        {isCurrent && <Icon emoji={STATUS_EMOJI.CURRENT_TURN} label="Their turn" />}
                    </div>
                </div>
            );
        })}
    </div>
);

export default PlayersBar;
