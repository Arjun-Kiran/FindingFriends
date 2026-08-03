import { render, screen, waitFor } from '@testing-library/react';
import App from './App';

beforeEach(() => {
    localStorage.clear();
    global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
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

test('clears a saved session when the game no longer exists', async () => {
    localStorage.setItem('findingFriendsSession', JSON.stringify({
        game_code: 'below-adopt-havoc',
        user_uuid: 'uuid-alice',
    }));
    global.fetch = jest.fn(() => Promise.resolve({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ error: 'game_not_found' }),
    }));

    render(<App />);

    await waitFor(() => expect(localStorage.getItem('findingFriendsSession')).toBeNull());
    expect(screen.getByRole('heading', { name: 'Create New Game' })).toBeInTheDocument();
});
