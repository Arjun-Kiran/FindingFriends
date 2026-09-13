import { render, screen, fireEvent } from '@testing-library/react';
import Game from './Game';
import { createMockSocket } from '../../test-utils/mockSocket';
import { playerView, sessionInfo, PLAYERS } from '../../test-utils/playerView';

/* HR-8 on the board: watching, seats counting down and opening, the host
   handing them out, and a room running short of players. */

const WATCHER = { uuid: 'uuid-wes', name: 'Wes', joined_at: 0 };
const BOB = PLAYERS[1].uuid;
const NOW = 1_800_000_000;

const renderGame = (state = {}) => {
    const socket = createMockSocket();
    render(
        <Game
            sessionInfo={sessionInfo()}
            initialGameState={playerView({ game_event_state: 'round-started', server_time: NOW, ...state })}
            socket={socket}
            onLeaveGame={vi.fn()}
            onSessionInvalid={vi.fn()}
        />
    );
    return { socket };
};

const asWatcher = (state = {}) => renderGame({
    uuid: WATCHER.uuid,
    name: WATCHER.name,
    is_watcher: true,
    my_level: 0,
    host_uuid: PLAYERS[0].uuid,
    watchers: [WATCHER],
    ...state,
});

const away = (secondsAgo, left = false) => ({ since: NOW - secondsAgo, left, announced: false });

describe('watching a game', () => {
    test('says so, and shows no hand', () => {
        asWatcher();

        expect(screen.getByRole('heading', { name: /You are watching/ })).toBeInTheDocument();
        expect(screen.queryByText(/Your Hand/)).not.toBeInTheDocument();
        expect(document.querySelector('.watching-badge')).toHaveTextContent('Watching');
    });

    test('leaving is stopping watching', () => {
        const { socket } = asWatcher();

        fireEvent.click(screen.getByRole('button', { name: 'Stop Watching' }));

        expect(socket.lastEmit('leave_game')).toBeDefined();
    });

    test('a watcher is never told which side they are on', () => {
        asWatcher({ all_friends_found: true });

        expect(screen.queryByText(/Your team/)).not.toBeInTheDocument();
    });

    test('can ask to play from the next round', () => {
        const { socket } = asWatcher();

        fireEvent.click(screen.getByRole('button', { name: 'Ask to play from the next round' }));

        expect(socket.lastEmit('ask_to_join')).toEqual(expect.objectContaining({
            game_code: 'below-adopt-havoc',
        }));
    });

    test('says who it is waiting on once it has asked, and can take it back', () => {
        const { socket } = asWatcher({
            seat_requests: [{ watcher_uuid: WATCHER.uuid, seat_uuid: '', approved: false, level: 1 }],
        });

        expect(screen.getByText(/You asked to play from the next round. Waiting for the host \(Alice\)/))
            .toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: 'Take back' }));

        expect(socket.lastEmit('withdraw_seat_request')).toBeDefined();
    });

    test('says so once the host has said yes', () => {
        asWatcher({
            seat_requests: [{ watcher_uuid: WATCHER.uuid, seat_uuid: '', approved: true, level: 5 }],
        });

        expect(screen.getByText(/you join when the next round starts/)).toBeInTheDocument();
    });

    test('is offered the seat of a player who has dropped', () => {
        const { socket } = asWatcher({
            disconnected_players: [BOB],
            seat_vacancies: { [BOB]: away(18) },
        });

        fireEvent.click(screen.getByRole('button', { name: "Take Bob's seat" }));

        expect(socket.lastEmit('volunteer_for_seat')).toEqual(expect.objectContaining({ seat_uuid: BOB }));
    });

    test('shows an offer as made', () => {
        asWatcher({
            seat_vacancies: { [BOB]: away(18) },
            seat_requests: [{ watcher_uuid: WATCHER.uuid, seat_uuid: BOB, approved: false, level: 1 }],
        });

        expect(screen.getByText('Offered')).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: "Take Bob's seat" })).not.toBeInTheDocument();
        expect(screen.getByText(/You offered to take over Bob's seat/)).toBeInTheDocument();
    });
});

describe('a seat whose player has gone', () => {
    test('counts down the time they have to come back, in words', () => {
        renderGame({ disconnected_players: [BOB], seat_vacancies: { [BOB]: away(18) } });

        expect(screen.getByText('0:42')).toBeInTheDocument();
        expect(screen.getByTitle(/Bob has 0:42 to reconnect/)).toBeInTheDocument();
    });

    test('says the seat is open once it is', () => {
        renderGame({ seat_vacancies: { [BOB]: away(90) }, open_seats: [BOB] });

        expect(screen.getByText('Seat open')).toBeInTheDocument();
        expect(screen.queryByText('0:00')).not.toBeInTheDocument();
    });

    test('opens at once for a player who pressed Leave', () => {
        renderGame({ seat_vacancies: { [BOB]: away(2, true) } });

        expect(screen.getByText('Seat open')).toBeInTheDocument();
    });

    test('is not offered to a player already at the table', () => {
        renderGame({ seat_vacancies: { [BOB]: away(18) } });

        expect(screen.queryByRole('button', { name: "Take Bob's seat" })).not.toBeInTheDocument();
    });
});

describe('the host', () => {
    const volunteer = { watcher_uuid: WATCHER.uuid, seat_uuid: BOB, approved: false, level: 1 };
    const joiner = { watcher_uuid: WATCHER.uuid, seat_uuid: '', approved: false, level: 1 };

    test('can approve a volunteer, who is told it seats them straight away', () => {
        const { socket } = renderGame({ hosting: true, watchers: [WATCHER], seat_requests: [volunteer] });

        expect(screen.getByText(/Wes wants to take over Bob's seat, hand and all. Approving seats them straight away./))
            .toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: 'Approve' }));

        expect(socket.lastEmit('approve_seat_request')).toEqual(expect.objectContaining({
            watcher_uuid: WATCHER.uuid,
        }));
    });

    test('can decline one', () => {
        const { socket } = renderGame({ hosting: true, watchers: [WATCHER], seat_requests: [volunteer] });

        fireEvent.click(screen.getByRole('button', { name: 'Decline' }));

        expect(socket.lastEmit('decline_seat_request')).toEqual(expect.objectContaining({
            watcher_uuid: WATCHER.uuid,
        }));
    });

    test('picks the level someone joining next round starts on', () => {
        const { socket } = renderGame({ hosting: true, watchers: [WATCHER], seat_requests: [joiner] });

        fireEvent.change(screen.getByLabelText("Wes's starting level"), { target: { value: '5' } });
        fireEvent.click(screen.getByRole('button', { name: 'Approve' }));

        expect(socket.lastEmit('approve_seat_request')).toEqual(expect.objectContaining({
            watcher_uuid: WATCHER.uuid,
            level: 5,
        }));
    });

    test('can end a round an empty seat is holding up, as a draw', () => {
        const { socket } = renderGame({
            hosting: true,
            round_held_up: true,
            open_seats: [BOB],
            seat_vacancies: { [BOB]: away(5, true) },
        });

        expect(screen.getByText(/Bob's seat is open. Approve a watcher to take over, or end the round as a draw/))
            .toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: 'End round as a draw' }));

        expect(socket.lastEmit('end_round_as_draw')).toBeDefined();
    });

    test('is the only one who sees requests to play', () => {
        renderGame({ hosting: false, watchers: [WATCHER], seat_requests: [volunteer] });

        expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument();
    });
});

describe('everyone else at a held-up table', () => {
    test('is told what the table is waiting on, and by whom', () => {
        renderGame({ hosting: false, host_uuid: PLAYERS[2].uuid, round_held_up: true, open_seats: [BOB] });

        expect(screen.getByText(/Bob's seat is open. Waiting for the host \(Carol\)/)).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'End round as a draw' })).not.toBeInTheDocument();
    });
});

describe('a room short of players', () => {
    test('warns everyone how long it has left', () => {
        renderGame({ room_closes_at: NOW + 540 });

        expect(screen.getByText(/This room closes in 9:00 unless 5 are back/)).toBeInTheDocument();
    });
});
