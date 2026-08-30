import { render, screen, fireEvent, act, within } from '@testing-library/react';
import Game from './Game';
import { createMockSocket } from '../../test-utils/mockSocket';
import { playerView, sessionInfo, PLAYERS, card, gameEvent } from '../../test-utils/playerView';
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

    /* Picking cards and confirming them are one gesture, so the button lives
       with the cards rather than in the panel at the top of the screen. The
       panel keeps the turn indicator, which is read and not pressed. */
    describe('the confirm button', () => {
        const playButton = () => screen.queryByRole('button', { name: /Play \d+ card/ });

        test('sits in the hand area, not the phase panel', () => {
            renderGame(playState);
            fireEvent.click(screen.getByTitle(cardTitle('A', 'HEART')));

            expect(playButton().closest('.hand-area')).toBeInTheDocument();
            expect(playButton().closest('.phase-panel')).toBeNull();
        });

        test('is absent until a card is picked', () => {
            renderGame(playState);

            expect(playButton()).toBeNull();
        });

        test('waits for the full count when following a multi-card lead', () => {
            renderGame({
                ...playState,
                player_hand: [card('ACE', 'HEART'), card('KING', 'SPADE')],
                leading_hand_of_subround: [card('TWO', 'CLUB'), card('THREE', 'CLUB')],
            });

            fireEvent.click(screen.getByTitle(cardTitle('A', 'HEART')));
            expect(playButton()).toBeNull();

            fireEvent.click(screen.getByTitle(cardTitle('K', 'SPADE')));
            expect(playButton()).toHaveTextContent('Play 2 cards');
        });

        test('never appears on somebody else\'s turn', () => {
            renderGame({ ...playState, my_turn: false, current_player: PLAYERS[1] });

            expect(playButton()).toBeNull();
        });

        /* The indicator has to stay put — it is the thing that says whose turn
           it is, and moving it down with the button would bury it. */
        test('leaves the turn indicator behind in the panel', () => {
            renderGame(playState);
            fireEvent.click(screen.getByTitle(cardTitle('A', 'HEART')));

            expect(document.querySelector('.phase-panel .turn-indicator')).toBeInTheDocument();
        });
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

        test('a star marks the play currently taking the trick', () => {
            renderGame({ ...trickState, winning_player_of_round: PLAYERS[2] });

            expect(playFor('K', 'SPADE').querySelector('[title="Winning the trick"]'))
                .toBeInTheDocument();
            expect(playFor('Q', 'DIAMOND').querySelector('[title="Winning the trick"]'))
                .not.toBeInTheDocument();
        });

        test('only one play is starred at a time', () => {
            renderGame({ ...trickState, winning_player_of_round: PLAYERS[1] });

            expect(document.querySelectorAll('[title="Winning the trick"]')).toHaveLength(1);
        });

        /* Every play keeps a slot for the star whether it holds one or not, so
           the row does not shift as the lead changes hands. */
        test('plays reserve the star slot even when not winning', () => {
            renderGame({ ...trickState, winning_player_of_round: PLAYERS[2] });

            expect(playFor('Q', 'DIAMOND').querySelector('.trick-play-winning')).toBeInTheDocument();
        });

        test('no star before anyone is winning', () => {
            renderGame({ ...trickState, winning_player_of_round: null });

            expect(document.querySelector('[title="Winning the trick"]')).toBeNull();
        });

        /* The star follows the winner, and the winner is whoever the server
           says — not the last card played. */
        test('the star moves when a later play takes the lead', () => {
            const { socket } = renderGame({ ...trickState, winning_player_of_round: PLAYERS[1] });
            expect(playFor('Q', 'DIAMOND').querySelector('[title="Winning the trick"]'))
                .toBeInTheDocument();

            act(() => socket.fire('game_stats', playerView({
                ...trickState, winning_player_of_round: PLAYERS[2],
            })));

            expect(playFor('K', 'SPADE').querySelector('[title="Winning the trick"]'))
                .toBeInTheDocument();
            expect(playFor('Q', 'DIAMOND').querySelector('[title="Winning the trick"]'))
                .not.toBeInTheDocument();
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

    test('non-hosts wait for the host, by name', () => {
        renderGame({ ...roundEnded, hosting: false, host_uuid: PLAYERS[1].uuid });

        expect(screen.queryByRole('button', { name: 'Start Next Round' })).not.toBeInTheDocument();
        expect(screen.getByText('Waiting for host (Bob) to start the next round...'))
            .toBeInTheDocument();
    });

    /* A host who is not in the player list yet would otherwise read as
       "Waiting for host () to start...". */
    test('and falls back to a nameless wait when the host is unknown', () => {
        renderGame({ ...roundEnded, hosting: false, host_uuid: 'nobody-here' });

        expect(screen.getByText('Waiting for the host to start the next round...'))
            .toBeInTheDocument();
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
    // Roles live beside the chip rather than in it, so they are looked up on
    // the seat that holds both.
    const seatFor = (name) => playersBar().getByText(name).closest('.player-seat');

    test('every player in the bar is shown with their avatar', () => {
        renderGame({ game_event_state: 'round-started' });

        PLAYERS.forEach(player => {
            expect(playersBar().getByLabelText(`${player.name}'s avatar`))
                .toHaveTextContent(player.avatar);
        });
    });

    test('the crown marks whoever is alpha, not just you', () => {
        renderGame({ game_event_state: 'round-started', alpha_uuid: PLAYERS[2].uuid });

        expect(seatFor('Carol').querySelector('[title="Alpha player"]')).toBeInTheDocument();
        expect(seatFor('Alice').querySelector('[title="Alpha player"]')).not.toBeInTheDocument();
    });

    /* Revealing yourself IS joining the alpha team, so the swords carry it and
       there is no separate handshake to look for. */
    test('only friends who have revealed themselves are marked', () => {
        renderGame({
            game_event_state: 'round-started',
            alpha_uuid: PLAYERS[2].uuid,
            revealed_friends: [PLAYERS[3].uuid],
        });

        expect(seatFor('Dave').querySelector('[title="Alpha team"]')).toBeInTheDocument();
        expect(seatFor('Erin').querySelector('[title="Alpha team"]')).toBeNull();
    });

    /* Sides are the game's central secret — a friend is indistinguishable from
       a defender until they play a called card. The chip may only colour what
       is already public, so these pin both halves: what is shown, and what is
       deliberately not. */
    describe('sides', () => {
        const inAPlayedRound = (overrides) => renderGame({
            game_event_state: 'round-started',
            alpha_uuid: PLAYERS[2].uuid,
            ...overrides,
        });

        test('the alpha is on the alpha team, which everyone can see', () => {
            inAPlayedRound({});

            expect(seatFor('Carol').querySelector('[title="Alpha team"]')).toBeInTheDocument();
        });

        test('a friend who has outed themselves joins them', () => {
            inAPlayedRound({ revealed_friends: [PLAYERS[3].uuid] });

            expect(seatFor('Dave').querySelector('[title="Alpha team"]')).toBeInTheDocument();
        });

        test('everyone else keeps their side to themselves', () => {
            inAPlayedRound({ revealed_friends: [PLAYERS[3].uuid] });

            expect(seatFor('Erin').querySelector('[title="Alpha team"]')).toBeNull();
            expect(seatFor('Erin').querySelector('[title="Defenders"]')).toBeNull();
        });

        /* A shield is a claim that someone is NOT a friend, and that cannot be
           made while a called card is still unplayed. */
        test('nobody wears a shield until the last friend is out', () => {
            inAPlayedRound({ revealed_friends: [PLAYERS[3].uuid] });

            PLAYERS.forEach(player => {
                expect(seatFor(player.name).querySelector('[title="Defenders"]')).toBeNull();
            });
        });

        /* Including your own seat. The view's `on_alpha_team` reads like "is a
           defender" and means "has already revealed" — a player still holding a
           called card is not in it, so their own shield would sit there all
           round and then flip to swords the moment they played the card. */
        test('your own seat included, whatever on_alpha_team says', () => {
            inAPlayedRound({ on_alpha_team: false });

            expect(seatFor('Alice').querySelector('[title="Defenders"]')).toBeNull();
            expect(seatFor('Alice').querySelector('[title="Alpha team"]')).toBeNull();
        });

        test('revealing yourself is what puts the swords on your own seat', () => {
            inAPlayedRound({ revealed_friends: [PLAYERS[0].uuid], on_alpha_team: true });

            expect(seatFor('Alice').querySelector('[title="Alpha team"]')).toBeInTheDocument();
        });

        /* Once the last friend is out there is no secret left: whoever has not
           revealed themselves is a defender by elimination. */
        test('once every friend is out, the rest are defenders', () => {
            inAPlayedRound({
                revealed_friends: [PLAYERS[3].uuid],
                all_friends_found: true,
            });

            expect(seatFor('Dave').querySelector('[title="Alpha team"]')).toBeInTheDocument();
            expect(seatFor('Erin').querySelector('[title="Defenders"]')).toBeInTheDocument();
        });

        test('nobody has a side before there is an alpha', () => {
            renderGame({ game_event_state: 'round-started', alpha_uuid: '', on_alpha_team: false });

            PLAYERS.forEach(player => {
                expect(seatFor(player.name).querySelector('[title="Defenders"]')).toBeNull();
                expect(seatFor(player.name).querySelector('[title="Alpha team"]')).toBeNull();
            });
        });
    });

    /* Who someone is sits outside the chip; what is happening to them stays
       inside it. Both halves are pinned, because "above the chip" is only
       meaningful if something is still in there. */
    describe('roles above the chip', () => {
        test('a role marker sits outside the name plate', () => {
            renderGame({ game_event_state: 'round-started', alpha_uuid: PLAYERS[2].uuid });

            expect(seatFor('Carol').querySelector('[title="Alpha player"]')).toBeInTheDocument();
            expect(chipFor('Carol').querySelector('[title="Alpha player"]')).toBeNull();
        });

        test('and sits above it, not below', () => {
            renderGame({ game_event_state: 'round-started', alpha_uuid: PLAYERS[2].uuid });

            const seat = seatFor('Carol');
            expect(seat.firstElementChild).toHaveClass('player-roles');
            expect(seat.lastElementChild).toHaveClass('player-chip');
        });

        /* Your own seat is marked by the stripe on the chip. A stripe is
           there or it is not, so it needs no glyph propping it up. */
        test('your own seat is the stripe, not a glyph above it', () => {
            renderGame({ game_event_state: 'round-started', alpha_uuid: PLAYERS[2].uuid });

            expect(chipFor('Alice')).toHaveClass('is-me');
            expect(seatFor('Alice').querySelector('[title="You"]')).toBeNull();
        });

        test('a player with no role has no marker beside them at all', () => {
            renderGame({ game_event_state: 'round-started', alpha_uuid: PLAYERS[2].uuid });

            expect(seatFor('Bob').querySelector('.player-roles')).toBeNull();
        });

        /* The side has to be readable without seeing the stripe's colour:
           green-vs-blue is not a difference every player can make. */
        test('the side is said in a glyph, not left to the stripe', () => {
            renderGame({
                game_event_state: 'round-started',
                alpha_uuid: PLAYERS[2].uuid,
                revealed_friends: [PLAYERS[3].uuid],
                all_friends_found: true,
            });

            expect(seatFor('Dave').querySelector('[title="Alpha team"]')).toBeInTheDocument();
            expect(seatFor('Erin').querySelector('[title="Defenders"]')).toBeInTheDocument();
        });

        test('and is absent exactly where the stripe is', () => {
            renderGame({
                game_event_state: 'round-started',
                alpha_uuid: PLAYERS[2].uuid,
                revealed_friends: [],
            });

            expect(seatFor('Erin').querySelector('[title="Defenders"]')).toBeNull();
            expect(seatFor('Erin').querySelector('[title="Alpha team"]')).toBeNull();
        });

        /* A dropped connection is a state, not a role — it belongs on the
           plate that is changing. */
        test('a status marker stays on the chip', () => {
            renderGame({
                game_event_state: 'round-started',
                disconnected_players: [PLAYERS[1].uuid],
                current_player: PLAYERS[1],
            });

            expect(chipFor('Bob').querySelector('[title="Lost connection"]')).toBeInTheDocument();
            expect(chipFor('Bob').querySelector('[title="Their turn"]')).toBeInTheDocument();
        });
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

/* The vertical order is deliberate, so it is pinned rather than left to
   whichever order the JSX happens to be in. Scores are a glance-up-at thing and
   belong with the header; the turn indicator says what you are being asked to
   do, which comes before what is already on the table. */
/* The hint is about your own hand against a lead the whole table can see, so
   there is nothing in it to wait for your turn over — and waiting is exactly
   when a player has time to plan. */
describe('the playable hint while you wait', () => {
    const waiting = {
        game_event_state: 'round-started',
        my_turn: false,
        current_player: PLAYERS[1],
        player_hand: [card('ACE', 'HEART'), card('TWO', 'CLUB')],
        leading_hand_of_subround: [card('KING', 'HEART')],
        playable_hand_cards: [true, false],
    };

    const turnOnHint = () =>
        fireEvent.click(screen.getByRole('button', { name: 'Highlight playable' }));

    const ringed = () => [...document.querySelectorAll('.hand-card')]
        .map(node => node.classList.contains('is-playable'));

    beforeEach(() => localStorage.clear());

    test('rings your cards before the turn reaches you', () => {
        renderGame(waiting);

        turnOnHint();

        expect(ringed()).toEqual([true, false]);
    });

    /* "Any card" is half an answer when the lead was a pair — a player who
       reads it and picks one card gets refused. */
    test('and says how many are needed when nothing is ruled out', () => {
        renderGame({
            ...waiting,
            leading_hand_of_subround: [card('KING', 'SPADE'), card('QUEEN', 'SPADE')],
            playable_hand_cards: [true, true],
        });

        turnOnHint();

        expect(screen.getByText('Nothing is ruled out — any 2 of your cards can be played.'))
            .toBeInTheDocument();
    });

    test('reads as one card when only one is needed', () => {
        renderGame({ ...waiting, playable_hand_cards: [true, true] });

        turnOnHint();

        expect(screen.getByText(/any single card in your hand can be played/))
            .toBeInTheDocument();
    });

    test('and says so differently when nothing has been led at all', () => {
        renderGame({
            ...waiting,
            my_turn: true,
            leading_hand_of_subround: [],
            playable_hand_cards: [true, true],
        });

        turnOnHint();

        expect(screen.getByText(/Nothing has been led/)).toBeInTheDocument();
    });
});

/* Cards on the table say who played them; the side says who they played them
   for, which turns five loose cards into a contest. It is the same secrecy rule
   as the chips — a side still hidden shows as nothing here too. */
describe('sides in the trick area', () => {
    const trickWith = (overrides) => renderGame({
        game_event_state: 'round-started',
        alpha_uuid: PLAYERS[2].uuid,
        cards_in_active_pile: [card('KING', 'SPADE'), card('TWO', 'CLUB')],
        active_pile_player_uuids: [PLAYERS[2].uuid, PLAYERS[4].uuid],
        ...overrides,
    });

    const playFor = (name) => within(document.querySelector('.trick-area'))
        .getByTitle(name).closest('.trick-play');

    test('the side sits beside the avatar under the card', () => {
        trickWith({ all_friends_found: true });

        const carol = playFor('Carol').querySelector('.trick-play-player');
        expect(carol.querySelector('[title="Alpha team"]')).toBeInTheDocument();
        expect(carol.querySelector('[aria-label="Carol\'s avatar"]')).toBeInTheDocument();
    });

    test('the two sides are told apart', () => {
        trickWith({ all_friends_found: true });

        expect(playFor('Carol').querySelector('[title="Alpha team"]')).toBeInTheDocument();
        expect(playFor('Erin').querySelector('[title="Defenders"]')).toBeInTheDocument();
    });

    /* The trick area must not become a way of reading the table. */
    test('a side still hidden shows as nothing', () => {
        trickWith({ all_friends_found: false });

        expect(playFor('Erin').querySelector('[title="Defenders"]')).toBeNull();
        expect(playFor('Erin').querySelector('[title="Alpha team"]')).toBeNull();
    });

    test('and agrees with the chip for the same player', () => {
        trickWith({ all_friends_found: true });

        const seat = within(document.querySelector('.players-bar'))
            .getByText('Erin').closest('.player-seat');
        expect(seat.querySelector('[title="Defenders"]')).toBeInTheDocument();
        expect(playFor('Erin').querySelector('[title="Defenders"]')).toBeInTheDocument();
    });
});

describe('the shape of the screen during a round', () => {
    const LANDMARKS = '.game-header, .scores-bar, .players-bar, .phase-panel, .trick-area, .hand-area';

    test('reads header, scores, players, what to do, the trick, your hand', () => {
        renderGame({
            game_event_state: 'round-started',
            my_turn: true,
            player_hand: [card('ACE', 'HEART')],
            cards_in_active_pile: [card('KING', 'SPADE')],
            active_pile_player_uuids: [PLAYERS[1].uuid],
        });

        const order = [...document.querySelectorAll(LANDMARKS)]
            .map(node => node.className.split(' ')[0]);

        expect(order).toEqual([
            'game-header', 'scores-bar', 'players-bar',
            'phase-panel', 'trick-area', 'hand-area',
        ]);
    });
});

describe('in-game notifications', () => {
    const messages = () =>
        Array.from(document.querySelectorAll('.notification-message')).map(n => n.textContent);

    test('the table sees what just happened', () => {
        renderGame({
            game_event_state: 'round-started',
            events: [gameEvent('Bob played A♠️'), gameEvent('Bob won the trick')],
        });

        expect(messages()).toEqual(['Bob won the trick', 'Bob played A♠️']);
    });

    test('events pushed mid-game show up', () => {
        const { socket } = renderGame({ game_event_state: 'round-started', events: [] });
        expect(document.querySelector('.notifications')).toBeNull();

        act(() => socket.fire('game_stats', playerView({
            game_event_state: 'round-started',
            events: [gameEvent('Carol has joined the alpha team')],
        })));

        expect(screen.getByText('Carol has joined the alpha team')).toBeInTheDocument();
    });
});

describe('called cards', () => {
    const strip = () => document.querySelector('.meta-strip');

    const withCalls = (calls) => ({
        game_event_state: 'round-started',
        friend_calling_cards: calls,
        player_list: PLAYERS,
    });

    const call = (order, rank, suit, revealedBy = '') =>
        ({ order, rank, suit, revealed_by: revealedBy });

    test('lists the called cards', () => {
        renderGame(withCalls([call(1, 'ACE', 'HEART')]));

        expect(strip()).toHaveTextContent('1st ACE of ♥️');
    });

    test('an untriggered rule names nobody', () => {
        renderGame(withCalls([call(1, 'ACE', 'HEART')]));

        expect(strip().querySelector('.called-card-revealer')).toBeNull();
    });

    test('a triggered rule shows who tripped it, with their avatar', () => {
        renderGame(withCalls([call(1, 'ACE', 'HEART', PLAYERS[1].uuid)]));

        const revealer = strip().querySelector('.called-card-revealer');
        expect(revealer).toHaveTextContent(`(${PLAYERS[1].avatar} Bob)`);
    });

    /* The whole point: with several rules in play, each shows its own trigger
       rather than the table seeing an undifferentiated list of friends. */
    test('each rule shows its own player', () => {
        renderGame(withCalls([
            call(1, 'ACE', 'HEART', PLAYERS[1].uuid),
            call(1, 'ACE', 'SPADE', PLAYERS[2].uuid),
        ]));

        const cards = document.querySelectorAll('.called-card');
        expect(cards[0]).toHaveTextContent(`1st ACE of ♥️ (${PLAYERS[1].avatar} Bob)`);
        expect(cards[1]).toHaveTextContent(`1st ACE of ♠️ (${PLAYERS[2].avatar} Carol)`);
    });

    /* The row exists to help work out who is on which side. Once the last
       friend is out there is nothing left to work out, and every side is
       already visible on the chips. */
    test('the row goes once the last friend is out', () => {
        renderGame({
            ...withCalls([call(1, 'ACE', 'HEART', PLAYERS[1].uuid)]),
            all_friends_found: true,
        });

        expect(strip()).toBeNull();
    });

    test('but stays while a friend is still hidden', () => {
        renderGame({
            ...withCalls([call(1, 'ACE', 'HEART', PLAYERS[1].uuid), call(1, 'ACE', 'SPADE')]),
            all_friends_found: false,
        });

        expect(strip()).toHaveTextContent('1st ACE of ♠️');
    });

    /* There used to be a second strip listing revealed friends by name. It was
       cut because it said strictly less than this row does, so this pins that a
       reveal is still readable in both of the places that survived it: against
       the rule that caused it, and on the player's own chip. */
    test('a reveal is readable without a strip listing friends by name', () => {
        renderGame({
            ...withCalls([call(1, 'ACE', 'HEART', PLAYERS[1].uuid)]),
            // Friends only exist once an alpha has called them, and the seat's
            // side is only worked out once there is an alpha to be a side of.
            alpha_uuid: PLAYERS[2].uuid,
            revealed_friends: [PLAYERS[1].uuid],
        });

        expect(strip().querySelector('.called-card-revealer')).toHaveTextContent('Bob');

        const bobSeat = within(document.querySelector('.players-bar'))
            .getByText('Bob').closest('.player-seat');
        expect(bobSeat.querySelector('[title="Alpha team"]')).toBeInTheDocument();
    });

    test('a triggered rule sits alongside an untriggered one', () => {
        renderGame(withCalls([
            call(1, 'ACE', 'HEART', PLAYERS[1].uuid),
            call(1, 'ACE', 'SPADE'),
        ]));

        const cards = document.querySelectorAll('.called-card');
        expect(cards[0]).toHaveClass('is-revealed');
        expect(cards[1]).not.toHaveClass('is-revealed');
        expect(cards[1].querySelector('.called-card-revealer')).toBeNull();
    });

    test('a rule naming someone no longer at the table still lists its card', () => {
        renderGame(withCalls([call(1, 'ACE', 'HEART', 'uuid-gone')]));

        expect(strip()).toHaveTextContent('1st ACE of ♥️');
        expect(strip().querySelector('.called-card-revealer')).toBeNull();
    });

    /* Hidden during the calling phase — the alpha is still choosing. */
    test('stays hidden while the alpha is still calling', () => {
        renderGame({
            game_event_state: 'waiting-on-alpha-friend-card-choice',
            friend_calling_cards: [call(1, 'ACE', 'HEART', PLAYERS[1].uuid)],
        });

        expect(screen.queryByText(/Called Cards/)).not.toBeInTheDocument();
    });
});

describe('leaving the game', () => {
    const leaveButton = () => screen.getByRole('button', { name: 'Leave Game' });

    test('tells the table on the way out', () => {
        const { socket } = renderGame({ game_event_state: 'round-started' });

        fireEvent.click(leaveButton());

        expect(socket.lastEmit('leave_game')).toEqual({
            game_code: sessionInfo().game_code,
            player_uuid: sessionInfo().user_uuid,
        });
    });

    test('still leaves', () => {
        const { onLeaveGame } = renderGame({ game_event_state: 'round-started' });

        fireEvent.click(leaveButton());

        expect(onLeaveGame).toHaveBeenCalled();
    });

    /* Nobody to tell when the socket is already down — and trapping a player
       in a dead game would be far worse than a missing notification. */
    test('leaves even with the connection down', () => {
        const socket = createMockSocket();
        socket.connected = false;
        const onLeaveGame = vi.fn();
        render(
            <Game
                sessionInfo={sessionInfo()}
                initialGameState={playerView({ game_event_state: 'round-started' })}
                socket={socket}
                onLeaveGame={onLeaveGame}
                onSessionInvalid={vi.fn()}
            />
        );

        fireEvent.click(screen.getByRole('button', { name: 'Leave Game' }));

        expect(onLeaveGame).toHaveBeenCalled();
        expect(socket.lastEmit('leave_game')).toBeUndefined();
    });

    test('a departure shows up in the notifications', () => {
        const { socket } = renderGame({ game_event_state: 'round-started' });

        act(() => socket.fire('game_stats', playerView({
            game_event_state: 'round-started',
            events: [gameEvent('Bob left the game', {
                event: 'player-left', playerUuid: PLAYERS[1].uuid,
            })],
        })));

        expect(screen.getByText('Bob left the game')).toBeInTheDocument();
    });
});
