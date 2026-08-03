/* Socket event names. Must match the @socketio.on handlers in backend Main.py. */

export const SOCKET_EVENTS = {
    // lifecycle
    CONNECT: 'connect',
    DISCONNECT: 'disconnect',

    // server -> client
    GAME_STATS: 'game_stats',
    ERROR: 'error',

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
