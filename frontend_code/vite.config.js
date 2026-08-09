import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [react()],

    server: {
        port: 3000,
        // Replaces CRA's "proxy" field: same-origin HTTP calls in dev, so
        // api/client.js can keep using relative paths like /create.
        // Websockets bypass this — see api/socket.js.
        proxy: {
            '/create': 'http://localhost:5050',
            '/join': 'http://localhost:5050',
            '/game': 'http://localhost:5050',
        },
    },

    test: {
        globals: true,          // describe/test/expect without importing them
        environment: 'jsdom',
        setupFiles: './src/setupTests.js',
        css: true,
    },
});
