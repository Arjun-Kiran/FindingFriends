import { useEffect, useState, useRef } from "react";
import { createSocket, SERVER_LABEL } from "../api/socket";
import { copyText } from "../utils/copyText";
import { SOCKET_EVENTS } from "../api/events";
import { fetchPlayerView } from "../api/client";
import { logger } from "../api/logger";
import { useEventToast } from "../hooks/useEventToast";
import { PHASE } from "../constants/phases";
import ConnectionBanner from "./ConnectionBanner";
import AvatarPicker from "./AvatarPicker";
import { Avatar, Icon } from "./Emoji";
import { ROLE_EMOJI } from "../constants/emoji";
import { GAME_SETTINGS } from "../constants/gameSettings";

const MIN_PLAYERS = 5;

const Lobby = (props) => {
    const [gameState, setGameState] = useState({});
    const [errorMessage, setErrorMessage] = useState('');
    const [copyState, setCopyState] = useState('idle');
    const [connected, setConnected] = useState(false);
    const socketRef = useRef(null);
    const handedOffToGame = useRef(false);
    // Read through a ref so the socket effect below doesn't re-run (and
    // reconnect) every time the parent re-renders with a new callback.
    const sessionInvalidRef = useRef(props.onSessionInvalid);
    sessionInvalidRef.current = props.onSessionInvalid;

    const game_code = props.sessionInfo['game_code'];
    const player_uuid = props.sessionInfo['user_uuid'];

    const isHost = gameState.hosting || false;
    const toastMessage = useEventToast(gameState.events);

    useEffect(() => {
        const socket = createSocket();
        socketRef.current = socket;

        // Fires again on every reconnect, so a restarted server learns about
        // this player anew — or tells us the session is gone.
        const handleConnect = () => {
            setConnected(true);
            socket.emit(SOCKET_EVENTS.JOIN, { game_code: game_code, player_uuid: player_uuid });
        };

        // The player list on screen is frozen from here until we're back.
        const handleDisconnect = (reason) => {
            setConnected(false);
            logger.warn('socket disconnected:', reason);
        };

        // The connection never came up — see the note in useGameSocket.js.
        const handleConnectError = (error) => {
            setConnected(false);
            logger.error(
                `could not connect to ${SERVER_LABEL}:`,
                (error && error.message) || error
            );
        };

        const handleGameStats = (data) => {
            setGameState(data);
            if (data.game_event_state && data.game_event_state !== PHASE.WAITING_FOR_PLAYERS) {
                if (props.onGameStarted) {
                    handedOffToGame.current = true;
                    props.onGameStarted(data, socket);
                }
            }
        };

        const handleError = (data) => {
            setErrorMessage((data && data.message) || 'An error occurred');
        };

        const handleSessionInvalid = (data) => {
            if (sessionInvalidRef.current) sessionInvalidRef.current(data);
        };

        socket.on(SOCKET_EVENTS.CONNECT, handleConnect);
        socket.on(SOCKET_EVENTS.DISCONNECT, handleDisconnect);
        socket.on(SOCKET_EVENTS.CONNECT_ERROR, handleConnectError);
        socket.on(SOCKET_EVENTS.GAME_STATS, handleGameStats);
        socket.on(SOCKET_EVENTS.ERROR, handleError);
        socket.on(SOCKET_EVENTS.SESSION_INVALID, handleSessionInvalid);

        return function cleanup() {
            // Always drop our own listeners: when the socket is handed to the
            // Game it keeps living, and these closures would otherwise go on
            // updating an unmounted Lobby.
            socket.off(SOCKET_EVENTS.CONNECT, handleConnect);
            socket.off(SOCKET_EVENTS.DISCONNECT, handleDisconnect);
            socket.off(SOCKET_EVENTS.CONNECT_ERROR, handleConnectError);
            socket.off(SOCKET_EVENTS.GAME_STATS, handleGameStats);
            socket.off(SOCKET_EVENTS.ERROR, handleError);
            socket.off(SOCKET_EVENTS.SESSION_INVALID, handleSessionInvalid);
            // Don't disconnect if the socket was handed off to Game component
            if (!handedOffToGame.current) {
                socket.disconnect();
            }
        };
    }, [game_code, player_uuid]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        fetchPlayerView(game_code, player_uuid)
            .then(setGameState)
            .catch(err => {
                if (err.isMissing && sessionInvalidRef.current) {
                    sessionInvalidRef.current({ message: err.message });
                    return;
                }
                setErrorMessage(err.message || 'Failed to load the lobby');
            });
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

    const handleChooseAvatar = (avatar) => {
        if (socketRef.current) {
            socketRef.current.emit(SOCKET_EVENTS.CHOOSE_AVATAR, {
                game_code: game_code,
                player_uuid: player_uuid,
                avatar: avatar
            });
        }
    };

    /* Sent whole rather than one key at a time: two quick clicks could
     * otherwise land in either order and disagree about the rest. */
    const handleToggleSetting = (key) => {
        const socket = socketRef.current;
        if (!socket || !connected) {
            setErrorMessage('Not connected to the server — waiting to reconnect.');
            return;
        }
        socket.emit(SOCKET_EVENTS.UPDATE_SETTINGS, {
            game_code: game_code,
            player_uuid: player_uuid,
            settings: { ...settings, [key]: !settings[key] },
        });
    };

    /* Copy can genuinely fail: navigator.clipboard does not exist over plain
     * http:// on an IP, which is how a droplet beta is reached, so this has to
     * report failure rather than pretend. The code is on screen either way. */
    const handleCopy = async () => {
        const copied = await copyText(game_code);
        setCopyState(copied ? 'copied' : 'failed');
        setTimeout(() => setCopyState('idle'), 3000);
    };

    const playerList = gameState.player_list || [];
    const canStart = isHost && gameState.can_start_game;
    // Falls back to the unnamed wording rather than an empty pair of brackets:
    // the first render happens before any state has arrived.
    const hostName = (playerList.find(player => player.uuid === gameState.host_uuid) || {}).name;
    const settings = gameState.settings || {};

    return (
        <div className="lobby-container">
            <div className="lobby-card">
                <ConnectionBanner connected={connected} />

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
                        {copyState === 'copied' && 'Copied!'}
                        {copyState === 'failed' && 'Copy failed'}
                        {copyState === 'idle' && 'Copy'}
                    </button>
                </div>

                <p className="lobby-hint">
                    {copyState === 'failed'
                        ? 'Could not reach the clipboard — select the code above and copy it yourself.'
                        : 'Share this code with friends to join'}
                </p>

                <p className="lobby-identity">
                    Playing as <Avatar player={gameState} /> <strong>{gameState.name}</strong>
                    {isHost && (
                        <span className="host-tag">
                            {' '}<Icon emoji={ROLE_EMOJI.HOST} label="Host" />(Host)
                        </span>
                    )}
                </p>

                <AvatarPicker
                    choices={gameState.avatar_choices || []}
                    taken={playerList.map(p => p.avatar).filter(Boolean)}
                    mine={gameState.avatar || ''}
                    onChoose={handleChooseAvatar}
                    disabled={!connected}
                />

                {toastMessage && (
                    <div className="toast-notification">{toastMessage}</div>
                )}

                <h3 className="lobby-players-heading">Players ({playerList.length})</h3>
                <ul className="player-list">
                    {playerList.map((player, idx) => (
                        <li key={player.uuid || idx} className={player.uuid === player_uuid ? 'is-you' : ''}>
                            <Avatar player={player} />
                            {' '}{player.name}
                            {player.uuid === gameState.host_uuid && (
                                <Icon emoji={ROLE_EMOJI.HOST} label="Host" />
                            )}
                            {player.uuid === player_uuid && (
                                <>{' (you)'}<Icon emoji={ROLE_EMOJI.YOU} label="You" /></>
                            )}
                        </li>
                    ))}
                </ul>

                {/* Shown to everyone, changeable by the host. A player deciding
                    whether to stay needs to know what game this is, and the
                    rules stop moving once the cards are dealt. */}
                <h3 className="lobby-players-heading">House Rules</h3>
                <ul className="settings-list">
                    {GAME_SETTINGS.map(setting => (
                        <li key={setting.key}>
                            <label className={isHost ? 'setting' : 'setting is-readonly'}>
                                <input
                                    type="checkbox"
                                    checked={Boolean(settings[setting.key])}
                                    disabled={!isHost || !connected}
                                    onChange={() => handleToggleSetting(setting.key)}
                                />
                                <span>
                                    <strong>{setting.label}</strong>
                                    <span className="setting-description">{setting.description}</span>
                                </span>
                            </label>
                        </li>
                    ))}
                </ul>
                {!isHost && (
                    <p className="lobby-hint">Only the host can change these.</p>
                )}

                {isHost && !canStart && (
                    <p className="lobby-status">Waiting for more players (need at least {MIN_PLAYERS})...</p>
                )}

                {canStart && (
                    <button onClick={handleStartGame} className="btn btn-primary" disabled={!connected}>
                        Start Game
                    </button>
                )}

                {!isHost && (
                    <p className="lobby-status">
                        {hostName
                            ? `Waiting for host (${hostName}) to start the game...`
                            : 'Waiting for host to start the game...'}
                    </p>
                )}
            </div>
        </div>
    );
}

export default Lobby;
