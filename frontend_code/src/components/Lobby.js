import React from "react";

const Lobby = (props) => {
    if(props.inLobby){
        return (
            <div>
                <p>Lobby Component Here</p>
            </div>
        )
    }

    return <div></div>
}


export default Lobby;