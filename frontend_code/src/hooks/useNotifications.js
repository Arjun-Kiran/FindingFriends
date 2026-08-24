import { useEffect, useState } from 'react';

/** How many notifications stay on screen at once. */
export const MAX_VISIBLE = 3;

/* Relative times go stale on their own — "now" stops being true a minute after
 * it is rendered, with no new event to trigger a re-render. This is the
 * heartbeat that keeps them honest. */
const TICK_MS = 30000;

/* The newest events, newest first, capped at MAX_VISIBLE.
 *
 * Events arrive oldest-first from the server and are the same list the game
 * state carries, so this reads the tail rather than keeping its own copy —
 * there is no local state to fall out of sync with the server. */
export const useNotifications = (events) => {
    const [, setTick] = useState(0);

    useEffect(() => {
        const timer = setInterval(() => setTick(tick => tick + 1), TICK_MS);
        return () => clearInterval(timer);
    }, []);

    const list = events || [];
    return list.slice(-MAX_VISIBLE).reverse();
};
