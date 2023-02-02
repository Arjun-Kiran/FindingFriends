import React, { useEffect, useState } from "react";

const Lobby = (props) => {

    const [game_code, setGameCode] = useState(props.sessionInfo['game_code']);
    const [gameState, setGameState] = useState({});

    const grabInfoFromServer = (game_code, user_uuid) => {
        fetch('/game/' +game_code + '/player/'+user_uuid).then((res) => 
        res.json().then((data)=> {
            setGameState(data);
        })
        );
    };
    
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