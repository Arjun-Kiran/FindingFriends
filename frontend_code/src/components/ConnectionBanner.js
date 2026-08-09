import { useEffect, useState } from 'react';

/* How long the socket may be down before we say anything. Covers the moment
 * before a fresh socket finishes connecting, and short blips that resolve on
 * their own — neither is worth interrupting the player for. */
const GRACE_MS = 1500;

/* Shown while the socket is down.
 *
 * The last state the server sent stays on screen — it has to, there's nothing
 * else to draw — so this says out loud that it's a snapshot and that actions
 * won't land until the connection is back. socket.io retries on its own; if the
 * game is gone by the time it succeeds, the server answers the re-join with
 * `session_invalid` and the app returns to the home screen. */
const ConnectionBanner = ({ connected }) => {
    const [showing, setShowing] = useState(false);

    useEffect(() => {
        if (connected) {
            setShowing(false);
            return undefined;
        }

        const timer = setTimeout(() => setShowing(true), GRACE_MS);
        return () => clearTimeout(timer);
    }, [connected]);

    if (!showing) return null;

    return (
        <div className="info-panel connection-banner" role="status">
            <span>Reconnecting to the server... the board may be out of date.</span>
        </div>
    );
};

export default ConnectionBanner;
