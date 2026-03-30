import { useState, useRef } from 'react';

import CreateGame from './components/CreateGame';
import Lobby from './components/Lobby';
import JoinGame from './components/JoinGame';
import Game from './components/Game';
import './App.css';

function App() {
  const [sessionInfo, setSessionInfo] = useState({
    'game_code': '',
    'user_name': '',
    'user_uuid': '',
    'game_link': '',
    'host': false
  })

  const [gameStarted, setGameStarted] = useState(false);
  const [inLobby, setLobby] = useState(false);
  const [initialGameState, setInitialGameState] = useState(null);
  const socketRef = useRef(null);

  const updateSessionInfo = (key, new_value) => {
    setSessionInfo(prev => ({...prev, [key]: new_value}));
  }

  const updateInLobby = (lobby) => {
    setLobby(lobby);
  }

  const handleGameStarted = (gameStateData, socket) => {
    setInitialGameState(gameStateData);
    socketRef.current = socket;
    setGameStarted(true);
  }

  if (gameStarted) {
    return (
      <div className="App">
        <Game
          sessionInfo={sessionInfo}
          initialGameState={initialGameState}
          socket={socketRef.current}
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
        />
      </div>
    );
  }

  return (
    <div className="App">
      <CreateGame updateSessionInfo={updateSessionInfo} updateLobby={updateInLobby} />
      <JoinGame updateSessionInfo={updateSessionInfo} updateLobby={updateInLobby} />
    </div>
  );
}

export default App;
