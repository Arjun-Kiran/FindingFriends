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

    const missingGame = 'No game with that code. Check the game code.';

    /* A game already under way has no seat to give, so whoever arrives late
     * watches it instead (HR-8) — and from there can ask the host for a seat.
     * No separate button: the player asked to join this game, and watching is
     * the only way into it right now. */
    const watchInstead = async () => {
        try {
            const watcher = await watchGame(gameCode, nickName);
            enter({ uuid: watcher.watcher_uuid, token: watcher.player_token });
        } catch (err) {
            if (err.isMissing) {
                setError(missingGame);
            } else if (err.code === 'game_over') {
                setError('That game is over.');
            } else {
                setError(err.message || 'Failed to join game');
            }
        }
    };

    const onSubmit = async (event) => {
        event.preventDefault();
        setError('');

        if (!gameCode.trim() || !nickName.trim()) {
            setError('Please enter both a game code and nickname');
            return;
        }

        try {
            const player = await joinGame(gameCode, nickName);
            enter({ uuid: player.new_player_uuid, token: player.player_token, link: player.game_link });
        } catch (err) {
            if (err.isMissing) {
                setError(missingGame);
            } else if (err.code === 'game_in_progress') {
                await watchInstead();
            } else {
                setError(err.message || 'Failed to join game');
            }
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
