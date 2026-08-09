import { useState } from "react";
import { joinGame } from "../api/client";

const JoinGame = (props) => {
    const [nickName, setNickName] = useState('');
    const [gameCode, setGameCode] = useState('');
    const [error, setError] = useState('');

    const onSubmit = async (event) => {
        event.preventDefault();
        setError('');

        if (!gameCode.trim() || !nickName.trim()) {
            setError('Please enter both a game code and nickname');
            return;
        }

        try {
            const player = await joinGame(gameCode, nickName);

            props.updateSessionInfo('game_code', gameCode);
            props.updateSessionInfo('user_name', nickName);
            props.updateSessionInfo('user_uuid', player.new_player_uuid);
            props.updateSessionInfo('game_link', player.game_link);
            props.updateSessionInfo('host', false);
            props.updateLobby(true);
        } catch (err) {
            setError(err.isMissing
                ? 'No game with that code. Check the game code.'
                : (err.message || 'Failed to join game'));
        }
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
