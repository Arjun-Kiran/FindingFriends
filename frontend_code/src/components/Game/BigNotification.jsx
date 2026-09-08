import { useBigNotification } from '../../hooks/useBigNotification';
import { STATUS_EMOJI } from '../../constants/emoji';
import { Avatar, Icon } from '../Emoji';

/* The big play, called out across the middle of the table for a moment.
 *
 * Sits over the board rather than beside it — the whole point is that you
 * cannot miss it — which is also why it never lasts and never takes a click.
 * The corner feed is the record; this is the interruption, and the two read
 * the same events.
 */
const BigNotification = ({ events = [], myTurn = false, players = [] }) => {
    const banner = useBigNotification({ events, myTurn, players });

    if (!banner) return null;

    return (
        /* Hidden from screen readers, which are already told all of this: the
           feed announces every event as a polite live region, and the turn
           indicator in the phase panel says whose turn it is in words. A
           second announcement of the same thing is just an interruption.

           Keyed so a banner arriving while one is up remounts the element and
           restarts the animation, rather than inheriting a fade already most
           of the way through. */
        <div className="big-notification" key={banner.key} aria-hidden="true">
            <div className="big-notification-card">
                {banner.lines.map(line => (
                    <p className="big-notification-line" key={line.id}>
                        {line.player
                            ? <><Avatar player={line.player} /> <strong>{line.player.name}</strong> {line.text}</>
                            /* The turn line is about you, so it gets the same
                               pointing finger the players bar puts on your
                               chip rather than an avatar. */
                            : <><Icon emoji={STATUS_EMOJI.CURRENT_TURN} label="Your turn" /> <strong>{line.text}</strong></>}
                    </p>
                ))}
            </div>
        </div>
    );
};

export default BigNotification;
