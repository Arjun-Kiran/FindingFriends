import { copyText } from './copyText';

/* The bug this guards against: on http:// with an IP address the browser does
 * not define navigator.clipboard, and the old code reached straight through it.
 */

const withContext = ({ secure, clipboard, exec }) => {
    Object.defineProperty(window, 'isSecureContext', {
        value: secure, configurable: true, writable: true,
    });
    Object.defineProperty(navigator, 'clipboard', {
        value: clipboard, configurable: true, writable: true,
    });
    document.execCommand = exec;
};

afterEach(() => {
    vi.restoreAllMocks();
});

test('uses the clipboard API in a secure context', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    const exec = vi.fn(() => true);
    withContext({ secure: true, clipboard: { writeText }, exec });

    await expect(copyText('happy-game-code')).resolves.toBe(true);
    expect(writeText).toHaveBeenCalledWith('happy-game-code');
    expect(exec).not.toHaveBeenCalled();
});

test('falls back when navigator.clipboard is undefined', async () => {
    // Exactly the droplet case: plain http:// on an IP.
    const exec = vi.fn(() => true);
    withContext({ secure: false, clipboard: undefined, exec });

    await expect(copyText('happy-game-code')).resolves.toBe(true);
    expect(exec).toHaveBeenCalledWith('copy');
});

test('does not throw when navigator.clipboard is undefined', async () => {
    withContext({ secure: false, clipboard: undefined, exec: () => true });
    // The old implementation threw a TypeError here.
    await expect(copyText('code')).resolves.not.toThrow;
});

test('falls back when the clipboard API rejects', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('denied'));
    const exec = vi.fn(() => true);
    withContext({ secure: true, clipboard: { writeText }, exec });

    await expect(copyText('code')).resolves.toBe(true);
    expect(exec).toHaveBeenCalledWith('copy');
});

test('reports failure when neither route works', async () => {
    withContext({ secure: false, clipboard: undefined, exec: () => false });
    await expect(copyText('code')).resolves.toBe(false);
});

test('leaves no scratch textarea behind', async () => {
    withContext({ secure: false, clipboard: undefined, exec: () => true });
    await copyText('code');
    expect(document.querySelectorAll('textarea')).toHaveLength(0);
});

test('removes the scratch textarea even when execCommand throws', async () => {
    withContext({
        secure: false,
        clipboard: undefined,
        exec: () => { throw new Error('nope'); },
    });
    await expect(copyText('code')).resolves.toBe(false);
    expect(document.querySelectorAll('textarea')).toHaveLength(0);
});
