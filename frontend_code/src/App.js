import { useState, useRef, useEffect } from 'react';

import { fetchPlayerView } from './api/client';
import { PHASE } from './constants/phases';
import CreateGame from './components/CreateGame';
import Lobby from './components/Lobby';
import JoinGame from './components/JoinGame';
import Game from './components/Game/Game';
import './App.css';

function App() {
  const [sessionInfo, setSessionInfo] = useState(() => {
    // Restore session from localStorage on page load
    const saved = localStorage.getItem('findingFriendsSession');
    if (saved) {
      try { return JSON.parse(saved); } catch {}
    }
    return { game_code: '', user_name: '', user_uuid: '', game_link: '', host: false };
  });

  const [gameStarted, setGameStarted] = useState(false);
  const [inLobby, setLobby] = useState(false);
  const [initialGameState, setInitialGameState] = useState(null);
  const socketRef = useRef(null);

  // Persist session info to localStorage
  useEffect(() => {
    if (sessionInfo.game_code && sessionInfo.user_uuid) {
      localStorage.setItem('findingFriendsSession', JSON.stringify(sessionInfo));
    }
  }, [sessionInfo]);

  // Auto-rejoin: if we have session info on mount, try to fetch current game state
  useEffect(() => {
    if (sessionInfo.game_code && sessionInfo.user_uuid && !inLobby && !gameStarted) {
      fetchPlayerView(sessionInfo.game_code, sessionInfo.user_uuid)
        .then(data => {
          if (data.game_event_state && data.game_event_state !== PHASE.WAITING_FOR_PLAYERS) {
            // Game is in progress, go straight to Game
            setInitialGameState(data);
            setGameStarted(true);
          } else if (data.game_event_state) {
            // Still in lobby
            setLobby(true);
          }
        })
        .catch(() => {
          // Game or player no longer exists, clear saved session
          localStorage.removeItem('findingFriendsSession');
          setSessionInfo({ game_code: '', user_name: '', user_uuid: '', game_link: '', host: false });
        });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const updateSessionInfo = (key, new_value) => {
    setSessionInfo(prev => ({...prev, [key]: new_value}));
  };

  const updateInLobby = (lobby) => {
    setLobby(lobby);
  };

  const handleGameStarted = (gameStateData, socket) => {
    setInitialGameState(gameStateData);
    socketRef.current = socket;
    setGameStarted(true);
  };

  const handleLeaveGame = () => {
    localStorage.removeItem('findingFriendsSession');
    setSessionInfo({ game_code: '', user_name: '', user_uuid: '', game_link: '', host: false });
    setGameStarted(false);
    setLobby(false);
    setInitialGameState(null);
    socketRef.current = null;
  };

  if (gameStarted) {
    return (
      <div className="App">
        <Game
          sessionInfo={sessionInfo}
          initialGameState={initialGameState}
          socket={socketRef.current}
          onLeaveGame={handleLeaveGame}
        />
      </div>
    );
  }

  if (inLobby) {
    return (
      <div className="App">
        <Lobby
          sessionInfo={sessionInfo}
          onGameStarted={handleGameStarted}
          onLeaveGame={handleLeaveGame}
        />
      </div>
    );
  }

  return (
    <div className="App">
      <div className="home-screen">
        <h1 className="home-title">Finding Friends</h1>
        <p className="home-subtitle">Zhao Pengyou &middot; 找朋友</p>
        <CreateGame updateSessionInfo={updateSessionInfo} updateLobby={updateInLobby} />
        <JoinGame updateSessionInfo={updateSessionInfo} updateLobby={updateInLobby} />
      </div>
    </div>
  );
}

export default App;
