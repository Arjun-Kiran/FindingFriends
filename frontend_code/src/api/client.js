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

const request = async (path) => {
    let response;
    try {
        response = await fetch(path);
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

    return body;
};

export const createGame = () => request('/create');

export const joinGame = (gameCode, nickName) =>
    request(`/join/${encodeURIComponent(gameCode)}?nick_name=${encodeURIComponent(nickName)}`);

export const fetchPlayerView = (gameCode, playerUuid) =>
    request(`/game/${encodeURIComponent(gameCode)}/player/${encodeURIComponent(playerUuid)}`);
