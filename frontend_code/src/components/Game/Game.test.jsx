import { render, screen, fireEvent, act, within } from '@testing-library/react';
import Game from './Game';
import { createMockSocket } from '../../test-utils/mockSocket';
import { playerView, sessionInfo, PLAYERS, card } from '../../test-utils/playerView';
import { SUIT_SYMBOLS } from '../../constants/cards';

/* Built from the constant rather than a literal glyph: the suit symbols are a
   presentation choice (they have already moved from text glyphs to emoji once),
   and these tests are about card selection, not about which glyph is current. */
const cardTitle = (rank, suit) => `${rank} ${SUIT_SYMBOLS[suit]}`;

const renderGame = (state = {}) => {
    const socket = createMockSocket();
    const onLeaveGame = vi.fn();
    const onSessionInvalid = vi.fn();
    const utils = render(
        <Game
            sessionInfo={sessionInfo()}
            initialGameState={playerView(state)}
            socket={socket}
            onLeaveGame={onLeaveGame}
            onSessionInvalid={onSessionInvalid}
        />
    );
    return { socket, onLeaveGame, onSessionInvalid, ...utils };
};

describe('while the connection is down', () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    /* The banner waits out a grace period; the refusal below does not. */
    const waitOutGracePeriod = () => act(() => vi.advanceTimersByTime(2000));

    test('says so instead of leaving a stale board looking live', () => {
        const { socket } = renderGame({ game_event_state: 'round-started' });

        expect(screen.queryByRole('status')).not.toBeInTheDocument();

        act(() => socket.fire('disconnect'));
        waitOutGracePeriod();

        expect(screen.getByRole('status')).toHaveTextContent(/Reconnecting/);
    });

    test('stays quiet through a blip that resolves inside the grace period', () => {
        const { socket } = renderGame({ game_event_state: 'round-started' });

        act(() => socket.fire('disconnect'));
        act(() => vi.advanceTimersByTime(500));
        act(() => socket.fire('connect'));
        waitOutGracePeriod();

        expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });

    test('treats a failed connection attempt the same as a dropped one', () => {
        // connect_error, not disconnect: the handshake never succeeded. This is
        // what a proxy that won't upgrade the websocket looks like.
        const { socket } = renderGame({ game_event_state: 'round-started' });

        act(() => socket.fire('connect_error', new Error('xhr poll error')));
        waitOutGracePeriod();

        expect(screen.getByRole('status')).toHaveTextContent(/Reconnecting/);
    });

    test('refuses actions rather than queueing them into a moved-on game', () => {
        const { socket } = renderGame({
            game_event_state: 'round-started',
            my_turn: true,
            player_hand: [card('ACE', 'HEART')],
        });
        act(() => socket.fire('disconnect'));
        socket.emit.mockClear();

        fireEvent.click(screen.getByTitle(cardTitle('A', 'HEART')));
        fireEvent.click(screen.getByRole('button', { name: /Play 1 card/ }));

        expect(socket.emit).not.toHaveBeenCalled();
        expect(screen.getByText(/Not connected to the server/)).toBeInTheDocument();
    });

    test('clears the warning once the socket is back', () => {
        const { socket } = renderGame({ game_event_state: 'round-started' });

        act(() => socket.fire('disconnect'));
        waitOutGracePeriod();
        expect(screen.getByRole('status')).toBeInTheDocument();

        act(() => socket.fire('connect'));

        expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });
});

describe('another player dropping mid-game', () => {
    test('marks their seat as held rather than removing them', () => {
        renderGame({
            game_event_state: 'round-started',
            disconnected_players: [PLAYERS[1].uuid],
        });

        // Still at the table — the seat is held, not freed — but flagged.
        const chip = screen.getByTitle('Bob lost connection');
        expect(chip).toHaveTextContent('Bob');
        expect(chip).toHaveClass('is-disconnected');
    });

    test('announces it, so a player looking at their hand still finds out', () => {
        const { socket } = renderGame({ game_event_state: 'round-started' });

        act(() => socket.fire('game_stats', playerView({
            game_event_state: 'round-started',
            disconnected_players: [PLAYERS[1].uuid],
            events: [{ uuid: 'evt-1', event: 'player-disconnected', message: 'Bob lost connection' }],
        })));

        expect(screen.getByText('Bob lost connection')).toBeInTheDocument();
    });

    test('explains a stalled turn instead of just going quiet', () => {
        renderGame({
            game_event_state: 'round-started',
            my_turn: false,
            current_player: PLAYERS[1],
            disconnected_players: [PLAYERS[1].uuid],
        });

        expect(screen.getByText(/Bob lost connection/)).toBeInTheDocument();
        expect(screen.queryByText(/Waiting for Bob to play/)).not.toBeInTheDocument();
    });

    test('reads as an ordinary wait when they are merely slow', () => {
        renderGame({
            game_event_state: 'round-started',
            my_turn: false,
            current_player: PLAYERS[1],
        });

        expect(screen.getByText(/Waiting for Bob to play/)).toBeInTheDocument();
    });
});

describe('a session the server no longer has', () => {
    test('hands the reset back to the parent', () => {
        const { socket, onSessionInvalid } = renderGame({ game_event_state: 'round-started' });

        act(() => socket.fire('session_invalid', {
            reason: 'game_not_found',
            message: 'Game not found: below-adopt-havoc',
        }));

        expect(onSessionInvalid).toHaveBeenCalledWith(
            expect.objectContaining({ reason: 'game_not_found' })
        );
    });

    test('re-joins on every reconnect so a restarted server learns of us', () => {
        const { socket } = renderGame({ game_event_state: 'round-started' });

        act(() => socket.fire('connect'));

        expect(socket.lastEmit('join')).toEqual({
            game_code: 'below-adopt-havoc',
            player_uuid: 'uuid-alice',
        });
    });
});

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

        // Name and status marker are separate elements now, so assert on the
        // chip as a whole rather than on one run of text.
        expect(screen.getByText('Alice').closest('.player-chip')).toHaveClass('is-me');

        const bobChip = screen.getByText('Bob').closest('.player-chip');
        expect(bobChip).toHaveClass('is-current');
        expect(bobChip.querySelector('[title="Their turn"]')).toBeInTheDocument();
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

        fireEvent.click(screen.getByTitle(cardTitle('A', 'HEART')));
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

        fireEvent.click(screen.getByRole('button', { name: SUIT_SYMBOLS.HEART }));

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

        fireEvent.click(screen.getByTitle(cardTitle('A', 'HEART')));
        expect(screen.queryByRole('button', { name: 'Confirm Discard' })).not.toBeInTheDocument();

        fireEvent.click(screen.getByTitle(cardTitle('K', 'SPADE')));
        expect(screen.getByRole('button', { name: 'Confirm Discard' })).toBeInTheDocument();
    });

    test('emits the selected cards as discards', () => {
        const { socket } = renderGame(kittyState);

        fireEvent.click(screen.getByTitle(cardTitle('A', 'HEART')));
        fireEvent.click(screen.getByTitle(cardTitle('K', 'SPADE')));
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

        fireEvent.click(screen.getByTitle(cardTitle('A', 'HEART')));
        fireEvent.click(screen.getByRole('button', { name: /Play 1 card/ }));

        expect(socket.lastEmit('play_cards').cards).toEqual([{ suit: 'HEART', rank: 'ACE' }]);
    });

    test('renders the cards already on the table', () => {
        renderGame({ ...playState, cards_in_active_pile: [card('QUEEN', 'DIAMOND')] });

        expect(screen.getByText('Current Trick')).toBeInTheDocument();
        expect(screen.getByTitle(cardTitle('Q', 'DIAMOND'))).toBeInTheDocument();
    });

    describe('who played what', () => {
        /* The play a given card belongs to, as rendered: the card element and
           the avatar beneath it share a .trick-play wrapper. Scoped to the
           trick area because the same card can also be sitting in your hand. */
        const playFor = (rank, suit) => within(document.querySelector('.trick-area'))
            .getByTitle(cardTitle(rank, suit))
            .closest('.trick-play');

        const trickState = {
            ...playState,
            cards_in_active_pile: [card('QUEEN', 'DIAMOND'), card('KING', 'SPADE')],
            active_pile_player_uuids: [PLAYERS[1].uuid, PLAYERS[2].uuid],
        };

        test('each card carries the avatar of whoever played it', () => {
            renderGame(trickState);

            expect(within(playFor('Q', 'DIAMOND')).getByLabelText("Bob's avatar"))
                .toHaveTextContent(PLAYERS[1].avatar);
            expect(within(playFor('K', 'SPADE')).getByLabelText("Carol's avatar"))
                .toHaveTextContent(PLAYERS[2].avatar);
        });

        test('two cards from the same player are both attributed to them', () => {
            renderGame({
                ...playState,
                cards_in_active_pile: [card('QUEEN', 'DIAMOND'), card('KING', 'SPADE')],
                active_pile_player_uuids: [PLAYERS[1].uuid, PLAYERS[1].uuid],
            });

            expect(within(playFor('Q', 'DIAMOND')).getByLabelText("Bob's avatar")).toBeInTheDocument();
            expect(within(playFor('K', 'SPADE')).getByLabelText("Bob's avatar")).toBeInTheDocument();
        });

        /* Games saved before the pile recorded who played what still have
           cards. A missing avatar is fine; a missing card is not. */
        test('cards with no attribution still render', () => {
            renderGame({
                ...playState,
                cards_in_active_pile: [card('QUEEN', 'DIAMOND')],
                active_pile_player_uuids: [],
            });

            expect(playFor('Q', 'DIAMOND')).toBeInTheDocument();
            expect(playFor('Q', 'DIAMOND').querySelector('.trick-play-player')).toBeNull();
        });

        test('a uuid with no matching player does not invent one', () => {
            renderGame({
                ...playState,
                cards_in_active_pile: [card('QUEEN', 'DIAMOND')],
                active_pile_player_uuids: ['uuid-who'],
            });

            expect(playFor('Q', 'DIAMOND')).toBeInTheDocument();
            expect(playFor('Q', 'DIAMOND').querySelector('.trick-play-player')).toBeNull();
        });
    });
});

describe('team scores', () => {
    // Teammates share one total, so the alpha and their friends must see the
    // same number rather than their individual trick tallies — but only once
    // every friend has revealed themselves.
    const scored = {
        game_event_state: 'round-started',
        all_friends_found: true,
        alpha_team_points: 50,
        defender_team_points: 45,
    };

    test('shows individual names while friends are still hidden', () => {
        renderGame({
            ...scored,
            all_friends_found: false,
            players_round_score: { [PLAYERS[0].uuid]: 30, [PLAYERS[1].uuid]: 20 },
        });

        expect(screen.getByText('Alice: 30 pts')).toBeInTheDocument();
        expect(screen.getByText('Bob: 20 pts')).toBeInTheDocument();
        expect(screen.queryByText('Alpha Team: 50 pts')).not.toBeInTheDocument();
    });

    test('switches to team totals once every friend is found', () => {
        renderGame(scored);

        expect(screen.getByText('Alpha Team: 50 pts')).toBeInTheDocument();
        expect(screen.getByText('Defenders: 45 pts')).toBeInTheDocument();
        expect(screen.queryByText(/Alice: \d+ pts/)).not.toBeInTheDocument();
    });

    test('an alpha and their friend see the same "your team" total', () => {
        const asAlpha = playerView({ ...scored, is_alpha: true, on_alpha_team: true, my_team_points: 50 });
        const asFriend = playerView({ ...scored, is_alpha: false, on_alpha_team: true, my_team_points: 50 });

        const { unmount } = render(
            <Game sessionInfo={sessionInfo()} initialGameState={asAlpha} socket={createMockSocket()} />
        );
        expect(screen.getByText(/Your team \(Alpha Team\): 50 pts/)).toBeInTheDocument();
        unmount();

        render(<Game sessionInfo={sessionInfo()} initialGameState={asFriend} socket={createMockSocket()} />);
        expect(screen.getByText(/Your team \(Alpha Team\): 50 pts/)).toBeInTheDocument();
    });

    test('defenders see the defender total as their own', () => {
        renderGame({ ...scored, on_alpha_team: false, my_team_points: 45 });

        expect(screen.getByText(/Your team \(Defenders\): 45 pts/)).toBeInTheDocument();
    });

    test('scores are hidden outside an active round', () => {
        renderGame({ ...scored, game_event_state: 'waiting-on-alpha-kitty-sort' });

        expect(screen.queryByText('Defenders: 45 pts')).not.toBeInTheDocument();
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

describe('avatars and role markers', () => {
    /* Avatars appear in the scores bar and the friends strip too, so every
       query here is scoped to the players bar rather than the whole document. */
    const playersBar = () => within(document.querySelector('.players-bar'));

    const chipFor = (name) => playersBar().getByText(name).closest('.player-chip');

    test('every player in the bar is shown with their avatar', () => {
        renderGame({ game_event_state: 'round-started' });

        PLAYERS.forEach(player => {
            expect(playersBar().getByLabelText(`${player.name}'s avatar`))
                .toHaveTextContent(player.avatar);
        });
    });

    test('the crown marks whoever is alpha, not just you', () => {
        renderGame({ game_event_state: 'round-started', alpha_uuid: PLAYERS[2].uuid });

        expect(chipFor('Carol').querySelector('[title="Alpha player"]')).toBeInTheDocument();
        expect(chipFor('Alice').querySelector('[title="Alpha player"]')).not.toBeInTheDocument();
    });

    test('only friends who have revealed themselves are marked', () => {
        renderGame({ game_event_state: 'round-started', revealed_friends: [PLAYERS[3].uuid] });

        expect(chipFor('Dave').querySelector('[title="Revealed friend"]')).toBeInTheDocument();
        expect(chipFor('Erin').querySelector('[title="Revealed friend"]')).not.toBeInTheDocument();
    });

    test('a disconnected player keeps their seat and gains a marker', () => {
        renderGame({ game_event_state: 'round-started', disconnected_players: [PLAYERS[1].uuid] });

        const bobChip = chipFor('Bob');
        expect(bobChip).toHaveClass('is-disconnected');
        expect(bobChip.querySelector('[title="Lost connection"]')).toBeInTheDocument();
    });

    /* Games saved before avatars existed still have players without one, and
       they must not render as an empty gap in the bar. */
    test('a player with no avatar falls back rather than rendering blank', () => {
        const noAvatar = PLAYERS.map(player => ({ ...player, avatar: undefined }));
        renderGame({ game_event_state: 'round-started', player_list: noAvatar });

        expect(playersBar().getByLabelText("Alice's avatar")).not.toBeEmptyDOMElement();
    });
});
