import { useEffect, useRef, useState } from 'react';
import { createSocket, SERVER_URL } from '../api/socket';
import { SOCKET_EVENTS } from '../api/events';
import { logger } from '../api/logger';

/* Owns the socket connection and the game state pushed over it.
 *
 * When `externalSocket` is given (the Lobby hands its socket to the Game on
 * start) that connection is reused and never torn down here. Otherwise a new
 * connection is opened and closed with the component. */
export const useGameSocket = ({ gameCode, playerUuid, externalSocket, initialState, onSessionInvalid }) => {
    const [gameState, setGameState] = useState(initialState || {});
    const [errorMessage, setErrorMessage] = useState('');
    // False while the socket is down. The last game state stays on screen, so
    // consumers use this to say so and to stop offering actions.
    const [connected, setConnected] = useState(false);
    // Held in state, not a ref, so the first render after connecting re-renders
    // consumers that need the socket to enable their controls.
    const [ownSocket, setOwnSocket] = useState(null);
    // Kept in a ref so a new callback identity each render doesn't tear down
    // and re-add the socket listeners below.
    const sessionInvalidRef = useRef(onSessionInvalid);
    sessionInvalidRef.current = onSessionInvalid;

    useEffect(() => {
        if (externalSocket) return undefined;

        const socket = createSocket();
        setOwnSocket(socket);

        return () => socket.disconnect();
    }, [externalSocket]);

    const socket = externalSocket || ownSocket;

    useEffect(() => {
        if (!socket) return undefined;

        const handleGameStats = (data) => {
            setGameState(data);
            setErrorMessage('');
        };
        const handleError = (data) => {
            setErrorMessage((data && data.message) || 'An error occurred');
        };
        const handleSessionInvalid = (data) => {
            if (sessionInvalidRef.current) sessionInvalidRef.current(data);
        };
        // Re-announce ourselves on every connect, not just the first: after the
        // server restarts, socket.io reconnects silently and the server has no
        // memory of this socket's room or player. The re-join is also what
        // surfaces a session that no longer exists.
        const handleConnect = () => {
            setConnected(true);
            socket.emit(SOCKET_EVENTS.JOIN, { game_code: gameCode, player_uuid: playerUuid });
        };
        // Nothing sent from here reaches the server until we reconnect, so the
        // board on screen is a snapshot from now on.
        const handleDisconnect = (reason) => {
            setConnected(false);
            logger.warn('socket disconnected:', reason);
        };
        /* The connection never came up. socket.io keeps retrying in silence, so
         * without this there is nothing anywhere to explain a game that simply
         * never loads — the failure mode behind a misconfigured proxy, where
         * polling succeeds and only the websocket upgrade fails. */
        const handleConnectError = (error) => {
            setConnected(false);
            logger.error(
                `could not connect to ${SERVER_URL}:`,
                (error && error.message) || error
            );
        };

        socket.on(SOCKET_EVENTS.CONNECT, handleConnect);
        socket.on(SOCKET_EVENTS.DISCONNECT, handleDisconnect);
        socket.on(SOCKET_EVENTS.CONNECT_ERROR, handleConnectError);
        socket.on(SOCKET_EVENTS.GAME_STATS, handleGameStats);
        socket.on(SOCKET_EVENTS.ERROR, handleError);
        socket.on(SOCKET_EVENTS.SESSION_INVALID, handleSessionInvalid);

        // A socket handed over already connected won't fire 'connect' again.
        if (socket.connected) handleConnect();

        return () => {
            socket.off(SOCKET_EVENTS.CONNECT, handleConnect);
            socket.off(SOCKET_EVENTS.DISCONNECT, handleDisconnect);
            socket.off(SOCKET_EVENTS.CONNECT_ERROR, handleConnectError);
            socket.off(SOCKET_EVENTS.GAME_STATS, handleGameStats);
            socket.off(SOCKET_EVENTS.ERROR, handleError);
            socket.off(SOCKET_EVENTS.SESSION_INVALID, handleSessionInvalid);
        };
    }, [socket, gameCode, playerUuid]);

    return { socket, connected, gameState, errorMessage, setErrorMessage };
};
