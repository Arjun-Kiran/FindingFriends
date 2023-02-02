import React, { useState } from 'react';

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

  const [gameCode, setGameCode] = useState('');
  const [userId, setUserId] = useState('')
  const [gameStarted, setGameStarted] = useState(false);
  const [inLobby, setLobby] = useState(false);

  const updateGameCode = (newGameCode) => {
    console.log("Updating the game code.");
    setGameCode(newGameCode);
  }

  const updateSessionInfo = (key, new_value) => {
    let session = sessionInfo;
    session[key]= new_value;
    setSessionInfo(session);
  }

  const updateUserId = (newUserID) => {
    console.log("Updating the user id.");
    setUserId(newUserID);
  }

  const updateGameStarted = (started) => {
    console.log("Updated the game state.");
    setGameStarted(started);
  }

  const updateInLobby = (lobby) => {
    console.log("Updated the lobby state")
    setLobby(lobby);
  }

  if (gameStarted === false && inLobby === false){
    return (
        <div className="App">
          <CreateGame updateSessionInfo={updateSessionInfo} updateLobby={updateInLobby} />
          <JoinGame updateSessionInfo={updateSessionInfo} updateLobby={updateInLobby} />
        </div>
    );
  } else if (inLobby){
    return (
      <div className="App">
        <Lobby gameStarted={gameStarted} inLobby={inLobby} sessionInfo={sessionInfo} />
      </div>
    );
  }

  return (
    <div className="App">
      <Game gameStarted={gameStarted} gameCode={gameCode} userID={userId} />
    </div>
  );
}

export default App;
