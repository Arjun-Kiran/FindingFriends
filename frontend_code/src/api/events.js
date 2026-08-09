/* Socket event names. Must match the @socketio.on handlers in backend Main.py. */

export const SOCKET_EVENTS = {
    // lifecycle
    CONNECT: 'connect',
    DISCONNECT: 'disconnect',
    // Emitted when a connection attempt fails outright — the server is down,
    // CORS rejected the origin, or the websocket upgrade failed at the proxy.
    // Distinct from DISCONNECT, which means an established connection dropped.
    CONNECT_ERROR: 'connect_error',

    // server -> client
    GAME_STATS: 'game_stats',
    ERROR: 'error',
    // The saved session points at a game or player the server no longer has —
    // the client should drop it and go back to the home screen.
    SESSION_INVALID: 'session_invalid',

    // client -> server
    JOIN: 'join',
    LEAVE_LOBBY: 'leave_lobby',
    START_GAME: 'start_game',
    DECLARE_TRUMP: 'declare_trump',
    CALL_FRIENDS: 'call_friends',
    KITTY_EXCHANGE: 'kitty_exchange',
    PLAY_CARDS: 'play_cards',
    NEXT_ROUND: 'next_round',
};
