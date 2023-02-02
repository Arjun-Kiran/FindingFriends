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

    const joinGame = (game_code, nick_name) => {
        fetch('/join/' +game_code + '?nick_name='+nick_name).then((res) => 
            res.json().then((data)=> {
                props.updateSessionInfo('game_code', game_code);
                props.updateSessionInfo('user_name', nick_name);
                props.updateSessionInfo('user_uuid', data.new_player_uuid);
                props.updateSessionInfo('game_link', data.game_link);
                props.updateSessionInfo('host', true);
                props.updateLobby(true);
            })
        );
    }


    const formSubmitHandler = (event) => {
        event.preventDefault();
        joinGame(inputGameCode, inputUserID);
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