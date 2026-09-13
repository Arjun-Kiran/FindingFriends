import { useState, useRef, useEffect } from 'react';

import { fetchPlayerView } from './api/client';
import { logger } from './api/logger';
import { PHASE } from './constants/phases';
import CreateGame from './components/CreateGame';
import Lobby from './components/Lobby';
import JoinGame from './components/JoinGame';
import Game from './components/Game/Game';
import './App.css';

/* `player_token` is the seat's secret: the server takes it as proof of who this
 * is. `user_uuid` is public — every player sees it — and only says which seat
 * on screen is ours. */
const EMPTY_SESSION = { game_code: '', user_name: '', user_uuid: '', player_token: '', game_link: '', host: false };

function App() {
  const [sessionInfo, setSessionInfo] = useState(() => {
    // Restore session from localStorage on page load
    const saved = localStorage.getItem('findingFriendsSession');
    if (saved) {
      try {
        const session = JSON.parse(saved);
        /* Saved before seats had tokens. The server no longer accepts a bare
         * uuid as proof of who you are, so there is nothing left to restore. */
        if (session.player_token) return session;
        localStorage.removeItem('findingFriendsSession');
      } catch {}
    }
    return EMPTY_SESSION;
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
    if (sessionInfo.game_code && sessionInfo.player_token) {
      localStorage.setItem('findingFriendsSession', JSON.stringify(sessionInfo));
    }
  }, [sessionInfo]);

  // Auto-rejoin: if we have session info on mount, try to fetch current game state
  useEffect(() => {
    if (sessionInfo.game_code && sessionInfo.player_token && !inLobby && !gameStarted) {
      fetchPlayerView(sessionInfo.game_code, sessionInfo.player_token)
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
            logger.info('saved session is gone, returning to the home screen');
            clearSession('That game has ended. Start or join a new one.');
          } else {
            logger.warn('could not restore the saved session:', err.message);
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
    setSessionInfo(EMPTY_SESSION);
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
        {/* A late arrival goes straight to the game with no socket to hand
            over, so Game opens its own — see JoinGame's watchInstead. */}
        <JoinGame
          updateSessionInfo={updateSessionInfo}
          updateLobby={updateInLobby}
          enterGame={(view) => handleGameStarted(view, null)}
        />
      </div>
    </div>
  );
}

export default App;
