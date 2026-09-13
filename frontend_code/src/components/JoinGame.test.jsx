import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import JoinGame from './JoinGame';
import { fetchPlayerView, joinGame, watchGame } from '../api/client';
import { playerView } from '../test-utils/playerView';

vi.mock('../api/client', () => ({
    fetchPlayerView: vi.fn(),
    joinGame: vi.fn(),
    watchGame: vi.fn(),
}));

const apiError = (message, fields) => Object.assign(new Error(message), { isMissing: false, ...fields });

const submit = () => {
    const updateSessionInfo = vi.fn();
    const updateLobby = vi.fn();
    const enterGame = vi.fn();
    render(<JoinGame updateSessionInfo={updateSessionInfo} updateLobby={updateLobby} enterGame={enterGame} />);
    fireEvent.change(screen.getByLabelText('Game Code'), { target: { value: 'below-adopt-havoc' } });
    fireEvent.change(screen.getByLabelText('Nickname'), { target: { value: 'Wes' } });
    fireEvent.click(screen.getByRole('button', { name: 'Join Game' }));
    return { updateSessionInfo, updateLobby, enterGame };
};

/* The server's refusal when the game has started, and the watch that follows. */
const gameUnderWay = () => {
    joinGame.mockRejectedValue(apiError('Game is not accepting new players', { code: 'game_in_progress' }));
    watchGame.mockResolvedValue({ watcher_uuid: 'uuid-wes', player_token: 'token-wes', nick_name: 'Wes' });
};

beforeEach(() => {
    fetchPlayerView.mockReset();
    joinGame.mockReset();
    watchGame.mockReset();
});

test('a game still in its lobby is joined as a player', async () => {
    joinGame.mockResolvedValue({ new_player_uuid: 'uuid-wes', player_token: 'token-wes', game_link: '/game/x/player' });

    const { updateSessionInfo, updateLobby, enterGame } = submit();

    await waitFor(() => expect(updateLobby).toHaveBeenCalledWith(true));
    expect(updateSessionInfo).toHaveBeenCalledWith('player_token', 'token-wes');
    expect(watchGame).not.toHaveBeenCalled();
    expect(enterGame).not.toHaveBeenCalled();
});

test('a game already under way is watched, straight from the board — not the lobby', async () => {
    gameUnderWay();
    const view = playerView({ game_event_state: 'round-started', is_watcher: true, uuid: 'uuid-wes' });
    fetchPlayerView.mockResolvedValue(view);

    const { updateSessionInfo, updateLobby, enterGame } = submit();

    await waitFor(() => expect(enterGame).toHaveBeenCalledWith(view));
    expect(watchGame).toHaveBeenCalledWith('below-adopt-havoc', 'Wes');
    expect(fetchPlayerView).toHaveBeenCalledWith('below-adopt-havoc', 'token-wes');
    expect(updateSessionInfo).toHaveBeenCalledWith('player_token', 'token-wes');
    expect(updateSessionInfo).toHaveBeenCalledWith('user_uuid', 'uuid-wes');
    expect(updateLobby).not.toHaveBeenCalled();
});

test('still gets in through the lobby if the board cannot be fetched', async () => {
    gameUnderWay();
    fetchPlayerView.mockRejectedValue(apiError('Could not reach the server', { code: 'network_error' }));

    const { updateSessionInfo, updateLobby, enterGame } = submit();

    await waitFor(() => expect(updateLobby).toHaveBeenCalledWith(true));
    expect(updateSessionInfo).toHaveBeenCalledWith('player_token', 'token-wes');
    expect(enterGame).not.toHaveBeenCalled();
});

test('goes to the lobby if the game turns out to be in it after all', async () => {
    gameUnderWay();
    fetchPlayerView.mockResolvedValue(playerView({ game_event_state: 'waiting-for-player-to-join', is_watcher: true }));

    const { updateLobby, enterGame } = submit();

    await waitFor(() => expect(updateLobby).toHaveBeenCalledWith(true));
    expect(enterGame).not.toHaveBeenCalled();
});

test('there is no separate button for watching', () => {
    render(<JoinGame updateSessionInfo={vi.fn()} updateLobby={vi.fn()} enterGame={vi.fn()} />);

    expect(screen.queryByRole('button', { name: 'Watch' })).not.toBeInTheDocument();
});

test('a game that is over says so', async () => {
    joinGame.mockRejectedValue(apiError('Game is not accepting new players', { code: 'game_in_progress' }));
    watchGame.mockRejectedValue(apiError('That game is over', { code: 'game_over' }));

    submit();

    expect(await screen.findByText('That game is over.')).toBeInTheDocument();
});

test('a code that matches no game says so', async () => {
    joinGame.mockRejectedValue(apiError('Game not found', { isMissing: true }));

    submit();

    expect(await screen.findByText('No game with that code. Check the game code.')).toBeInTheDocument();
    expect(watchGame).not.toHaveBeenCalled();
});
