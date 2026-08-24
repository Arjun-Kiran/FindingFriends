import { render, screen, fireEvent, act, within } from '@testing-library/react';
import Notifications from './Notifications';
import { gameEvent, PLAYERS } from '../../test-utils/playerView';
import { MAX_VISIBLE } from '../../hooks/useNotifications';

beforeEach(() => {
    localStorage.clear();
});

const messages = () =>
    Array.from(document.querySelectorAll('.notification-message')).map(node => node.textContent);

test('renders nothing when nothing has happened', () => {
    const { container } = render(<Notifications events={[]} />);

    expect(container).toBeEmptyDOMElement();
});

test('shows the events that have happened', () => {
    render(<Notifications events={[gameEvent('Bob played A♠️')]} />);

    expect(screen.getByText('Bob played A♠️')).toBeInTheDocument();
});

describe('only the newest few', () => {
    const five = [
        gameEvent('first'), gameEvent('second'), gameEvent('third'),
        gameEvent('fourth'), gameEvent('fifth'),
    ];

    test(`keeps at most ${MAX_VISIBLE}`, () => {
        render(<Notifications events={five} />);

        expect(messages()).toHaveLength(MAX_VISIBLE);
    });

    test('keeps the newest, not the oldest', () => {
        render(<Notifications events={five} />);

        expect(messages()).toEqual(['fifth', 'fourth', 'third']);
        expect(screen.queryByText('first')).not.toBeInTheDocument();
    });

    test('the newest is on top', () => {
        render(<Notifications events={five} />);

        expect(messages()[0]).toBe('fifth');
    });
});

describe('timestamps', () => {
    test('a fresh event reads as "now"', () => {
        render(<Notifications events={[gameEvent('Bob won the trick')]} />);

        expect(screen.getByText('now')).toBeInTheDocument();
    });

    test('older events say how long ago they were', () => {
        render(<Notifications events={[
            gameEvent('a while back', { secondsAgo: 600 }),
            gameEvent('just then', { secondsAgo: 60 }),
        ]} />);

        expect(screen.getByText('10 minutes ago')).toBeInTheDocument();
        expect(screen.getByText('1 minute ago')).toBeInTheDocument();
    });

    /* Nothing re-renders the stack between events, so without its own heartbeat
       "now" would still say "now" ten minutes later. */
    test('times refresh without a new event arriving', () => {
        vi.useFakeTimers();
        try {
            const events = [gameEvent('Bob won the trick')];
            render(<Notifications events={events} />);
            expect(screen.getByText('now')).toBeInTheDocument();

            act(() => vi.advanceTimersByTime(5 * 60 * 1000));

            expect(screen.getByText('5 minutes ago')).toBeInTheDocument();
            expect(screen.queryByText('now')).not.toBeInTheDocument();
        } finally {
            vi.useRealTimers();
        }
    });
});

describe('the newest notification', () => {
    const notifications = () => Array.from(document.querySelectorAll('.notification'));

    test('is outlined', () => {
        render(<Notifications events={[gameEvent('older'), gameEvent('newest')]} />);

        expect(notifications()[0]).toHaveTextContent('newest');
        expect(notifications()[0]).toHaveClass('is-latest');
    });

    test('is the only one outlined', () => {
        render(<Notifications events={[gameEvent('a'), gameEvent('b'), gameEvent('c')]} />);

        expect(notifications().filter(n => n.classList.contains('is-latest'))).toHaveLength(1);
    });

    test('the highlight moves when a newer event arrives', () => {
        const events = [gameEvent('first')];
        const { rerender } = render(<Notifications events={events} />);
        expect(notifications()[0]).toHaveTextContent('first');

        rerender(<Notifications events={[...events, gameEvent('second')]} />);

        expect(notifications()[0]).toHaveTextContent('second');
        expect(notifications()[0]).toHaveClass('is-latest');
        expect(notifications()[1]).not.toHaveClass('is-latest');
    });
});

describe('the player an event is about', () => {
    const bob = PLAYERS[1];

    test('is shown by their avatar, in front of the message', () => {
        render(
            <Notifications
                events={[gameEvent('Bob played A♠️', { playerUuid: bob.uuid })]}
                players={PLAYERS}
            />
        );

        const message = document.querySelector('.notification-message');
        expect(message).toHaveTextContent(`${bob.avatar} Bob played A♠️`);
        expect(within(message).getByLabelText("Bob's avatar")).toBeInTheDocument();
    });

    test('the avatar comes before the text, not after', () => {
        render(
            <Notifications
                events={[gameEvent('Bob won the trick', { playerUuid: bob.uuid })]}
                players={PLAYERS}
            />
        );

        const text = document.querySelector('.notification-message').textContent;
        expect(text.indexOf(bob.avatar)).toBe(0);
    });

    /* Events about the table rather than a player carry no uuid. */
    test('an event about nobody in particular gets no avatar', () => {
        render(<Notifications events={[gameEvent('The round has ended')]} players={PLAYERS} />);

        const message = document.querySelector('.notification-message');
        expect(message).toHaveTextContent('The round has ended');
        expect(message.querySelector('.avatar')).toBeNull();
    });

    /* A player can leave mid-game; their events stay in the feed. */
    test('an event naming someone no longer at the table still reads', () => {
        render(
            <Notifications
                events={[gameEvent('Zoe left the game', { playerUuid: 'uuid-gone' })]}
                players={PLAYERS}
            />
        );

        expect(screen.getByText('Zoe left the game')).toBeInTheDocument();
        expect(document.querySelector('.notification-message .avatar')).toBeNull();
    });
});

describe('choosing a corner', () => {
    const stack = () => document.querySelector('.notifications');
    const moveButton = () => within(stack()).getByRole('button');

    test('defaults to the top right', () => {
        render(<Notifications events={[gameEvent('hello')]} />);

        expect(stack()).toHaveClass('is-top-right');
    });

    test('the player can move it to the other corner', () => {
        render(<Notifications events={[gameEvent('hello')]} />);

        fireEvent.click(moveButton());

        expect(stack()).toHaveClass('is-top-left');
    });

    test('the choice is remembered for next time', () => {
        const { unmount } = render(<Notifications events={[gameEvent('hello')]} />);
        fireEvent.click(moveButton());
        unmount();

        render(<Notifications events={[gameEvent('hello again')]} />);

        expect(stack()).toHaveClass('is-top-left');
    });

    test('a stored corner that is not a corner falls back to the default', () => {
        localStorage.setItem('findingFriendsNotificationCorner', 'somewhere-else');

        render(<Notifications events={[gameEvent('hello')]} />);

        expect(stack()).toHaveClass('is-top-right');
    });

    /* Private windows and "block site data" make localStorage throw on access,
       not just return null. A notification preference must not take the game
       down with it. */
    test('survives a browser that refuses storage', () => {
        const blocked = () => { throw new Error('storage disabled'); };
        const getItem = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(blocked);
        const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(blocked);

        try {
            render(<Notifications events={[gameEvent('hello')]} />);
            expect(stack()).toHaveClass('is-top-right');

            fireEvent.click(moveButton());
            expect(stack()).toHaveClass('is-top-left');
        } finally {
            getItem.mockRestore();
            setItem.mockRestore();
        }
    });

    test('the button says which way it will move them', () => {
        render(<Notifications events={[gameEvent('hello')]} />);

        expect(screen.getByLabelText('Move notifications to the left')).toBeInTheDocument();
        fireEvent.click(moveButton());
        expect(screen.getByLabelText('Move notifications to the right')).toBeInTheDocument();
    });
});
