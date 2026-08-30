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

`sh setup.sh` and `./setup.sh` work too — the script re-execs itself under bash
if another shell started it.

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
and newer ship a new enough Python and are used directly. On 22.04 the distro
Python is 3.10, which this project cannot use; `setup.sh` offers to install
[pyenv](https://github.com/pyenv/pyenv) and build the pinned Python from source
instead, which takes a few minutes. Both paths are tested from a bare image.

Node comes from [nvm](https://github.com/nvm-sh/nvm) rather than `apt`, because
the `nodejs` package is usually far behind the version Vite needs.

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

`run_all.sh` takes a mode.

| | `dev` (default) | `prod` |
| --- | --- | --- |
| Frontend | vite dev server, hot reload | built once into `dist/` |
| Served by | vite `:3000` + gunicorn `:5050` | gunicorn alone, one port |
| Bound to | `127.0.0.1` — this machine only | `0.0.0.0` — publicly reachable |
| Origins | two (vite proxies the API) | one (page, API and socket together) |
| Database | cleared on every start | preserved across restarts |
| Tests | run before serving | not run |

### Development

```bash
bash run_all.sh          # or: bash run_all.sh dev
```

Starts the backend in the background and the frontend in the foreground. The
game is at `http://localhost:3000`. Nothing is reachable from other machines.

### Production

```bash
bash run_all.sh prod                 # port 80, needs root
PORT=8080 bash run_all.sh prod       # unprivileged port
```

Builds the frontend and serves it from gunicorn, so the page, the REST
endpoints and the websocket all share **one origin on one port**. Hand out the
bare address — `http://<your-ip>` — and players go there and enter a game code.

One port is the whole point. The socket is built with an empty
`VITE_SERVER_URL`, which makes it connect back to whatever address the player
loaded, so the build contains no hostname and works unchanged on an IP, a
domain, or localhost. Nothing needs a second firewall hole.

Production deliberately does **not** go through `run_flask_server.sh`: that
script clears the database and runs the test suite before serving, which would
wipe every game in progress on each restart.

To keep it running after you log out:

```bash
nohup bash run_all.sh prod > prod.log 2>&1 &
```

That does not survive a reboot — use a systemd unit if you need it to.

Anyone who has the address can create or join a game; there is no
authentication. See `ProductionTasks.md`.

### Running the servers individually (development)

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

**`set: Illegal option -o pipefail`.** An old copy of `setup.sh` run as
`sh setup.sh`, where `/bin/sh` is dash on Ubuntu. Current versions re-exec
themselves under bash; `git pull` and try again.

**`nvm: command not found` in a new terminal after setup.** nvm and pyenv both
install themselves into your shell profile, which the shell running `setup.sh`
had already read. `setup.sh` handles this for its own run and prints the lines
to add. Open a new terminal, or:

```bash
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"
```

**`No module named pip` from inside `backend_venv`.** A virtualenv created
while `python3-venv` was missing has an interpreter but no pip. `setup.sh`
detects this and rebuilds; if you are on an older copy of the script, delete
`backend_code/backend_venv` and run it again.

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
