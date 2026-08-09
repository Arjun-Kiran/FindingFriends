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
  // Explains on the home screen why a session was dropped, when it wasn't the
  // user's own choice to leave.
  const [sessionNotice, setSessionNotice] = useState('');
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
        .catch(err => {
          // Only drop the session when the server says the game or player is
          // gone. An unreachable server is likely a restart in progress, and
          // the session is still worth keeping.
          if (err.isMissing) {
            clearSession('That game has ended. Start or join a new one.');
          } else {
            setSessionNotice(err.message || 'Could not reach the server.');
          }
        });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const updateSessionInfo = (key, new_value) => {
    setSessionInfo(prev => ({...prev, [key]: new_value}));
  };

  /* Forget the saved session and return to the home screen. `notice` is shown
   * there when the reset wasn't the user's own doing. */
  const clearSession = (notice = '') => {
    localStorage.removeItem('findingFriendsSession');
    setSessionInfo({ game_code: '', user_name: '', user_uuid: '', game_link: '', host: false });
    setGameStarted(false);
    setLobby(false);
    setInitialGameState(null);
    socketRef.current = null;
    setSessionNotice(notice);
  };

  /* The server told us this session no longer exists — most often because the
   * backend restarted while this tab still had the game open. */
  const handleSessionInvalid = (data) => {
    clearSession((data && data.message) || 'This game session is no longer available.');
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
    clearSession();
  };

  if (gameStarted) {
    return (
      <div className="App">
        <Game
          sessionInfo={sessionInfo}
          initialGameState={initialGameState}
          socket={socketRef.current}
          onLeaveGame={handleLeaveGame}
          onSessionInvalid={handleSessionInvalid}
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
          onSessionInvalid={handleSessionInvalid}
        />
      </div>
    );
  }

  return (
    <div className="App">
      <div className="home-screen">
        <h1 className="home-title">Finding Friends</h1>
        <p className="home-subtitle">Zhao Pengyou &middot; 找朋友</p>
        {sessionNotice && (
          <div className="info-panel error home-notice">
            <span>{sessionNotice}</span>
            <button className="close-btn" onClick={() => setSessionNotice('')}>✕</button>
          </div>
        )}
        <CreateGame updateSessionInfo={updateSessionInfo} updateLobby={updateInLobby} />
        <JoinGame updateSessionInfo={updateSessionInfo} updateLobby={updateInLobby} />
      </div>
    </div>
  );
}

export default App;
