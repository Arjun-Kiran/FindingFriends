import { render, screen, fireEvent, act, waitFor, within } from '@testing-library/react';
import Lobby from './Lobby';
import { createMockSocket } from '../test-utils/mockSocket';
import { playerView, sessionInfo, PLAYERS, ME, AVATAR_CHOICES } from '../test-utils/playerView';

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

/* Resolves with a real lobby view, not {}. The component fetches once on mount
   and that promise settles on its own schedule — an empty payload landing last
   would wipe whatever the test had pushed. */
vi.mock('../api/client', () => ({
    fetchPlayerView: () => Promise.resolve(lobbyState()),
}));

/** Push a lobby state from the server, the way the real socket would. */
const pushState = (overrides = {}) => act(() => {
    socket.fire('connect');
    socket.fire('game_stats', lobbyState(overrides));
});

/* Render and wait for the mount fetch to land before pushing anything, so a
   late-resolving fetch can never overwrite the state under test. */
const renderSettled = async () => {
    render(<Lobby sessionInfo={sessionInfo()} onLeaveGame={vi.fn()} onSessionInvalid={vi.fn()} />);
    await waitFor(() => expect(document.querySelector('.player-list')).toBeInTheDocument());
};

beforeEach(() => {
    socket.emit.mockClear();
});

test('offers the avatars the server sent', async () => {
    await renderSettled();
    pushState();

    AVATAR_CHOICES.forEach(glyph => {
        expect(screen.getByRole('button', { name: glyph })).toBeInTheDocument();
    });
});

test('picking an avatar sends it to the server', async () => {
    await renderSettled();
    pushState();

    const free = AVATAR_CHOICES.find(glyph => !PLAYERS.some(player => player.avatar === glyph));
    fireEvent.click(screen.getByRole('button', { name: free }));

    expect(socket.lastEmit('choose_avatar')).toEqual({
        game_code: sessionInfo().game_code,
        player_uuid: ME.uuid,
        avatar: free,
    });
});

test('avatars other players hold cannot be picked', async () => {
    await renderSettled();
    pushState();

    // Bob's avatar, held by someone who is not us.
    expect(screen.getByRole('button', { name: PLAYERS[1].avatar })).toBeDisabled();
});

test('shows every player in the lobby with their avatar', async () => {
    await renderSettled();
    pushState();

    // Scoped to the roster: your own avatar also appears in the "Playing as"
    // line above it.
    const roster = within(document.querySelector('.player-list'));
    PLAYERS.forEach(player => {
        expect(roster.getByLabelText(`${player.name}'s avatar`)).toHaveTextContent(player.avatar);
    });
});

describe('waiting for the host', () => {
    test('names the host while you wait', async () => {
        await renderSettled();
        // Bob hosts; we are Alice, so the wait message is the one on screen.
        pushState({ hosting: false, host_uuid: PLAYERS[1].uuid });

        expect(screen.getByText('Waiting for host (Bob) to start the game...'))
            .toBeInTheDocument();
    });

    /* The lobby renders once before any state arrives; "Waiting for host ()"
       would be worse than the unnamed wording. */
    test('drops the brackets when the host is not known yet', async () => {
        await renderSettled();
        pushState({ hosting: false, host_uuid: '', player_list: [] });

        expect(screen.getByText('Waiting for host to start the game...'))
            .toBeInTheDocument();
    });

    test('the host is not told to wait for themselves', async () => {
        await renderSettled();
        pushState({ hosting: true, host_uuid: ME.uuid });

        expect(screen.queryByText(/Waiting for host/)).not.toBeInTheDocument();
    });
});


/* House rules are shown to the whole table and moved only by the host. A player
   deciding whether to stay needs to know what game this is. */
describe('house rules', () => {
    const ANY_TRUMP = 'Alpha may declare any trump';
    const box = (label) => screen.getByRole('checkbox', { name: new RegExp(label) });

    test('every rule is listed, whoever is looking', async () => {
        await renderSettled();
        pushState({ hosting: false });

        expect(screen.getByText('Trumps can be called as friend cards')).toBeInTheDocument();
        expect(screen.getByText(ANY_TRUMP)).toBeInTheDocument();
        expect(screen.getByText('Draw the first alpha at random')).toBeInTheDocument();
    });

    test('what the server says is on, shows as on', async () => {
        await renderSettled();
        pushState({ hosting: true, settings: { free_trump_choice: true } });

        expect(box(ANY_TRUMP)).toBeChecked();
    });

    test('the host toggling one sends the whole set', async () => {
        await renderSettled();
        pushState({
            hosting: true,
            settings: {
                trumps_can_be_called: true,
                free_trump_choice: false,
                random_first_alpha: false,
            },
        });

        fireEvent.click(box(ANY_TRUMP));

        /* Whole, not one key: two quick clicks sent piecemeal could land in
           either order and disagree about the rest. */
        expect(socket.emit).toHaveBeenCalledWith('update_settings', expect.objectContaining({
            settings: {
                trumps_can_be_called: true,
                free_trump_choice: true,
                random_first_alpha: false,
            },
        }));
    });

    test('a guest can read them but not move them', async () => {
        await renderSettled();
        pushState({ hosting: false, settings: { random_first_alpha: true } });

        expect(box('Draw the first alpha at random')).toBeChecked();
        expect(box('Draw the first alpha at random')).toBeDisabled();
        expect(screen.getByText('Only the host can change these.')).toBeInTheDocument();
    });

    /* The server would refuse the change anyway; this stops the box flipping
       on screen and then springing back when the state arrives. */
    test('and nor can the host while the socket is down', async () => {
        render(<Lobby sessionInfo={sessionInfo()} onLeaveGame={vi.fn()} onSessionInvalid={vi.fn()} />);
        await waitFor(() => expect(document.querySelector('.player-list')).toBeInTheDocument());
        act(() => socket.fire('game_stats', lobbyState({ hosting: true })));

        expect(box(ANY_TRUMP)).toBeDisabled();
    });
});
