import { useNotifications } from '../../hooks/useNotifications';
import { CORNER, useNotificationCorner } from '../../hooks/useNotificationCorner';
import { eventTimeMs, relativeTime } from '../../utils/relativeTime';
import { Avatar } from '../Emoji';

/* The running feed of what is happening at the table — who played what, who
 * took the trick, who just outed themselves as a friend.
 *
 * Only the newest few are kept on screen and they do not time out: a player
 * who looks up mid-hand should find the last three things that happened, with
 * how long ago each was, rather than an empty corner. */
const Notifications = ({ events = [], players = [] }) => {
    const notifications = useNotifications(events);
    const { corner, toggle } = useNotificationCorner();

    if (notifications.length === 0) return null;

    const movingTo = corner === CORNER.RIGHT ? 'left' : 'right';

    // Events about the table rather than a player carry no uuid, and events
    // about someone who has since left will not match anyone.
    const subjectOf = (event) => players.find(player => player.uuid === event.player_uuid);

    return (
        /* role="log" with a polite live region: these announce themselves as
           they arrive without interrupting whatever is being read. */
        <div className={`notifications is-${corner}`} role="log" aria-live="polite">
            <button
                type="button"
                className="notifications-move"
                onClick={toggle}
                aria-label={`Move notifications to the ${movingTo}`}
                title={`Move notifications to the ${movingTo}`}
            >
                {corner === CORNER.RIGHT ? '←' : '→'}
            </button>

            {notifications.map((event, idx) => {
                const subject = subjectOf(event);
                return (
                /* The newest is outlined so a glance finds what just happened,
                   without having to read all three and compare timestamps. */
                <div
                    className={`notification${idx === 0 ? ' is-latest' : ''}`}
                    key={event.uuid}
                >
                    <span className="notification-message">
                        {subject && <><Avatar player={subject} />{' '}</>}
                        {event.message}
                    </span>
                    <span className="notification-time">
                        {relativeTime(eventTimeMs(event.time_stamp))}
                    </span>
                </div>
                );
            })}
        </div>
    );
};

export default Notifications;
