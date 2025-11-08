import React, { useEffect, useState } from "react";
import { io } from "socket.io-client";

const Lobby = (props) => {

    const [game_code, setGameCode] = useState(props.sessionInfo['game_code']);
    const [gameState, setGameState] = useState({});

    const grabInfoFromServer = (game_code, user_uuid) => {
        fetch('/game/' + game_code + '/player/'+user_uuid).then((res) => 
        res.json().then((data)=> {
            setGameState(data);
        })
        );
    };
    
    useEffect(() => {
    console.log('Trying to connect')
    const socket = io("http://127.0.0.1:5000", {
        transports: ["polling"],
        cors: {
          origin: "http://localhost:3000/",
        },
      });

      socket.on("connect", (data) => {
        console.log("connected to websocket")
        console.log(data);
        socket.send('User connected')
      });

      socket.on("disconnect", (data) => {
        console.log("Disconnected from websocket")
        console.log(data);
      });

      return function cleanup() {
        socket.disconnect();
      };

    },[]);
    
    useEffect(() => {
        grabInfoFromServer(props.sessionInfo['game_code'], props.sessionInfo['user_uuid']);
    },[]);

    console.log(gameState);
    return (
        <div>
            <p>Lobby Component Here</p>
            <p>Name: {gameState["name"]}</p>
            <p>UUID: {gameState["uuid"]}</p>
            <p>Game Code: { game_code }</p>
            <p>Hosting: {gameState.hosting ? "Yes" : "No" }</p>
            <p>Number of Players: {gameState.number_of_players}</p>
        </div>
    )
}


export default Lobby;