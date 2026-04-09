import { useState } from "react";

const CreateGame = (props) => {
    const [nickName, setNickName] = useState('');
    const [error, setError] = useState('');

    const joinGame = (game_code, nickName) => {
        fetch('/join/' + game_code + '?nick_name=' + nickName).then((res) =>
            res.json().then((data) => {
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
        setError('');
        if (!nickName.trim()) {
            setError('Please enter a nickname');
            return;
        }
        fetch("/create").then((res) => {
            if (!res.ok) throw new Error('Failed to create game');
            res.json().then((data) => {
                joinGame(data.game_code, nickName);
            })
        }).catch(err => setError(err.message || 'Failed to create game'));
    }

    return (
        <div className="form-card">
            <h3>Create New Game</h3>
            <form onSubmit={onSubmit}>
                <label htmlFor="create_nick">Nickname</label>
                <input
                    type="text"
                    id="create_nick"
                    name="nick_name"
                    value={nickName}
                    onChange={(e) => setNickName(e.target.value)}
                    placeholder="Enter your name"
                />
                <button type="submit" className="btn btn-primary">Create Game</button>
            </form>
            {error && <p className="error-text">{error}</p>}
        </div>
    );
}

export default CreateGame;
