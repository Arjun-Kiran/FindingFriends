import { useState } from "react";

const JoinGame = (props) => {
    const [nickName, setNickName] = useState('');
    const [gameCode, setGameCode] = useState('');
    const [error, setError] = useState('');

    const joinGame = (game_code, nick_name) => {
        setError('');
        fetch('/join/' + game_code + '?nick_name=' + nick_name).then((res) => {
            if (!res.ok) throw new Error('Failed to join game. Check the game code.');
            res.json().then((data) => {
                props.updateSessionInfo('game_code', game_code);
                props.updateSessionInfo('user_name', nick_name);
                props.updateSessionInfo('user_uuid', data.new_player_uuid);
                props.updateSessionInfo('game_link', data.game_link);
                props.updateSessionInfo('host', false);
                props.updateLobby(true);
            })
        }).catch(err => setError(err.message || 'Failed to join game'));
    }

    const onSubmit = (event) => {
        event.preventDefault();
        if (!gameCode.trim() || !nickName.trim()) {
            setError('Please enter both a game code and nickname');
            return;
        }
        joinGame(gameCode, nickName);
    }

    return (
        <div className="form-card">
            <h3>Join Existing Game</h3>
            <form onSubmit={onSubmit}>
                <label htmlFor="join_gamecode">Game Code</label>
                <input
                    type="text"
                    id="join_gamecode"
                    name="gamecode"
                    value={gameCode}
                    onChange={(e) => setGameCode(e.target.value)}
                    placeholder="e.g. apple-banana-cherry"
                />
                <label htmlFor="join_nick">Nickname</label>
                <input
                    type="text"
                    id="join_nick"
                    name="nick_name"
                    value={nickName}
                    onChange={(e) => setNickName(e.target.value)}
                    placeholder="Enter your name"
                />
                <button type="submit" className="btn btn-primary">Join Game</button>
            </form>
            {error && <p className="error-text">{error}</p>}
        </div>
    );
}

export default JoinGame;
