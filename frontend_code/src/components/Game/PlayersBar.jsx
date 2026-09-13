import { Avatar, Icon } from '../Emoji';
import { ROLE_EMOJI, RESULT_EMOJI, STATUS_EMOJI } from '../../constants/emoji';
import { TEAM_MARK } from '../../utils/teams';
import { formatCountdown } from '../../utils/countdown';

const PlayersBar = ({
    players = [],
    currentPlayer,
    myUuid,
    disconnected = [],
    alphaUuid = '',
    /* Who is ahead on points, on a table playing with the totals hidden. Empty
     * everywhere else: with the numbers on screen there is nothing for a flame
     * to tell anyone that reading the scores bar does not. */
    onFire = [],
    /* Which side to show a player as. Passed in rather than worked out here,
     * so the chips and the trick area can never disagree — see utils/teams.js
     * for why that matters. */
    teamFor = () => '',
    /* HR-8. Seats whose player is away or gone, keyed by seat, and the server
     * clock to count them down against. */
    vacancies = {},
    graceSeconds = 60,
    serverNow = 0,
    openSeats = [],
    /* Given only to a watcher: offer for a seat whose player has gone. */
    onTakeSeat = null,
    offeredSeat = '',
}) => (
    <div className="players-bar">
        {players.map((player, idx) => {
            const isCurrent = currentPlayer && currentPlayer.uuid === player.uuid;
            const isMe = player.uuid === myUuid;
            const isAlpha = alphaUuid && player.uuid === alphaUuid;
            // Their seat is held while they reconnect — say so, so a stalled
            // turn reads as "waiting for Bob" instead of "the game is broken".
            const isGone = disconnected.includes(player.uuid);
            const isOnFire = onFire.includes(player.uuid);
            const vacancy = vacancies[player.uuid];
            /* Worked out here as well as on the server, so the chip turns over
             * the moment its countdown reaches zero rather than whenever the
             * next update happens to arrive. */
            const secondsLeft = vacancy && !vacancy.left ? vacancy.since + graceSeconds - serverNow : 0;
            const isOpen = openSeats.includes(player.uuid) || Boolean(vacancy && secondsLeft <= 0);
            const isCountingDown = Boolean(vacancy) && !isOpen;
            /* What is true of this chip but has no words on it. The fire and
             * the dropped plug are both glyphs, and a glyph is a tooltip away
             * from meaning nothing — so the chip says it in full. Both at once
             * is a real state: the player who is ahead can also be the one
             * whose connection just went. */
            const chipTitle = [
                isGone && `${player.name} lost connection`,
                isCountingDown && `${player.name} has ${formatCountdown(secondsLeft)} to reconnect`,
                isOpen && `${player.name}'s seat is open`,
                isOnFire && `${player.name} is leading on points`,
            ].filter(Boolean).join(' — ') || undefined;
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

            const chipClasses = [
                'player-chip',
                isCurrent && 'is-current',
                isMe && 'is-me',
                isGone && 'is-disconnected',
                isOpen && 'is-open-seat',
            ].filter(Boolean).join(' ');

            return (
                <div className="player-seat" key={player.uuid || idx}>
                    {/* Omitted rather than left empty: the bar bottom-aligns
                      * the chips, so a player with no role simply has nothing
                      * above theirs rather than a reserved blank. */}
                    {roles.length > 0 && <span className="player-roles">{roles}</span>}
                    <div className={chipClasses} title={chipTitle}>
                        <Avatar player={player} />
                        {/* The fire is decoration on the name, so it is the
                          * name that burns. The glyph beside it is what
                          * actually carries the meaning — a chip is small, the
                          * flames are a glow, and neither a reader who cannot
                          * pick the colour out nor one being read to should be
                          * left working out why this name looks different. */}
                        <span className={`player-chip-name${isOnFire ? ' is-on-fire' : ''}`}>
                            {player.name}
                        </span>
                        {isOnFire && <Icon emoji={RESULT_EMOJI.LEADING} label="Leading on points" />}
                        {isGone && <Icon emoji={STATUS_EMOJI.DISCONNECTED} label="Lost connection" />}
                        {/* In words and numbers, not a draining ring: how long
                          * is left is the whole message, and a ring's colour
                          * or fill is exactly the thing not everyone can read. */}
                        {isCountingDown && (
                            <span className="seat-countdown">
                                <Icon emoji={STATUS_EMOJI.COUNTDOWN} label="Time left to reconnect" />
                                {formatCountdown(secondsLeft)}
                            </span>
                        )}
                        {isOpen && (
                            <span className="seat-open">
                                <Icon emoji={STATUS_EMOJI.SEAT_OPEN} label="Seat open" />
                                Seat open
                            </span>
                        )}
                        {/* No marker for whose turn it is. The ring around this
                          * chip says it, and the panel below says it in words —
                          * "Waiting for Bob to play..." — which is the one a
                          * screen reader actually reads. A third copy inside the
                          * chip only competed with the markers that have nothing
                          * else saying them. */}
                    </div>
                    {/* A watcher may offer for a seat from the moment its
                      * player goes, not only once it is open: the host can
                      * approve during the countdown. */}
                    {onTakeSeat && vacancy && (offeredSeat === player.uuid ? (
                        <span className="seat-offered">Offered</span>
                    ) : (
                        <button
                            type="button"
                            className="btn-take-seat"
                            onClick={() => onTakeSeat(player.uuid)}
                            aria-label={`Take ${player.name}'s seat`}
                        >
                            Take seat
                        </button>
                    ))}
                </div>
            );
        })}
    </div>
);

export default PlayersBar;
