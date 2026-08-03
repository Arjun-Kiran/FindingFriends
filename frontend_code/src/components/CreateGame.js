import { useState } from "react";
import { createGame, joinGame } from "../api/client";

const CreateGame = (props) => {
    const [nickName, setNickName] = useState('');
    const [error, setError] = useState('');

    const onSubmit = async (event) => {
        event.preventDefault();
        setError('');

        if (!nickName.trim()) {
            setError('Please enter a nickname');
            return;
        }

        try {
            const { game_code } = await createGame();
            const player = await joinGame(game_code, nickName);

            props.updateSessionInfo('game_code', game_code);
            props.updateSessionInfo('user_name', nickName);
            props.updateSessionInfo('user_uuid', player.new_player_uuid);
            props.updateSessionInfo('game_link', player.game_link);
            props.updateSessionInfo('host', true);
            props.updateLobby(true);
        } catch (err) {
            setError(err.message || 'Failed to create game');
        }
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
