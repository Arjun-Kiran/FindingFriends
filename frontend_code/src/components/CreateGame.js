import React, { useState } from "react";

const CreateGame = (props) => {

    const [nickName, setNickName] = useState('');

    const [gameInfo, setGameInfo] = useState({
        'game_code': '',
        'join_link': ''
    });

    const onChangeNickName = (event) => {
        setNickName(event.target.value);
    }

    const joinGame = (game_code, nickName) => {
        fetch('/join/' +game_code + '?nick_name='+nickName).then((res) => 
            res.json().then((data)=> {
                props.updateSessionInfo('game_code', game_code);
                props.updateSessionInfo('user_name', nickName);
                props.updateSessionInfo('user_uuid', data.new_player_uuid);
                props.updateSessionInfo('game_link', data.game_link);
                props.updateSessionInfo('host', true);
                props.updateLobby(true);
            })
        );
    }


    const onSubmit = (event) => {
        event.preventDefault();
        fetch("/create").then((res) =>{
            res.json().then((data) => {
                console.log(data)
                joinGame(data.game_code, nickName)
                setGameInfo({
                    game_code: data.game_code,
                    join_link: data.link,
                });
            })
        });

    }

    return (
        <div>
            <form onSubmit={onSubmit}>
            <p>Create Game</p>
            <label htmlFor="nick_name">NickName:</label>
            <input type="text" id="nick_name" name="nick_name" onChange={(e) => onChangeNickName(e)} />
            <br/>
            <input type="submit" value="Submit" />
            </form>
        </div>
    )
}


export default CreateGame;