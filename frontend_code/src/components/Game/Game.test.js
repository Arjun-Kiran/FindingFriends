import { render, screen, fireEvent, act } from '@testing-library/react';
import Game from './Game';
import { createMockSocket } from '../../test-utils/mockSocket';
import { playerView, sessionInfo, PLAYERS, card } from '../../test-utils/playerView';

const renderGame = (state = {}) => {
    const socket = createMockSocket();
    const onLeaveGame = jest.fn();
    const utils = render(
        <Game
            sessionInfo={sessionInfo()}
            initialGameState={playerView(state)}
            socket={socket}
            onLeaveGame={onLeaveGame}
        />
    );
    return { socket, onLeaveGame, ...utils };
};

describe('header and player bar', () => {
    test('shows the game code and a readable phase label', () => {
        renderGame({ game_event_state: 'round-started' });

        expect(screen.getByText('Game: below-adopt-havoc')).toBeInTheDocument();
        expect(screen.getByText('Round in Progress')).toBeInTheDocument();
    });

    test('shows the trump declaration once one exists', () => {
        renderGame({
            game_event_state: 'round-started',
            declare_trump: { rank: 'ACE', suit: 'HEART' },
        });

        expect(screen.getByText(/Trump: ACE/)).toBeInTheDocument();
    });

    test('marks the current player and yourself in the player bar', () => {
        renderGame({ game_event_state: 'round-started', current_player: PLAYERS[1] });

        expect(screen.getByText(/^Alice \(you\)$/)).toBeInTheDocument();
        expect(screen.getByText(/^Bob ◀$/)).toBeInTheDocument();
    });
});

describe('socket wiring', () => {
    test('re-renders from a pushed game_stats payload', () => {
        const { socket } = renderGame({ game_event_state: 'round-started' });

        act(() => socket.fire('game_stats', playerView({ game_event_state: 'game-ended' })));

        expect(screen.getByText('Game Over!')).toBeInTheDocument();
    });

    test('surfaces a server error and lets it be dismissed', () => {
        const { socket } = renderGame({ game_event_state: 'round-started' });

        act(() => socket.fire('error', { message: 'Game not found: below-adopt-havoc' }));
        expect(screen.getByText('Game not found: below-adopt-havoc')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: '✕' }));
        expect(screen.queryByText('Game not found: below-adopt-havoc')).not.toBeInTheDocument();
    });

    test('unsubscribes its handlers on unmount', () => {
        const { socket, unmount } = renderGame({ game_event_state: 'round-started' });

        unmount();

        expect(socket.off).toHaveBeenCalledWith('game_stats', expect.any(Function));
        expect(socket.off).toHaveBeenCalledWith('error', expect.any(Function));
    });
});

describe('trump declaration phase', () => {
    test('non-alpha players are told to wait', () => {
        renderGame({ game_event_state: 'waiting-on-alpha-choose-trump', is_alpha: false });

        expect(screen.getByText(/Waiting for the alpha player to declare trump/)).toBeInTheDocument();
    });

    test('alpha sees the declaration panel', () => {
        renderGame({
            game_event_state: 'waiting-on-alpha-choose-trump',
            is_alpha: true,
            my_level: 13,
            player_hand: [card('ACE', 'HEART')],
        });

        expect(screen.getByText('Declare Trump Suit')).toBeInTheDocument();
    });

    // my_level arrives as an enum VALUE (13) while card.rank arrives as an enum
    // NAME ('ACE'). Comparing them directly is always false, which used to make
    // every hand look empty of level-matching cards.
    test('recognises hand cards that match your level', () => {
        const { socket } = renderGame({
            game_event_state: 'waiting-on-alpha-choose-trump',
            is_alpha: true,
            my_level: 13,
            player_hand: [card('ACE', 'HEART'), card('TWO', 'CLUB')],
        });

        expect(screen.queryByText(/You have no cards matching your level/)).not.toBeInTheDocument();

        fireEvent.click(screen.getByTitle('A ♥'));
        fireEvent.click(screen.getByRole('button', { name: /Declare .* as Trump/ }));

        expect(socket.lastEmit('declare_trump')).toEqual({
            game_code: 'below-adopt-havoc',
            player_uuid: PLAYERS[0].uuid,
            suit: 'HEART',
            rank: 'ACE',
        });
    });

    test('falls back to a suit picker when no card matches your level', () => {
        const { socket } = renderGame({
            game_event_state: 'waiting-on-alpha-choose-trump',
            is_alpha: true,
            my_level: 13,
            player_hand: [card('TWO', 'CLUB')],
        });

        expect(screen.getByText(/You have no cards matching your level/)).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: '♥' }));

        expect(socket.lastEmit('declare_trump')).toEqual({
            game_code: 'below-adopt-havoc',
            player_uuid: PLAYERS[0].uuid,
            suit: 'HEART',
            rank: 'ACE',
        });
    });

    test('jokers never count as a level match', () => {
        renderGame({
            game_event_state: 'waiting-on-alpha-choose-trump',
            is_alpha: true,
            my_level: 15,
            player_hand: [card('JOKER', 'BIG')],
        });

        expect(screen.getByText(/You have no cards matching your level/)).toBeInTheDocument();
    });
});

describe('friend calling phase', () => {
    const friendState = {
        game_event_state: 'waiting-on-alpha-friend-card-choice',
        is_alpha: true,
        num_friends_to_call: 2,
    };

    test('renders one selector row per friend to call', () => {
        renderGame(friendState);

        expect(screen.getByText('Call 2 Friend Cards')).toBeInTheDocument();
        expect(screen.getByText('#1')).toBeInTheDocument();
        expect(screen.getByText('#2')).toBeInTheDocument();
    });

    test('emits the chosen calling cards', () => {
        const { socket } = renderGame(friendState);

        fireEvent.click(screen.getByRole('button', { name: 'Confirm Friend Cards' }));

        const payload = socket.lastEmit('call_friends');
        expect(payload.game_code).toBe('below-adopt-havoc');
        expect(payload.calling_cards).toHaveLength(2);
    });

    test('non-alpha players are told to wait', () => {
        renderGame({ ...friendState, is_alpha: false });

        expect(screen.getByText(/Waiting for alpha to call friends/)).toBeInTheDocument();
    });
});

describe('kitty exchange phase', () => {
    const kittyState = {
        game_event_state: 'waiting-on-alpha-kitty-sort',
        is_alpha: true,
        kitty_size: 2,
        player_hand: [card('ACE', 'HEART'), card('KING', 'SPADE'), card('TWO', 'CLUB')],
    };

    test('discard button stays hidden until exactly kitty_size cards are picked', () => {
        renderGame(kittyState);

        expect(screen.queryByRole('button', { name: 'Confirm Discard' })).not.toBeInTheDocument();

        fireEvent.click(screen.getByTitle('A ♥'));
        expect(screen.queryByRole('button', { name: 'Confirm Discard' })).not.toBeInTheDocument();

        fireEvent.click(screen.getByTitle('K ♠'));
        expect(screen.getByRole('button', { name: 'Confirm Discard' })).toBeInTheDocument();
    });

    test('emits the selected cards as discards', () => {
        const { socket } = renderGame(kittyState);

        fireEvent.click(screen.getByTitle('A ♥'));
        fireEvent.click(screen.getByTitle('K ♠'));
        fireEvent.click(screen.getByRole('button', { name: 'Confirm Discard' }));

        expect(socket.lastEmit('kitty_exchange').discarded_cards).toEqual([
            { suit: 'HEART', rank: 'ACE' },
            { suit: 'SPADE', rank: 'KING' },
        ]);
    });
});

describe('card play phase', () => {
    const playState = {
        game_event_state: 'round-started',
        my_turn: true,
        player_hand: [card('ACE', 'HEART'), card('KING', 'SPADE')],
    };

    test('prompts you to lead when the trick is empty', () => {
        renderGame(playState);

        expect(screen.getByText(/your turn to lead/)).toBeInTheDocument();
    });

    test('asks for a matching count when following', () => {
        renderGame({ ...playState, leading_hand_of_subround: [card('TWO', 'CLUB'), card('THREE', 'CLUB')] });

        expect(screen.getByText(/Select 2 cards to play/)).toBeInTheDocument();
    });

    test('names the player being waited on', () => {
        renderGame({ ...playState, my_turn: false, current_player: PLAYERS[1] });

        expect(screen.getByText('Waiting for Bob to play...')).toBeInTheDocument();
    });

    test('emits the selected cards', () => {
        const { socket } = renderGame(playState);

        fireEvent.click(screen.getByTitle('A ♥'));
        fireEvent.click(screen.getByRole('button', { name: /Play 1 card/ }));

        expect(socket.lastEmit('play_cards').cards).toEqual([{ suit: 'HEART', rank: 'ACE' }]);
    });

    test('renders the cards already on the table', () => {
        renderGame({ ...playState, cards_in_active_pile: [card('QUEEN', 'DIAMOND')] });

        expect(screen.getByText('Current Trick')).toBeInTheDocument();
        expect(screen.getByTitle('Q ♦')).toBeInTheDocument();
    });
});

describe('round and game results', () => {
    const roundEnded = {
        game_event_state: 'round-ended',
        round_winner_side: 'defender',
        round_defender_points: 85,
        round_promotion_levels: 2,
        round_promoted_players: [PLAYERS[1].uuid],
        player_levels: { [PLAYERS[0].uuid]: 1, [PLAYERS[1].uuid]: 3 },
    };

    test('summarises the round outcome', () => {
        renderGame(roundEnded);

        expect(screen.getByText('Round Over!')).toBeInTheDocument();
        expect(screen.getByText('Defenders win!')).toBeInTheDocument();
        expect(screen.getByText(/85/)).toBeInTheDocument();
    });

    test('only the host can advance the round', () => {
        const { socket } = renderGame({ ...roundEnded, hosting: true });

        fireEvent.click(screen.getByRole('button', { name: 'Start Next Round' }));

        expect(socket.lastEmit('next_round')).toEqual({
            game_code: 'below-adopt-havoc',
            player_uuid: PLAYERS[0].uuid,
        });
    });

    test('non-hosts wait for the host', () => {
        renderGame({ ...roundEnded, hosting: false });

        expect(screen.queryByRole('button', { name: 'Start Next Round' })).not.toBeInTheDocument();
        expect(screen.getByText(/Waiting for the host to start the next round/)).toBeInTheDocument();
    });

    test('announces the winner and offers a way home', () => {
        const { onLeaveGame } = renderGame({
            game_event_state: 'game-ended',
            game_winner: PLAYERS[1].uuid,
        });

        expect(screen.getByText('Bob has passed Ace and wins the game!')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Back to Home' }));
        expect(onLeaveGame).toHaveBeenCalled();
    });
});

describe('hand', () => {
    test('reports how many cards you hold', () => {
        renderGame({
            game_event_state: 'round-started',
            player_hand: [card('ACE', 'HEART'), card('KING', 'SPADE')],
        });

        expect(screen.getByText('Your Hand (2 cards)')).toBeInTheDocument();
    });
});
