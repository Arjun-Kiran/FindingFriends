import { render, screen, act } from '@testing-library/react';
import BigNotification from './BigNotification';
import { BANNER_MS, MAX_EVENT_LINES } from '../../hooks/useBigNotification';
import { gameEvent, PLAYERS } from '../../test-utils/playerView';
// The stylesheet as text — see the pointer-events test at the bottom.
import appCss from '../../App.css?raw';

const BOB = PLAYERS[1];
const CAROL = PLAYERS[2];

/* A play worth interrupting for. Only events carrying a clause are — the
   server decides that, so the fixtures have to say it too. */
const big = (clause, { player = BOB, event = 'hand-play' } = {}) =>
    gameEvent(`${player.name} ${clause}`, { event, playerUuid: player.uuid, clause });

const banner = () => document.querySelector('.big-notification');
const lines = () =>
    Array.from(document.querySelectorAll('.big-notification-line')).map(n => n.textContent);

const show = (props) => render(<BigNotification players={PLAYERS} {...props} />);

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

/* Nothing is news on a first render — see the first-look note in the hook. The
   banner only ever fires on something arriving, so every test here starts from
   a mount and then pushes state, exactly as the socket does. */
const arrive = (rerender, props) => {
    act(() => { rerender(<BigNotification players={PLAYERS} {...props} />); });
};

describe('what earns a banner', () => {
    test('a big play interrupts the table', () => {
        const { rerender } = show({ events: [] });

        arrive(rerender, { events: [big('led with a tractor')] });

        expect(lines()).toEqual([`${BOB.avatar} ${BOB.name} led with a tractor`]);
    });

    test('an ordinary event does not', () => {
        const { rerender } = show({ events: [] });

        arrive(rerender, { events: [gameEvent('Bob played 7♠️', { playerUuid: BOB.uuid })] });

        expect(banner()).toBeNull();
    });

    test('nothing is on screen before anything happens', () => {
        const { container } = show({ events: [] });

        expect(container).toBeEmptyDOMElement();
    });

    /* Opening the board mid-game would otherwise fire a banner for whatever
       happened before you arrived. */
    test('the events already in the feed are history, not news', () => {
        show({ events: [big('won the trick with A♠️', { event: 'trick-won' })] });

        expect(banner()).toBeNull();
    });
});

describe('combining what happened at once', () => {
    test("one player's plays are stitched under one name", () => {
        const { rerender } = show({ events: [] });

        arrive(rerender, {
            events: [
                big('led with a tractor'),
                big('won the trick with 8♣️8♣️7♣️7♣️', { event: 'trick-won' }),
            ],
        });

        expect(lines()).toEqual([
            `${BOB.avatar} ${BOB.name} led with a tractor and won the trick with 8♣️8♣️7♣️7♣️`,
        ]);
    });

    test('three clauses read as a list', () => {
        const { rerender } = show({ events: [] });

        arrive(rerender, {
            events: [
                big('led with a tractor'),
                big('joined the alpha team', { event: 'friend-revealed' }),
                big('won the trick with 8♣️8♣️', { event: 'trick-won' }),
            ],
        });

        // In the order they happened, which is how the player watched them.
        // Priority ranks lines against each other, not clauses within one.
        expect(lines()[0]).toContain(
            'led with a tractor, joined the alpha team and won the trick with 8♣️8♣️'
        );
    });

    /* The friend who reveals themselves is whoever played the called card, and
       need not be the one who takes the trick. Two subjects cannot share a
       sentence, so they get a line each. */
    test('two players get a line each', () => {
        const { rerender } = show({ events: [] });

        arrive(rerender, {
            events: [
                big('joined the alpha team', { player: CAROL, event: 'friend-revealed' }),
                big('won the trick with A♠️', { event: 'trick-won' }),
            ],
        });

        expect(lines()).toEqual([
            `${CAROL.avatar} ${CAROL.name} joined the alpha team`,
            `${BOB.avatar} ${BOB.name} won the trick with A♠️`,
        ]);
    });

    test(`no more than ${MAX_EVENT_LINES} players are named`, () => {
        const { rerender } = show({ events: [] });

        arrive(rerender, {
            events: PLAYERS.map(player => big('won the trick with A♠️', { player, event: 'trick-won' })),
        });

        expect(lines()).toHaveLength(MAX_EVENT_LINES);
    });

    /* Ranked by how much it changes the game, not by arrival order — a friend
       revealing themselves redraws the teams. */
    test('the most important players are the ones kept', () => {
        const { rerender } = show({ events: [] });

        arrive(rerender, {
            events: [
                big('declared ♥️ as trump', { player: PLAYERS[3], event: 'trump-declared' }),
                big('won the trick with A♠️', { event: 'trick-won' }),
                big('joined the alpha team', { player: CAROL, event: 'friend-revealed' }),
            ],
        });

        expect(lines()[0]).toContain(CAROL.name);
        expect(lines()[1]).toContain(BOB.name);
        expect(lines().join()).not.toContain(PLAYERS[3].name);
    });
});

describe('your turn', () => {
    test('is announced when the turn comes round', () => {
        const { rerender } = show({ events: [], myTurn: false });

        arrive(rerender, { events: [], myTurn: true });

        expect(lines()).toEqual(['👉 Your turn']);
    });

    test('is not announced again while it is still your turn', () => {
        const { rerender } = show({ events: [], myTurn: false });
        arrive(rerender, { events: [], myTurn: true });
        act(() => { vi.advanceTimersByTime(BANNER_MS); });

        arrive(rerender, { events: [], myTurn: true });

        expect(banner()).toBeNull();
    });

    test('is announced again the next time round', () => {
        const { rerender } = show({ events: [], myTurn: false });
        arrive(rerender, { events: [], myTurn: true });
        arrive(rerender, { events: [], myTurn: false });
        act(() => { vi.advanceTimersByTime(BANNER_MS); });

        arrive(rerender, { events: [], myTurn: true });

        expect(lines()).toEqual(['👉 Your turn']);
    });

    /* Loading straight into your own turn is exactly when you need telling. */
    test('is announced on a board that opens on your turn', () => {
        show({ events: [], myTurn: true });

        expect(lines()).toEqual(['👉 Your turn']);
    });

    /* Winning a trick puts the lead on you, so both land in one push. */
    test('rides along with the play that caused it', () => {
        const { rerender } = show({ events: [], myTurn: false });

        arrive(rerender, {
            events: [big('won the trick with A♠️', { event: 'trick-won' })],
            myTurn: true,
        });

        expect(lines()).toEqual([
            `${BOB.avatar} ${BOB.name} won the trick with A♠️`,
            '👉 Your turn',
        ]);
    });

    /* The one line that asks the player to do something. The cap trims plays,
       never this. */
    test('survives a banner already full of plays', () => {
        const { rerender } = show({ events: [], myTurn: false });

        arrive(rerender, {
            events: PLAYERS.map(player => big('won the trick with A♠️', { player, event: 'trick-won' })),
            myTurn: true,
        });

        expect(lines()).toHaveLength(MAX_EVENT_LINES + 1);
        expect(lines()[lines().length - 1]).toBe('👉 Your turn');
    });
});

describe('going away again', () => {
    test('stays up for its two seconds', () => {
        const { rerender } = show({ events: [] });
        arrive(rerender, { events: [big('led with a tractor')] });

        act(() => { vi.advanceTimersByTime(BANNER_MS - 100); });

        expect(banner()).not.toBeNull();
    });

    test('is gone after that', () => {
        const { rerender } = show({ events: [] });
        arrive(rerender, { events: [big('led with a tractor')] });

        act(() => { vi.advanceTimersByTime(BANNER_MS); });

        expect(banner()).toBeNull();
    });

    /* Two seconds is already a long time to cover the table, so a new banner
       replaces whatever is up rather than queueing behind it. */
    test('a newer banner replaces one still on screen', () => {
        const { rerender } = show({ events: [] });
        const first = [big('led with a tractor')];
        arrive(rerender, { events: first });
        act(() => { vi.advanceTimersByTime(BANNER_MS / 2); });

        arrive(rerender, {
            events: [...first, big('won the trick with A♠️', { player: CAROL, event: 'trick-won' })],
        });

        expect(lines()).toEqual([`${CAROL.avatar} ${CAROL.name} won the trick with A♠️`]);
    });

    test('the replacement gets its full two seconds', () => {
        const { rerender } = show({ events: [] });
        const first = [big('led with a tractor')];
        arrive(rerender, { events: first });
        act(() => { vi.advanceTimersByTime(BANNER_MS / 2); });
        arrive(rerender, {
            events: [...first, big('won the trick with A♠️', { player: CAROL, event: 'trick-won' })],
        });

        act(() => { vi.advanceTimersByTime(BANNER_MS - 100); });

        expect(banner()).not.toBeNull();
    });
});

/* The socket re-pushes the whole state on every reconnect, unchanged. Without
   dedupe by event uuid that would replay the last big play every time the
   connection flapped. */
describe('a state push that is not news', () => {
    test('the same events arriving again say nothing', () => {
        const { rerender } = show({ events: [] });
        const events = [big('led with a tractor')];
        arrive(rerender, { events });
        act(() => { vi.advanceTimersByTime(BANNER_MS); });

        arrive(rerender, { events: [...events] });

        expect(banner()).toBeNull();
    });

    test('a fresh copy of the same array is still not news', () => {
        const { rerender } = show({ events: [] });
        const events = [big('led with a tractor')];
        arrive(rerender, { events });
        act(() => { vi.advanceTimersByTime(BANNER_MS); });

        arrive(rerender, { events: events.map(event => ({ ...event })) });

        expect(banner()).toBeNull();
    });
});

describe('an event about someone no longer at the table', () => {
    /* Their name and avatar are gone, and a subjectless "won the trick" is not
       worth covering the board for. The feed still carries it, name and all. */
    test('is left to the feed', () => {
        const { rerender } = show({ events: [] });

        arrive(rerender, {
            events: [gameEvent('Zoe won the trick', {
                event: 'trick-won', playerUuid: 'uuid-gone', clause: 'won the trick',
            })],
        });

        expect(banner()).toBeNull();
    });

    test('does not take a line from someone who is still here', () => {
        const { rerender } = show({ events: [] });

        arrive(rerender, {
            events: [
                gameEvent('Zoe won the trick', {
                    event: 'trick-won', playerUuid: 'uuid-gone', clause: 'won the trick',
                }),
                big('led with a tractor'),
            ],
        });

        expect(lines()).toEqual([`${BOB.avatar} ${BOB.name} led with a tractor`]);
    });
});

describe('getting out of the way', () => {
    /* It lands over the board at the moment a player is being told to act. One
       that ate the tap answering it would be worse than no banner at all.

       Read out of the stylesheet because jsdom loads no CSS, so a computed
       style here would say 'auto' however the rule was written. That makes
       this a guard against the declaration being dropped rather than proof of
       what a browser does — which is still the regression worth catching. */
    test('never takes a click', () => {
        const rule = appCss.slice(appCss.indexOf('.big-notification {'));

        expect(rule.slice(0, rule.indexOf('}'))).toContain('pointer-events: none');
    });

    /* The feed announces every event as a polite live region and the phase
       panel says whose turn it is in words. Saying it a third time is just an
       interruption. */
    test('is not read out on top of the feed and the turn indicator', () => {
        const { rerender } = show({ events: [], myTurn: false });

        arrive(rerender, { events: [big('led with a tractor')], myTurn: true });

        expect(banner()).toHaveAttribute('aria-hidden', 'true');
    });

    test('the player is named in words, not only by their avatar', () => {
        const { rerender } = show({ events: [] });

        arrive(rerender, { events: [big('led with a tractor')] });

        expect(screen.getByText(BOB.name)).toBeInTheDocument();
    });
});
