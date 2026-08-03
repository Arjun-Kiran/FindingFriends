import { useEffect, useState } from 'react';
import { createSocket } from '../api/socket';
import { SOCKET_EVENTS } from '../api/events';

/* Owns the socket connection and the game state pushed over it.
 *
 * When `externalSocket` is given (the Lobby hands its socket to the Game on
 * start) that connection is reused and never torn down here. Otherwise a new
 * connection is opened and closed with the component. */
export const useGameSocket = ({ gameCode, playerUuid, externalSocket, initialState }) => {
    const [gameState, setGameState] = useState(initialState || {});
    const [errorMessage, setErrorMessage] = useState('');
    // Held in state, not a ref, so the first render after connecting re-renders
    // consumers that need the socket to enable their controls.
    const [ownSocket, setOwnSocket] = useState(null);

    useEffect(() => {
        if (externalSocket) return undefined;

        const socket = createSocket();
        socket.on(SOCKET_EVENTS.CONNECT, () => {
            socket.emit(SOCKET_EVENTS.JOIN, { game_code: gameCode, player_uuid: playerUuid });
        });
        setOwnSocket(socket);

        return () => socket.disconnect();
    }, [externalSocket, gameCode, playerUuid]);

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

        socket.on(SOCKET_EVENTS.GAME_STATS, handleGameStats);
        socket.on(SOCKET_EVENTS.ERROR, handleError);

        return () => {
            socket.off(SOCKET_EVENTS.GAME_STATS, handleGameStats);
            socket.off(SOCKET_EVENTS.ERROR, handleError);
        };
    }, [socket]);

    return { socket, gameState, errorMessage, setErrorMessage };
};
