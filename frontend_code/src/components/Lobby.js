import { useEffect, useState, useRef } from "react";
import { createSocket } from "../api/socket";
import { SOCKET_EVENTS } from "../api/events";
import { fetchPlayerView } from "../api/client";
import { PHASE } from "../constants/phases";

const MIN_PLAYERS = 5;
const TOAST_DURATION_MS = 4000;

const Lobby = (props) => {
    const [gameState, setGameState] = useState({});
    const [errorMessage, setErrorMessage] = useState('');
    const [copied, setCopied] = useState(false);
    const [toastMessage, setToastMessage] = useState('');
    const socketRef = useRef(null);
    const handedOffToGame = useRef(false);

    const game_code = props.sessionInfo['game_code'];
    const player_uuid = props.sessionInfo['user_uuid'];

    const isHost = gameState.hosting || false;
    const latestEvent = (gameState.events && gameState.events.length > 0)
        ? gameState.events[gameState.events.length - 1]
        : null;
    // Depend on primitives, not the event object, so a re-fetch of identical
    // state doesn't re-trigger the toast.
    const latestEventUuid = latestEvent && latestEvent.uuid;
    const latestEventMessage = latestEvent && latestEvent.message;

    useEffect(() => {
        if (!latestEventMessage) {
            return undefined;
        }

        setToastMessage(latestEventMessage);
        const timer = setTimeout(() => setToastMessage(''), TOAST_DURATION_MS);

        return () => clearTimeout(timer);
    }, [latestEventUuid, latestEventMessage]);

    useEffect(() => {
        const socket = createSocket();
        socketRef.current = socket;

        socket.on(SOCKET_EVENTS.CONNECT, () => {
            socket.emit(SOCKET_EVENTS.JOIN, { game_code: game_code, player_uuid: player_uuid });
        });

        socket.on(SOCKET_EVENTS.GAME_STATS, (data) => {
            setGameState(data);
            if (data.game_event_state && data.game_event_state !== PHASE.WAITING_FOR_PLAYERS) {
                if (props.onGameStarted) {
                    handedOffToGame.current = true;
                    props.onGameStarted(data, socket);
                }
            }
        });

        socket.on(SOCKET_EVENTS.ERROR, (data) => {
            setErrorMessage((data && data.message) || 'An error occurred');
        });

        return function cleanup() {
            // Don't disconnect if the socket was handed off to Game component
            if (!handedOffToGame.current) {
                socket.disconnect();
            }
        };
    }, [game_code, player_uuid]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        fetchPlayerView(game_code, player_uuid)
            .then(setGameState)
            .catch(err => setErrorMessage(err.message || 'Failed to load the lobby'));
    }, [game_code, player_uuid]);

    const handleStartGame = () => {
        if (socketRef.current) {
            socketRef.current.emit(SOCKET_EVENTS.START_GAME, {
                game_code: game_code,
                player_uuid: player_uuid
            });
        }
    };

    const handleLeave = () => {
        if (socketRef.current) {
            socketRef.current.emit(SOCKET_EVENTS.LEAVE_LOBBY, {
                game_code: game_code,
                player_uuid: player_uuid
            });
        }
        if (props.onLeaveGame) {
            props.onLeaveGame();
        }
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(game_code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const playerList = gameState.player_list || [];
    const canStart = isHost && gameState.can_start_game;

    return (
        <div className="lobby-container">
            <div className="lobby-card">
                {errorMessage && (
                    <div className="info-panel error lobby-error">
                        <span>{errorMessage}</span>
                        <button className="close-btn" onClick={() => setErrorMessage('')}>✕</button>
                    </div>
                )}

                <div className="lobby-header">
                    <h2>Game Lobby</h2>
                    {props.onLeaveGame && (
                        <button className="btn-leave" onClick={handleLeave}>Leave</button>
                    )}
                </div>

                <div className="game-code-row">
                    <div className="game-code-display">{game_code}</div>
                    <button className="btn-copy" onClick={handleCopy}>
                        {copied ? 'Copied!' : 'Copy'}
                    </button>
                </div>

                <p className="lobby-hint">Share this code with friends to join</p>

                <p className="lobby-identity">
                    Playing as <strong>{gameState.name}</strong>
                    {isHost && <span className="host-tag"> (Host)</span>}
                </p>

                {toastMessage && (
                    <div className="toast-notification">{toastMessage}</div>
                )}

                <h3 className="lobby-players-heading">Players ({playerList.length})</h3>
                <ul className="player-list">
                    {playerList.map((player, idx) => (
                        <li key={player.uuid || idx} className={player.uuid === player_uuid ? 'is-you' : ''}>
                            {player.name}
                            {player.uuid === player_uuid && ' (you)'}
                        </li>
                    ))}
                </ul>

                {isHost && !canStart && (
                    <p className="lobby-status">Waiting for more players (need at least {MIN_PLAYERS})...</p>
                )}

                {canStart && (
                    <button onClick={handleStartGame} className="btn btn-primary">
                        Start Game
                    </button>
                )}

                {!isHost && (
                    <p className="lobby-status">Waiting for host to start the game...</p>
                )}
            </div>
        </div>
    );
}

export default Lobby;
