import { watchGame } from './client';

const respond = (response) => {
    global.fetch = vi.fn(() => Promise.resolve(response));
};

test('watching asks the backend, and hands back what it says', async () => {
    respond({ ok: true, status: 200, json: () => Promise.resolve({ watcher_uuid: 'uuid-wes', player_token: 'token-wes' }) });

    const watcher = await watchGame('below-adopt-havoc', 'Wes');

    expect(global.fetch).toHaveBeenCalledWith('/watch/below-adopt-havoc?nick_name=Wes', {});
    expect(watcher.watcher_uuid).toBe('uuid-wes');
});

/* What a route the dev proxy does not forward looks like: the page, with a 200.
   It has to fail here, rather than reach a caller as an answer of null. */
test('a success that is not JSON is refused, not passed on as null', async () => {
    respond({ ok: true, status: 200, json: () => Promise.reject(new SyntaxError('Unexpected token <')) });

    await expect(watchGame('below-adopt-havoc', 'Wes')).rejects.toMatchObject({
        message: 'Unexpected response from the server',
        code: 'not_json',
    });
});
