import { io } from 'socket.io-client';

/* Websockets bypass the CRA dev proxy in package.json, so the server URL has
 * to be given explicitly. Set REACT_APP_SERVER_URL for anything but local dev. */
export const SERVER_URL = process.env.REACT_APP_SERVER_URL || 'http://127.0.0.1:5050';

export const createSocket = () => io(SERVER_URL, { transports: ['websocket'] });
