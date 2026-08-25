/* Turning a server event's timestamp into "now" / "10 minutes ago".
 *
 * The backend writes time_stamp as epoch SECONDS in a string (see
 * EventSystem.build_event), not milliseconds and not ISO — parse accordingly.
 */

const SECOND = 1000;
const MINUTE = 60 * SECOND;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** Epoch milliseconds for an event's time_stamp, or null if unparseable. */
export const eventTimeMs = (timeStamp) => {
    const seconds = Number.parseFloat(timeStamp);
    return Number.isFinite(seconds) ? seconds * SECOND : null;
};

const plural = (count, unit) => `${count} ${unit}${count === 1 ? '' : 's'} ago`;

/* How long ago `thenMs` was, in words.
 *
 * Anything under a minute reads as "now", which also absorbs clock skew: the
 * browser and the server keep their own time, so a fresh event can look
 * slightly in the future. That must never surface as a negative age. */
export const relativeTime = (thenMs, nowMs = Date.now()) => {
    if (thenMs === null || thenMs === undefined) return '';

    const elapsed = nowMs - thenMs;
    if (elapsed < MINUTE) return 'now';
    if (elapsed < HOUR) return plural(Math.floor(elapsed / MINUTE), 'minute');
    if (elapsed < DAY) return plural(Math.floor(elapsed / HOUR), 'hour');
    return plural(Math.floor(elapsed / DAY), 'day');
};
