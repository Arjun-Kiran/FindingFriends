import { vi, describe, test, expect, beforeEach, afterEach } from 'vitest';

/* What these pin down is the TLS migration.
 *
 * socket.io only upgrades to wss:// on its own when it is given NO url and has
 * to derive one from the page. Hand it an absolute http:// address and an
 * https:// page refuses it as mixed content — and because the client is
 * websocket-only with no polling fallback, that is not a degraded game, it is
 * a game that never starts. */

const io = vi.fn(() => ({ on: vi.fn(), close: vi.fn() }));
vi.mock('socket.io-client', () => ({ io: (...args) => io(...args) }));

const loadSocketModule = async (serverUrl) => {
    vi.resetModules();
    io.mockClear();
    vi.stubEnv('VITE_SERVER_URL', serverUrl);
    return import('./socket');
};

afterEach(() => {
    vi.unstubAllEnvs();
});

describe('with an explicitly empty VITE_SERVER_URL (a production build)', () => {
    test('connects with no url, so the socket follows the page origin', async () => {
        const { createSocket, SERVER_URL } = await loadSocketModule('');
        createSocket();

        expect(SERVER_URL).toBe('');
        // One argument only: the options. A url would pin the scheme and break
        // under https.
        expect(io).toHaveBeenCalledWith({ transports: ['websocket'] });
        expect(io.mock.calls[0]).toHaveLength(1);
    });

    test('names no scheme or host anywhere', async () => {
        const { SERVER_URL } = await loadSocketModule('');
        expect(SERVER_URL).not.toMatch(/https?:/);
        expect(SERVER_URL).not.toMatch(/127\.0\.0\.1|localhost/);
    });

    test('reports the origin in words for log messages', async () => {
        const { SERVER_LABEL } = await loadSocketModule('');
        expect(SERVER_LABEL).toBe('the page origin');
    });
});

describe('with VITE_SERVER_URL unset (local development)', () => {
    test('keeps the dev backend so npm start needs no configuration', async () => {
        const { createSocket, SERVER_URL } = await loadSocketModule(undefined);
        createSocket();

        expect(SERVER_URL).toBe('http://127.0.0.1:5050');
        expect(io).toHaveBeenCalledWith('http://127.0.0.1:5050', { transports: ['websocket'] });
    });
});

describe('with an explicit VITE_SERVER_URL', () => {
    test('is honoured, for an API on a different host', async () => {
        const { createSocket } = await loadSocketModule('https://api.example.com');
        createSocket();
        expect(io).toHaveBeenCalledWith('https://api.example.com', { transports: ['websocket'] });
    });
});
