import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import App from './App';
import { createMockSocket } from './test-utils/mockSocket';
import { playerView } from './test-utils/playerView';

vi.mock('./api/socket', () => ({
    SERVER_URL: 'http://127.0.0.1:5050',
    SERVER_LABEL: 'http://127.0.0.1:5050',
    createSocket: () => createMockSocket(),
}));

const jsonResponse = (status, body) => Promise.resolve({
    ok: status < 400,
    status,
    json: () => Promise.resolve(body),
});

test('joining a game already under way lands on the board as a watcher, never the lobby', async () => {
    global.fetch = vi.fn((path) => {
        if (path.startsWith('/join/')) {
            return jsonResponse(409, { error: 'game_in_progress', message: 'Game is not accepting new players' });
        }
        if (path.startsWith('/watch/')) {
            return jsonResponse(200, { watcher_uuid: 'uuid-wes', player_token: 'token-wes', nick_name: 'Wes' });
        }
        return jsonResponse(200, playerView({
            game_event_state: 'round-started', is_watcher: true, uuid: 'uuid-wes', name: 'Wes',
        }));
    });
    render(<App />);
    // The home screen has two nickname fields — creating a game has one too.
    const joinForm = within(screen.getByRole('heading', { name: 'Join Existing Game' }).closest('.form-card'));

    fireEvent.change(joinForm.getByLabelText('Game Code'), { target: { value: 'below-adopt-havoc' } });
    fireEvent.change(joinForm.getByLabelText('Nickname'), { target: { value: 'Wes' } });
    fireEvent.click(joinForm.getByRole('button', { name: 'Join Game' }));

    expect(await screen.findByRole('heading', { name: /You are watching/ })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Game Lobby' })).not.toBeInTheDocument();
});

beforeEach(() => {
    localStorage.clear();
    global.fetch = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
});

test('shows the home screen with both ways into a game', () => {
    render(<App />);

    expect(screen.getByText('Finding Friends')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Create New Game' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Join Existing Game' })).toBeInTheDocument();
});

test('does not try to restore a session when none is saved', () => {
    render(<App />);

    expect(global.fetch).not.toHaveBeenCalled();
});

test('asks for the saved seat with its token, in a header', () => {
    localStorage.setItem('findingFriendsSession', JSON.stringify({
        game_code: 'below-adopt-havoc',
        user_uuid: 'uuid-alice',
        player_token: 'token-alice',
    }));

    render(<App />);

    expect(global.fetch).toHaveBeenCalledWith('/game/below-adopt-havoc/player', {
        headers: { 'X-Player-Token': 'token-alice' },
    });
});

test('drops a session saved before seats had tokens, without asking the server', () => {
    localStorage.setItem('findingFriendsSession', JSON.stringify({
        game_code: 'below-adopt-havoc',
        user_uuid: 'uuid-alice',
    }));

    render(<App />);

    expect(global.fetch).not.toHaveBeenCalled();
    expect(localStorage.getItem('findingFriendsSession')).toBeNull();
    expect(screen.getByRole('heading', { name: 'Create New Game' })).toBeInTheDocument();
});

test('clears a saved session when the game no longer exists', async () => {
    localStorage.setItem('findingFriendsSession', JSON.stringify({
        game_code: 'below-adopt-havoc',
        user_uuid: 'uuid-alice',
        player_token: 'token-alice',
    }));
    global.fetch = vi.fn(() => Promise.resolve({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ error: 'game_not_found' }),
    }));

    render(<App />);

    await waitFor(() => expect(localStorage.getItem('findingFriendsSession')).toBeNull());
    expect(screen.getByRole('heading', { name: 'Create New Game' })).toBeInTheDocument();
    expect(screen.getByText(/That game has ended/)).toBeInTheDocument();
});

test('keeps a saved session when the server is merely unreachable', async () => {
    localStorage.setItem('findingFriendsSession', JSON.stringify({
        game_code: 'below-adopt-havoc',
        user_uuid: 'uuid-alice',
        player_token: 'token-alice',
    }));
    global.fetch = vi.fn(() => Promise.reject(new Error('connection refused')));

    render(<App />);

    await waitFor(() => expect(screen.getByText(/Could not reach the server/)).toBeInTheDocument());
    expect(localStorage.getItem('findingFriendsSession')).not.toBeNull();
});
