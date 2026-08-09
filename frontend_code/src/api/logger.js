/* One place for diagnostic output.
 *
 * Routine problems belong in the UI, not the console — this is for the things a
 * player can't see and would otherwise have to guess at: a socket that won't
 * connect, an API call that failed for a reason other than "that game is gone".
 * Keeping it behind one module means one place to silence it in tests, and one
 * place to point at a service later if that ever becomes worth doing.
 *
 * Never log game state. A player's view includes their own hand, and the
 * console ends up on screen shares and screenshots. */

const PREFIX = '[finding-friends]';

// Jest sets NODE_ENV=test; keep test output readable.
const enabled = process.env.NODE_ENV !== 'test';

export const logger = {
    info: (...args) => {
        if (enabled) console.info(PREFIX, ...args);
    },
    warn: (...args) => {
        if (enabled) console.warn(PREFIX, ...args);
    },
    error: (...args) => {
        if (enabled) console.error(PREFIX, ...args);
    },
};

export default logger;
