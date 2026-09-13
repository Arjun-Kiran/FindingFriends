import { useEffect, useMemo, useState } from 'react';

/* The server's clock, as near as this browser can tell, in epoch seconds —
 * re-read once a second while `ticking` is on.
 *
 * Countdowns run against times the server stamped, and a browser's own clock
 * can be minutes out. So each view carries the server's time when it was
 * built, and the gap between that and this browser's clock is added back. */
export const useServerNow = (serverTime, ticking) => {
    const offset = useMemo(
        () => (serverTime ? serverTime - Date.now() / 1000 : 0),
        [serverTime]
    );
    const [, setTick] = useState(0);

    useEffect(() => {
        if (!ticking) return undefined;
        const timer = setInterval(() => setTick(tick => tick + 1), 1000);
        return () => clearInterval(timer);
    }, [ticking]);

    return Date.now() / 1000 + offset;
};
