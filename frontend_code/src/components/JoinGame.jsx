import { useState } from "react";
import { fetchPlayerView, joinGame, watchGame } from "../api/client";
import { PHASE } from "../constants/phases";

const JoinGame = (props) => {
    const [nickName, setNickName] = useState('');
    const [gameCode, setGameCode] = useState('');
    const [error, setError] = useState('');

    /* Save who this is, then go — to the lobby unless told otherwise. */
    const enter = ({ uuid, token, link = '' }, go = () => props.updateLobby(true)) => {
        props.updateSessionInfo('game_code', gameCode);
        props.updateSessionInfo('user_name', nickName);
        props.updateSessionInfo('user_uuid', uuid);
        props.updateSessionInfo('player_token', token);
        props.updateSessionInfo('game_link', link);
        props.updateSessionInfo('host', false);
        go();
    };

    const missingGame = 'No game with that code. Check the game code.';

    /* A game already under way has no seat to give, so whoever arrives late
     * watches it instead (HR-8) — and from there can ask the host for a seat.
     * No separate button: the player asked to join this game, and watching is
     * the only way into it right now. */
    const watchInstead = async () => {
        let watcher;
        try {
            watcher = await watchGame(gameCode, nickName);
        } catch (err) {
            if (err.isMissing) {
                setError(missingGame);
            } else if (err.code === 'game_over') {
                setError('That game is over.');
            } else {
                setError(err.message || 'Failed to join game');
            }
            return;
        }
        const session = { uuid: watcher.watcher_uuid, token: watcher.player_token };

        /* Straight to the board, not through the lobby. The game is under way
         * — that is why the join was refused — so the lobby would only show a
         * waiting room for a game that has already started, until its socket
         * caught up and handed over. The view is fetched first so the board
         * is drawn complete rather than empty; the game opens its own socket,
         * as it does when a page is reloaded mid-game. */
        try {
            const view = await fetchPlayerView(gameCode, watcher.player_token);
            if (props.enterGame && view.game_event_state !== PHASE.WAITING_FOR_PLAYERS) {
                enter(session, () => props.enterGame(view));
                return;
            }
        } catch {
            // The lobby fetches for itself, and hands over the moment its
            // socket says the game is on, so it is still a way in.
        }
        enter(session);
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
