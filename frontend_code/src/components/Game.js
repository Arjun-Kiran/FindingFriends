import React from "react";

const Game = (props) => {
    if(props.gameStarted){
        return (
            <div>
                <p>Game Component Here</p>
            </div>
        )
    }
    return <div></div>
}


export default Game;