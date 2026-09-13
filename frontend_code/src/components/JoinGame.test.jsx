import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import JoinGame from './JoinGame';
import { joinGame, watchGame } from '../api/client';

vi.mock('../api/client', () => ({
    joinGame: vi.fn(),
    watchGame: vi.fn(),
}));

const apiError = (message, fields) => Object.assign(new Error(message), { isMissing: false, ...fields });

const submit = () => {
    const updateSessionInfo = vi.fn();
    const updateLobby = vi.fn();
    render(<JoinGame updateSessionInfo={updateSessionInfo} updateLobby={updateLobby} />);
    fireEvent.change(screen.getByLabelText('Game Code'), { target: { value: 'below-adopt-havoc' } });
    fireEvent.change(screen.getByLabelText('Nickname'), { target: { value: 'Wes' } });
    fireEvent.click(screen.getByRole('button', { name: 'Join Game' }));
    return { updateSessionInfo, updateLobby };
};

beforeEach(() => {
    joinGame.mockReset();
    watchGame.mockReset();
});

test('a game still in its lobby is joined as a player', async () => {
    joinGame.mockResolvedValue({ new_player_uuid: 'uuid-wes', player_token: 'token-wes', game_link: '/game/x/player' });

    const { updateSessionInfo, updateLobby } = submit();

    await waitFor(() => expect(updateLobby).toHaveBeenCalledWith(true));
    expect(updateSessionInfo).toHaveBeenCalledWith('player_token', 'token-wes');
    expect(watchGame).not.toHaveBeenCalled();
});

test('a game already under way is watched instead, with no second step', async () => {
    joinGame.mockRejectedValue(apiError('Game is not accepting new players', { code: 'game_in_progress' }));
    watchGame.mockResolvedValue({ watcher_uuid: 'uuid-wes', player_token: 'token-wes', nick_name: 'Wes' });

    const { updateSessionInfo, updateLobby } = submit();

    await waitFor(() => expect(updateLobby).toHaveBeenCalledWith(true));
    expect(watchGame).toHaveBeenCalledWith('below-adopt-havoc', 'Wes');
    expect(updateSessionInfo).toHaveBeenCalledWith('player_token', 'token-wes');
    expect(updateSessionInfo).toHaveBeenCalledWith('user_uuid', 'uuid-wes');
});

test('there is no separate button for watching', () => {
    render(<JoinGame updateSessionInfo={vi.fn()} updateLobby={vi.fn()} />);

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
