import { render, screen, act, waitFor } from '@testing-library/react';
import Lobby from './Lobby';
import { createMockSocket } from '../test-utils/mockSocket';
import { playerView, sessionInfo, AVATAR_CHOICES } from '../test-utils/playerView';

/* HR-8 in the lobby: a watcher waits for the game like everyone else, but has
   no seat, and so no avatar to pick. */

const socket = createMockSocket();

const lobbyState = (overrides = {}) => playerView({
    game_event_state: 'waiting-for-player-to-join',
    ...overrides,
});

vi.mock('../api/socket', () => ({
    SERVER_URL: 'http://127.0.0.1:5050',
    SERVER_LABEL: 'http://127.0.0.1:5050',
    createSocket: () => socket,
}));

vi.mock('../api/client', () => ({
    fetchPlayerView: () => Promise.resolve(lobbyState()),
}));

const pushState = (overrides = {}) => act(() => {
    socket.fire('connect');
    socket.fire('game_stats', lobbyState(overrides));
});

const renderSettled = async () => {
    render(<Lobby sessionInfo={sessionInfo()} onLeaveGame={vi.fn()} onSessionInvalid={vi.fn()} />);
    await waitFor(() => expect(document.querySelector('.player-list')).toBeInTheDocument());
};

test('a watcher is told they are watching and offered no avatar', async () => {
    await renderSettled();

    pushState({ is_watcher: true, uuid: 'uuid-wes', name: 'Wes' });

    expect(screen.getByText(/Watching as/)).toBeInTheDocument();
    expect(screen.queryByText(/Playing as/)).not.toBeInTheDocument();
    AVATAR_CHOICES.forEach(glyph => {
        expect(screen.queryByRole('button', { name: glyph })).not.toBeInTheDocument();
    });
});

test('the lobby shows who is watching', async () => {
    await renderSettled();

    pushState({ watchers: [{ uuid: 'uuid-wes', name: 'Wes', joined_at: 0 }] });

    expect(screen.getByText('Watching: Wes')).toBeInTheDocument();
});
