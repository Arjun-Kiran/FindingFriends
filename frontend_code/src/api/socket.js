import { io } from 'socket.io-client';

/* Where the websocket connects.
 *
 * Two deployments, opposite needs:
 *
 * - Dev: vite serves the page on :3000 while the backend is on :5050, and
 *   websockets bypass the vite proxy entirely, so the port must be named.
 * - Prod: one origin serves the page, the API and the socket, so the socket
 *   must NOT name a host — it has to follow whatever address the player typed,
 *   whether that is an IP, a domain, or localhost.
 *
 * So an explicitly EMPTY VITE_SERVER_URL means "same origin as the page", and
 * an unset one keeps the dev default. The distinction matters: `|| default`
 * cannot express it, because an empty string is falsy and silently became
 * 127.0.0.1:5050 — which in a remote player's browser is their own laptop.
 *
 * Baked in at build time, so a deployed build needs this set before
 * `npm run build`, not when the server starts. */
const DEV_DEFAULT = 'http://127.0.0.1:5050';
const configured = import.meta.env.VITE_SERVER_URL;

export const SERVER_URL = configured === undefined ? DEV_DEFAULT : configured;

/** Human-readable form of the above, for log messages. */
export const SERVER_LABEL = SERVER_URL || 'the page origin';

/* Passing no URL is what makes socket.io connect back to the page's own
 * origin; passing '' is not the same thing. */
export const createSocket = () => (
    SERVER_URL
        ? io(SERVER_URL, { transports: ['websocket'] })
        : io({ transports: ['websocket'] })
);
