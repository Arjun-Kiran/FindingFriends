import { useState } from 'react';
import { useNotifications } from '../../hooks/useNotifications';
import { CORNER, useNotificationCorner, useNotificationsCollapsed } from '../../hooks/useNotificationCorner';
import { eventTimeMs, relativeTime } from '../../utils/relativeTime';
import { Avatar } from '../Emoji';

/* The running feed of what is happening at the table — who played what, who
 * took the trick, who just outed themselves as a friend.
 *
 * Only the newest few are kept on screen and they do not time out: a player
 * who looks up mid-hand should find the last three things that happened, with
 * how long ago each was, rather than an empty corner.
 *
 * The player can fold the stack down to one button, which then says "new" in
 * words when something has happened since — so folding it away never means
 * missing that something did. */
const Notifications = ({ events = [], players = [] }) => {
    const notifications = useNotifications(events);
    const { corner, toggle } = useNotificationCorner();
    const { collapsed, toggle: toggleCollapsed } = useNotificationsCollapsed();
    const newestUuid = notifications.length > 0 ? notifications[0].uuid : '';
    // The newest the player has seen: whatever was on top when they last had
    // the stack open, or when the page loaded with it already folded.
    const [seenUuid, setSeenUuid] = useState(newestUuid);

    if (notifications.length === 0) return null;

    const movingTo = corner === CORNER.RIGHT ? 'left' : 'right';
    const hasNew = collapsed && newestUuid !== seenUuid;
    const toggleLabel = collapsed
        ? (hasNew ? 'Show notifications — new' : 'Show notifications')
        : 'Hide notifications';
    const onToggleCollapsed = () => {
        setSeenUuid(newestUuid);
        toggleCollapsed();
    };

    // Events about the table rather than a player carry no uuid, and events
    // about someone who has since left will not match anyone.
    const subjectOf = (event) => players.find(player => player.uuid === event.player_uuid);

    return (
        /* role="log" with a polite live region: these announce themselves as
           they arrive without interrupting whatever is being read. */
        <div className={`notifications is-${corner}${collapsed ? ' is-collapsed' : ''}`} role="log" aria-live="polite">
            {/* One child of the stack, so the fading by position below still
                counts from the first message. */}
            <div className="notifications-controls">
                <button
                    type="button"
                    className={`notifications-collapse${hasNew ? ' has-new' : ''}`}
                    onClick={onToggleCollapsed}
                    aria-expanded={!collapsed}
                    aria-label={toggleLabel}
                    title={toggleLabel}
                >
                    {collapsed ? (hasNew ? '🔔 New' : '🔔') : '▴ Hide'}
                </button>
                {!collapsed && (
                    <button
                        type="button"
                        className="notifications-move"
                        onClick={toggle}
                        aria-label={`Move notifications to the ${movingTo}`}
                        title={`Move notifications to the ${movingTo}`}
                    >
                        {corner === CORNER.RIGHT ? '←' : '→'}
                    </button>
                )}
            </div>

            {/* Folded away, the newest still reaches a screen reader: the
                live region is what announces it, and it stays mounted. */}
            {collapsed && (
                <span className="visually-hidden">{notifications[0].message}</span>
            )}

            {!collapsed && notifications.map((event, idx) => {
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
