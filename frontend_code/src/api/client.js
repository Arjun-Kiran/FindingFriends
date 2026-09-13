import { logger } from './logger';

/* HTTP calls to the game backend.
 *
 * Every response is checked for `ok` before use, so a 404 for a missing game
 * surfaces as a thrown ApiError rather than an error object masquerading as
 * game state. */

export class ApiError extends Error {
    constructor(message, { status, code } = {}) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.code = code;
    }

    /** True when the game or player no longer exists on the server. */
    get isMissing() {
        return this.status === 404;
    }
}

const request = async (path, options = {}) => {
    let response;
    try {
        response = await fetch(path, options);
    } catch (cause) {
        logger.error(`request to ${path} could not reach the server:`, cause.message);
        throw new ApiError('Could not reach the server', { code: 'network_error' });
    }

    let body = null;
    try {
        body = await response.json();
    } catch {
        // Non-JSON response; fall through to the status check below.
    }

    if (!response.ok) {
        // A 404 is the expected answer for a game that has ended — the UI
        // handles it. Anything else is worth a trace the player can send on.
        if (response.status !== 404) {
            logger.error(`request to ${path} failed (${response.status}):`, body);
        }
        throw new ApiError(
            (body && body.message) || `Request failed (${response.status})`,
            { status: response.status, code: body && body.error }
        );
    }

    /* Every route answers with JSON. A success that is not JSON came from
     * somewhere else — in dev, a path the vite proxy does not forward gets
     * index.html back with a 200 — and handing null on as the answer only
     * fails later, somewhere that cannot say why. */
    if (body === null) {
        logger.error(`request to ${path} did not come back as JSON — is it proxied to the backend?`);
        throw new ApiError('Unexpected response from the server', { status: response.status, code: 'not_json' });
    }

    return body;
};

export const createGame = () => request('/create');

export const joinGame = (gameCode, nickName) =>
    request(`/join/${encodeURIComponent(gameCode)}?nick_name=${encodeURIComponent(nickName)}`);

/* Watch a game rather than play in it (HR-8). Works mid-game, which joining
 * does not. The token that comes back is stored and sent exactly like a
 * player's — it is the server that knows it belongs to a watcher, and that
 * starts treating it as a seat's if the host hands them one. */
export const watchGame = (gameCode, nickName) =>
    request(`/watch/${encodeURIComponent(gameCode)}?nick_name=${encodeURIComponent(nickName)}`);

/* The player's own view, hand included. The token goes in a header rather than
 * the URL, which would leave it in server logs and browser history. */
export const fetchPlayerView = (gameCode, playerToken) =>
    request(`/game/${encodeURIComponent(gameCode)}/player`, {
        headers: { 'X-Player-Token': playerToken },
    });
