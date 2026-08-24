import { eventTimeMs, relativeTime } from './relativeTime';

const NOW = Date.parse('2026-08-23T12:00:00Z');
const ago = (ms) => relativeTime(NOW - ms, NOW);

describe('eventTimeMs', () => {
    /* The backend writes epoch seconds as a string. Reading it as milliseconds
       would date every event to 1970. */
    test('reads the epoch seconds the backend sends', () => {
        expect(eventTimeMs('1756000000.123')).toBe(1756000000123);
    });

    test('returns null for anything unparseable', () => {
        expect(eventTimeMs('')).toBeNull();
        expect(eventTimeMs(undefined)).toBeNull();
        expect(eventTimeMs('not-a-time')).toBeNull();
    });
});

describe('relativeTime', () => {
    test('anything under a minute is "now"', () => {
        expect(ago(0)).toBe('now');
        expect(ago(59_000)).toBe('now');
    });

    test('counts minutes, singular and plural', () => {
        expect(ago(60_000)).toBe('1 minute ago');
        expect(ago(10 * 60_000)).toBe('10 minutes ago');
        expect(ago(59 * 60_000)).toBe('59 minutes ago');
    });

    test('rolls up to hours and days', () => {
        expect(ago(60 * 60_000)).toBe('1 hour ago');
        expect(ago(3 * 60 * 60_000)).toBe('3 hours ago');
        expect(ago(24 * 60 * 60_000)).toBe('1 day ago');
        expect(ago(50 * 60 * 60_000)).toBe('2 days ago');
    });

    /* The browser and the server keep their own clocks, so a fresh event can
       arrive looking slightly in the future. */
    test('a timestamp in the future reads as "now", never a negative age', () => {
        expect(relativeTime(NOW + 30_000, NOW)).toBe('now');
        expect(relativeTime(NOW + 60 * 60_000, NOW)).toBe('now');
    });

    test('an unparseable time renders as nothing at all', () => {
        expect(relativeTime(null, NOW)).toBe('');
    });
});
