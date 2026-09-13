import { useState } from "react";
import { joinGame, watchGame } from "../api/client";

const JoinGame = (props) => {
    const [nickName, setNickName] = useState('');
    const [gameCode, setGameCode] = useState('');
    const [error, setError] = useState('');

    /* Both ways in land in the lobby, which hands over to the game as soon as
     * the server says one is under way. */
    const enter = ({ uuid, token, link = '' }) => {
        props.updateSessionInfo('game_code', gameCode);
        props.updateSessionInfo('user_name', nickName);
        props.updateSessionInfo('user_uuid', uuid);
        props.updateSessionInfo('player_token', token);
        props.updateSessionInfo('game_link', link);
        props.updateSessionInfo('host', false);
        props.updateLobby(true);
    };

    const filledIn = () => {
        if (!gameCode.trim() || !nickName.trim()) {
            setError('Please enter both a game code and nickname');
            return false;
        }
        return true;
    };

    const onSubmit = async (event) => {
        event.preventDefault();
        setError('');
        if (!filledIn()) return;

        try {
            const player = await joinGame(gameCode, nickName);
            enter({ uuid: player.new_player_uuid, token: player.player_token, link: player.game_link });
        } catch (err) {
            if (err.isMissing) {
                setError('No game with that code. Check the game code.');
            } else if (err.code === 'game_in_progress') {
                // The one way in that still works mid-game (HR-8).
                setError('That game has already started. You can watch it instead, and ask the host for a seat.');
            } else {
                setError(err.message || 'Failed to join game');
            }
        }
    }

    const onWatch = async () => {
        setError('');
        if (!filledIn()) return;

        try {
            const watcher = await watchGame(gameCode, nickName);
            enter({ uuid: watcher.watcher_uuid, token: watcher.player_token });
        } catch (err) {
            setError(err.isMissing
                ? 'No game with that code. Check the game code.'
                : (err.message || 'Failed to watch game'));
        }
    };

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
                <button type="button" className="btn btn-secondary" onClick={onWatch}>Watch</button>
            </form>
            {error && <p className="error-text">{error}</p>}
        </div>
    );
}

export default JoinGame;
