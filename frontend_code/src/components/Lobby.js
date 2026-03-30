import React, { useEffect, useState, useRef } from "react";
import { io } from "socket.io-client";

const Lobby = (props) => {

    const [gameState, setGameState] = useState({});
    const socketRef = useRef(null);

    const game_code = props.sessionInfo['game_code'];
    const player_uuid = props.sessionInfo['user_uuid'];
    const isHost = props.sessionInfo['host'];

    useEffect(() => {
        const socket = io("http://127.0.0.1:5000", {
            transports: ["websocket"],
            cors: {
                origin: "http://localhost:3000",
                methods: ["GET", "POST"]
            },
        });

        socketRef.current = socket;

        socket.on("connect", () => {
            console.log("connected to websocket");
            socket.emit('join', { game_code: game_code, player_uuid: player_uuid });
        });

        socket.on('game_stats', (data) => {
            console.log('received game_stats', data);
            setGameState(data);

            // Transition to game if state has moved past lobby
            if (data.game_event_state && data.game_event_state !== 'waiting-for-player-to-join') {
                if (props.onGameStarted) {
                    props.onGameStarted(data, socket);
                }
            }
        });

        socket.on("disconnect", () => {
            console.log("Disconnected from websocket");
        });

        socket.on("error", (data) => {
            console.error("Socket error:", data);
        });

        return function cleanup() {
            socket.disconnect();
        };

    }, [game_code, player_uuid]);

    // Also fetch initial state via REST
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
        <div style={{ padding: '20px' }}>
            <h2>Game Lobby</h2>
            <p><strong>Game Code:</strong> {game_code}</p>
            <p><strong>Your Name:</strong> {gameState.name}</p>
            <p><strong>Role:</strong> {isHost ? "Host" : "Player"}</p>

            <h3>Players ({playerList.length})</h3>
            <ul>
                {playerList.map((player, idx) => (
                    <li key={player.uuid || idx}>
                        {player.name}
                        {gameState.hosting && player.uuid === player_uuid && " (you, host)"}
                        {!gameState.hosting && player.uuid === player_uuid && " (you)"}
                    </li>
                ))}
            </ul>

            {isHost && !canStart && (
                <p><em>Waiting for more players (need at least 5)...</em></p>
            )}

            {canStart && (
                <button onClick={handleStartGame} style={{ padding: '10px 20px', fontSize: '16px', cursor: 'pointer' }}>
                    Start Game
                </button>
            )}

            {!isHost && (
                <p><em>Waiting for host to start the game...</em></p>
            )}
        </div>
    );
}

export default Lobby;
