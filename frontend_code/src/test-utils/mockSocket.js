/* Minimal stand-in for a socket.io client.
 * Records emits so tests can assert what was sent, and exposes `fire()`
 * so tests can simulate server pushes. */
export const createMockSocket = () => {
    const handlers = {};

    return {
        // Stands in for a live connection, like the real socket a component is
        // handed after the lobby. Set false to render the disconnected state.
        connected: true,

        on: vi.fn((event, callback) => {
            handlers[event] = handlers[event] || [];
            handlers[event].push(callback);
        }),
        off: vi.fn((event, callback) => {
            handlers[event] = (handlers[event] || []).filter(h => h !== callback);
        }),
        emit: vi.fn(),
        disconnect: vi.fn(),

        /** Simulate the server pushing an event to this client. */
        fire: (event, data) => {
            (handlers[event] || []).forEach(handler => handler(data));
        },

        /** Payload of the last emit for `event`, or undefined. */
        lastEmit(event) {
            const call = [...this.emit.mock.calls].reverse().find(c => c[0] === event);
            return call ? call[1] : undefined;
        },
    };
};
