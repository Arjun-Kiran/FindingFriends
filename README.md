# Finding Friends (Zhao Pengyou / 找朋友)

A multiplayer web-based implementation of the Chinese trick-taking card game "Looking for Friends" (Zhǎo Péngyou). Supports 5-12 players with variable hidden partnerships, trump declaration, and level progression. See [ZhaoPengyou_Rules.md](ZhaoPengyou_Rules.md) for full game rules.

## Tech Stack

- **Backend**: Python, Flask, Flask-SocketIO (threading mode), gunicorn, SQLite
- **Frontend**: React 19, Vite, Socket.IO client
- **Communication**: WebSocket for real-time game events, REST for game creation/joining

## Project Structure

```
backend_code/       Flask backend (port 5050)
frontend_code/      React frontend (port 3000)
setup.sh            One-command setup for a new machine
ZhaoPengyou_Rules.md  Full game rules reference
```

## Setup

On a machine that has never run this before:

```bash
git clone <this repo>
cd FindingFriends
bash setup.sh
```

`setup.sh` checks for everything the project needs, offers to install anything
missing, builds the backend virtualenv and the frontend `node_modules`, and then
runs both test suites so you find out the machine is broken now rather than at
the first game. It never starts a server.

| Flag | What it does |
| --- | --- |
| *(none)* | Check, and ask before installing anything |
| `--yes` | Assume yes to every prompt — unattended installs |
| `--check-only` | Report what is missing, change nothing, exit non-zero if there are gaps |
| `--skip-tests` | Skip the verification test run |

### Platform notes

**macOS** — needs [Homebrew](https://brew.sh); `setup.sh` offers to install it if
it is absent. Note that the system `python3` is 3.9 and too old, so Python gets
installed either way.

**Ubuntu / Debian** — installs via `apt`, so it will ask for `sudo`. Ubuntu 24.04
and newer ship a new enough Python. On 22.04 the distro Python is 3.10, and
`setup.sh` will point you at [pyenv](https://github.com/pyenv/pyenv#installation)
to get the pinned version.

**Windows** — use **WSL2**, not native Windows or Git Bash. This is not a shell
preference: the backend is served by gunicorn, which imports `fcntl`, a
POSIX-only module that does not exist on Windows, and the kill scripts need
`pgrep` and `lsof`. In PowerShell **as Administrator**:

```powershell
wsl --install -d Ubuntu
```

Reboot, open the Ubuntu shell, and from there it is the Ubuntu path above:

```bash
sudo apt update && sudo apt install -y git
git clone <this repo>
cd FindingFriends
bash setup.sh
```

The dev servers bind on ports 3000 and 5050 inside WSL, and Windows forwards
`localhost` to them, so `http://localhost:3000` works in a normal Windows
browser. Keep the clone on the Linux filesystem (`~/`), not under `/mnt/c` —
`node_modules` on a mounted Windows drive is slow enough to be painful.

### Prerequisites, if you would rather install them yourself

| | Pinned | Minimum | Pinned in |
| --- | --- | --- | --- |
| Python | 3.13.12 | 3.12 | [.python-version](.python-version) |
| Node.js | 24 | 20.19 | [frontend_code/.nvmrc](frontend_code/.nvmrc) |
| npm | — | 10 | `engines` in [frontend_code/package.json](frontend_code/package.json) |

The pins are what the project is developed and tested against; the minimums are
what it actually needs. [pyenv](https://github.com/pyenv/pyenv) and
[nvm](https://github.com/nvm-sh/nvm) are optional but recommended — the run
scripts pick up the pinned versions automatically when they are installed, and
warn and carry on when they are not.

Then, by hand:

```bash
python3 -m venv backend_code/backend_venv
backend_code/backend_venv/bin/pip install -r backend_code/requirement.txt -r backend_code/requirement-dev.txt
cd frontend_code && npm ci
```

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

## Tests

```bash
cd backend_code && backend_venv/bin/python -m pytest -q
cd frontend_code && npm test
```

`run_flask_server.sh` also runs the backend suite before it starts serving, so a
failing test stops the server from coming up.

## Troubleshooting

**`bash setup.sh` says Python is too old.** The system Python is often behind —
3.9 on macOS, 3.10 on Ubuntu 22.04. Install [pyenv](https://github.com/pyenv/pyenv#installation),
then `pyenv install 3.13.12` from the project root, which reads `.python-version`.

**`nvm: command not found` right after `setup.sh` installed it.** nvm adds itself
to your shell profile, which the current shell has already read. Open a new
terminal, or `export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"`.

**Port 3000 or 5050 is already in use.** `bash kill_all.sh` sweeps both.

**The lobby never connects, or the game freezes after joining.** The WebSocket is
separate from the HTTP proxy — see [frontend_code/README.md](frontend_code/README.md).
Check the browser console; the frontend logs `connect_error` and disconnects.

**Everything installed, but a test fails.** Re-run `bash setup.sh` — it is safe
to run repeatedly and will rebuild a virtualenv left over from an older Python.

## How to Play

1. Open `http://localhost:3000`
2. One player creates a game and shares the game code
3. Other players join using the game code (minimum 5 players)
4. The host starts the game from the lobby
5. The alpha player declares trump, calls friend cards, and exchanges the kitty
6. Players play tricks — the alpha team tries to prevent defenders from scoring points
7. Winners advance levels; first team past Ace wins
