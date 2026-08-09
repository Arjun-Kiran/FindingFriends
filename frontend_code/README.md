# Finding Friends — frontend

React 19 + Vite. See the [root README](../README.md) for running the full stack
(backend and frontend together).

## Scripts

| Command | What it does |
| --- | --- |
| `npm start` | Dev server on port 3000, with HMR |
| `npm run build` | Production build into `dist/` |
| `npm run preview` | Serve the built `dist/` locally, to check a build |
| `npm test` | Run the test suite once (Vitest) |
| `npm run test:watch` | Re-run tests as files change |

## Talking to the backend

Two different paths, and they are configured separately:

- **HTTP** (`/create`, `/join`, `/game`) goes through the dev proxy in
  `vite.config.js`, so `api/client.js` uses relative paths and there is no
  cross-origin request in development.
- **WebSockets bypass that proxy entirely.** `api/socket.js` connects to
  `VITE_SERVER_URL`, defaulting to `http://127.0.0.1:5050`.

`VITE_SERVER_URL` is read at **build** time, not runtime — a deployed build
needs it set before `npm run build`, not when the server starts.

## Layout

```
src/
  api/          HTTP client, socket setup, event names, logger
  components/   UI; Game/ holds the in-game screen, Game/phases/ one file per phase
  hooks/        Socket lifecycle, card selection, event toasts
  constants/    Card and phase enums shared with the backend's vocabulary
  test-utils/   Fixtures mirroring the backend's PlayerView, and a socket stand-in
```

Files containing JSX use the `.jsx` extension — Vite only parses JSX there.
