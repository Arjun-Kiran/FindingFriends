import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import JoinGame from './JoinGame';
import { joinGame, watchGame } from '../api/client';

vi.mock('../api/client', () => ({
    joinGame: vi.fn(),
    watchGame: vi.fn(),
}));

const renderForm = () => {
    const updateSessionInfo = vi.fn();
    const updateLobby = vi.fn();
    render(<JoinGame updateSessionInfo={updateSessionInfo} updateLobby={updateLobby} />);
    fireEvent.change(screen.getByLabelText('Game Code'), { target: { value: 'below-adopt-havoc' } });
    fireEvent.change(screen.getByLabelText('Nickname'), { target: { value: 'Wes' } });
    return { updateSessionInfo, updateLobby };
};

beforeEach(() => {
    joinGame.mockReset();
    watchGame.mockReset();
});

test('watching keeps the token it is given and heads for the game', async () => {
    watchGame.mockResolvedValue({ watcher_uuid: 'uuid-wes', player_token: 'token-wes', nick_name: 'Wes' });
    const { updateSessionInfo, updateLobby } = renderForm();

    fireEvent.click(screen.getByRole('button', { name: 'Watch' }));

    await waitFor(() => expect(updateLobby).toHaveBeenCalledWith(true));
    expect(watchGame).toHaveBeenCalledWith('below-adopt-havoc', 'Wes');
    expect(updateSessionInfo).toHaveBeenCalledWith('player_token', 'token-wes');
    expect(updateSessionInfo).toHaveBeenCalledWith('user_uuid', 'uuid-wes');
    expect(joinGame).not.toHaveBeenCalled();
});

test('a game already under way suggests watching it instead', async () => {
    joinGame.mockRejectedValue(Object.assign(new Error('Game is not accepting new players'), {
        code: 'game_in_progress',
        isMissing: false,
    }));
    renderForm();

    fireEvent.click(screen.getByRole('button', { name: 'Join Game' }));

    expect(await screen.findByText(/You can watch it instead/)).toBeInTheDocument();
});

test('watching needs a code and a name too', () => {
    render(<JoinGame updateSessionInfo={vi.fn()} updateLobby={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Watch' }));

    expect(screen.getByText('Please enter both a game code and nickname')).toBeInTheDocument();
    expect(watchGame).not.toHaveBeenCalled();
});
