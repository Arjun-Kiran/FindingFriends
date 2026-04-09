import { useEffect, useState, useRef } from "react";
import { io } from "socket.io-client";

const Lobby = (props) => {
    const [gameState, setGameState] = useState({});
    const [errorMessage, setErrorMessage] = useState('');
    const socketRef = useRef(null);
    const handedOffToGame = useRef(false);

    const game_code = props.sessionInfo['game_code'];
    const player_uuid = props.sessionInfo['user_uuid'];
    const isHost = props.sessionInfo['host'];

    useEffect(() => {
        const socket = io("http://127.0.0.1:5050", {
            transports: ["websocket"],
        });

        socketRef.current = socket;

        socket.on("connect", () => {
            console.log("connected to websocket");
            socket.emit('join', { game_code: game_code, player_uuid: player_uuid });
        });

        socket.on('game_stats', (data) => {
            console.log('received game_stats', data);
            setGameState(data);
            if (data.game_event_state && data.game_event_state !== 'waiting-for-player-to-join') {
                if (props.onGameStarted) {
                    handedOffToGame.current = true;
                    props.onGameStarted(data, socket);
                }
            }
        });

        socket.on("disconnect", () => {
            console.log("Disconnected from websocket");
        });

        socket.on("error", (data) => {
            console.error("Socket error:", data);
            setErrorMessage(data.message || 'An error occurred');
        });

        return function cleanup() {
            // Don't disconnect if the socket was handed off to Game component
            if (!handedOffToGame.current) {
                socket.disconnect();
            }
        };
    }, [game_code, player_uuid]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        fetch('/game/' + game_code + '/player/' + player_uuid)
            .then(res => res.json())
            .then(data => setGameState(data))
            .catch(err => console.error('Failed to fetch game state:', err));
    }, [game_code, player_uuid]);

    const handleStartGame = () => {
        if (socketRef.current) {
            socketRef.current.emit('start_game', {
                game_code: game_code,
                player_uuid: player_uuid
            });
        }
    };

    const playerList = gameState.player_list || [];
    const canStart = isHost && gameState.can_start_game;

    return (
        <div className="lobby-container">
            <div className="lobby-card">
                {errorMessage && (
                    <div className="info-panel error" style={{ marginBottom: '16px' }}>
                        <span>{errorMessage}</span>
                        <button className="close-btn" onClick={() => setErrorMessage('')}>✕</button>
                    </div>
                )}

                <h2>Game Lobby</h2>
                <div className="game-code-display">{game_code}</div>
                <p style={{ fontSize: '0.9rem', color: '#7f8c8d' }}>
                    Share this code with friends to join
                </p>

                <p style={{ fontSize: '0.95rem' }}>
                    Playing as <strong>{gameState.name}</strong>
                    {isHost && <span style={{ color: '#e67e22' }}> (Host)</span>}
                </p>

                <h3 style={{ marginBottom: '8px' }}>Players ({playerList.length})</h3>
                <ul className="player-list">
                    {playerList.map((player, idx) => (
                        <li key={player.uuid || idx} className={player.uuid === player_uuid ? 'is-you' : ''}>
                            {player.name}
                            {player.uuid === player_uuid && ' (you)'}
                        </li>
                    ))}
                </ul>

                {isHost && !canStart && (
                    <p className="lobby-status">Waiting for more players (need at least 5)...</p>
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
