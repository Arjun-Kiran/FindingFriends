import React, { useState } from "react";


const JoinGame = (props) => {

    const [inputUserID, setInputUserID] = useState('');
    const [inputGameCode, setInputGameCode] = useState('');

    const onChangeGameCodeInput = (event) => {
        setInputGameCode(event.target.value);
        return true;
    }

    const onChangeUserIdInput = (event) => {
        setInputUserID(event.target.value);
        return true;
    }

    const formSubmitHandler = (event) => {
        event.preventDefault();
        props.updateGameCode(inputGameCode);
        props.updateUserId(inputUserID);
        props.updateLobby(true);
        console.log("Game Code: " + inputGameCode);
        console.log("User Id: " + inputUserID);
        return true;
    }

    return (
        <div>
            <form onSubmit={formSubmitHandler}>
            <p>Join Existing Game</p>
            <label htmlFor="gamecode">Game Code:</label>
            <input type="text" id="gamecode" name="gamecode" value={inputGameCode} onChange={(e) => onChangeGameCodeInput(e)} />
            <br/>
            <label htmlFor="nick_name">NickName:</label>
            <input type="text" id="nick_name" name="nick_name" value={inputUserID} onChange={(e) => onChangeUserIdInput(e)} />
            <br/>
            <input type="submit" value="Submit" />
            </form>
        </div>
    )
}

export default JoinGame;