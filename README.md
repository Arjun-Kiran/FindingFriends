# Finding Friends (Zhao Pengyou / 找朋友)

A multiplayer web-based implementation of the Chinese trick-taking card game "Looking for Friends" (Zhǎo Péngyou). Supports 5-12 players with variable hidden partnerships, trump declaration, and level progression. See [ZhaoPengyou_Rules.md](ZhaoPengyou_Rules.md) for full game rules.

## Tech Stack

- **Backend**: Python, Flask, Flask-SocketIO, eventlet, SQLite
- **Frontend**: React 18, Socket.IO client
- **Communication**: WebSocket for real-time game events, REST for game creation/joining

## Project Structure

```
backend_code/       Flask backend (port 5050)
frontend_code/      React frontend (port 3000)
python_client/      Optional Python CLI client (WIP)
ZhaoPengyou_Rules.md  Full game rules reference
```

## Prerequisites

- Python 3.8+
- Node.js 16+
- npm

## Running the App

### Quick Start

From the project root:

```bash
bash run_all.sh
```

This starts the backend (in the background) and frontend. The game will be available at `http://localhost:3000`.

### Running Individually

**Backend:**

```bash
cd backend_code
bash run_flask_server.sh
```

This clears the database, creates a Python virtual environment (if needed), installs dependencies, runs tests, and starts gunicorn on port 5050. Use `--recreate-venv` to rebuild the virtual environment from scratch.

**Frontend:**

```bash
cd frontend_code
bash run_frontend.sh
```

This installs npm dependencies and starts the React dev server on port 3000. Use `--reinstall` to wipe and reinstall node_modules.

### Stopping

```bash
bash kill_all.sh
```

Or individually:

```bash
bash backend_code/kill_backend.sh
bash frontend_code/kill_frontend.sh
```

### Clearing the Database

The database is automatically cleared on each backend start. To clear it manually:

```bash
bash backend_code/clear_db.sh
```

## How to Play

1. Open `http://localhost:3000`
2. One player creates a game and shares the game code
3. Other players join using the game code (minimum 5 players)
4. The host starts the game from the lobby
5. The alpha player declares trump, calls friend cards, and exchanges the kitty
6. Players play tricks — the alpha team tries to prevent defenders from scoring points
7. Winners advance levels; first team past Ace wins
