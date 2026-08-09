import { io } from 'socket.io-client';

/* Websockets bypass the dev proxy in vite.config.js, so the server URL has to
 * be given explicitly. Set VITE_SERVER_URL for anything but local dev — it is
 * baked in at build time, so the deployed build needs it set before `npm run
 * build`, not at runtime. */
export const SERVER_URL = import.meta.env.VITE_SERVER_URL || 'http://127.0.0.1:5050';

export const createSocket = () => io(SERVER_URL, { transports: ['websocket'] });
