#!/usr/bin/env bash
#
# Finding Friends — one-command setup for a fresh machine.
#
# Checks for the toolchain the project needs, offers to install what is
# missing, builds the backend virtualenv and the frontend node_modules, and
# runs both test suites to prove the machine actually works.
#
# Supported: macOS, Ubuntu/Debian, and WSL2 (Ubuntu) on Windows.
#
# Native Windows is deliberately NOT supported. run_flask_server.sh serves the
# app with gunicorn, which imports fcntl — a POSIX-only module with no Windows
# equivalent. The kill scripts also need pgrep and lsof. Install WSL2 and run
# this from inside Ubuntu; see the README.
#
# Usage:
#   bash setup.sh                # check, and prompt before installing anything
#   bash setup.sh --yes          # assume yes to every prompt (unattended)
#   bash setup.sh --check-only   # report gaps, change nothing, exit 1 if any
#   bash setup.sh --skip-tests   # skip the verification test run
#
# Deliberately not using `set -e`: a missing prerequisite should be collected
# and reported alongside the others, not abort the run on the first one.
# Re-exec under bash when we were started by some other shell.
#
# `sh setup.sh` on Ubuntu runs dash, which has neither `set -o pipefail` nor
# ${BASH_SOURCE} — it fails on the very next line with a confusing "Illegal
# option" before printing anything useful. The shebang already asks for bash;
# this covers the case where the shebang was bypassed. Kept in strict POSIX
# syntax so that dash can parse it in order to get here at all.
if [ -z "${BASH_VERSION:-}" ]; then
    if command -v bash > /dev/null 2>&1; then
        exec bash "$0" "$@"
    fi
    echo "setup.sh needs bash, and this system does not have it." >&2
    echo "On Ubuntu/Debian:  sudo apt-get install -y bash" >&2
    exit 1
fi

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1

# ---------------------------------------------------------------------------
# Versions
#
# PINNED_* are what the project develops against, read from the same files the
# run scripts read so there is only one place to bump them.
#
# MIN_* are what the project actually needs. They are looser than the pins on
# purpose: requiring an exact patch release on a fresh machine means an install
# of pyenv/nvm before anything can run, and nothing here needs 3.13.12 over
# 3.12. Anything at or above the minimum is accepted with a note.
# ---------------------------------------------------------------------------
PINNED_PYTHON="$(tr -d '[:space:]' < .python-version 2>/dev/null)"
PINNED_NODE="$(tr -d '[:space:]' < frontend_code/.nvmrc 2>/dev/null)"
MIN_PYTHON="3.12"
MIN_NODE="20.19.0"   # matches the `engines` field in frontend_code/package.json

# Pinned so a bad upstream push cannot change what this script runs. Bump
# occasionally: https://github.com/nvm-sh/nvm/releases
NVM_INSTALL_TAG="v0.40.3"

ASSUME_YES=0
CHECK_ONLY=0
SKIP_TESTS=0

for arg in "$@"; do
    case "$arg" in
        --yes|-y)      ASSUME_YES=1 ;;
        --check-only)  CHECK_ONLY=1 ;;
        --skip-tests)  SKIP_TESTS=1 ;;
        --help|-h)     awk 'NR<3{next} /^# Deliberately/{exit} !/^#/{exit} {sub(/^# ?/,""); print}' "$0"; exit 0 ;;
        *)             echo "Unknown option: $arg (try --help)" >&2; exit 2 ;;
    esac
done

# ---------------------------------------------------------------------------
# Output helpers.
#
# Status is carried by the word and the symbol, never by colour alone — the
# symbols have to survive a monochrome terminal, a log file, and a reader who
# cannot separate red from green.
# ---------------------------------------------------------------------------
BOLD=""; DIM=""; RESET=""
if [ -t 1 ] && command -v tput >/dev/null 2>&1 && [ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]; then
    BOLD="$(tput bold)"; DIM="$(tput dim)"; RESET="$(tput sgr0)"
fi

GAP_COUNT=0
GAP_LIST=""

step() { printf '\n%s==> %s%s\n' "$BOLD" "$1" "$RESET"; }
ok()   { printf '  [ ok ]   %s\n' "$1"; }
info() { printf '  %s[ .. ]   %s%s\n' "$DIM" "$1" "$RESET"; }
warn() { printf '  [ note ] %s\n' "$1"; }
bad()  { printf '  [ MISS ] %s\n' "$1"; GAP_COUNT=$((GAP_COUNT + 1)); GAP_LIST="$GAP_LIST$1\n"; }
die()  { printf '\n[ STOP ] %s\n' "$1" >&2; exit 1; }

# Version comparison: true when $1 >= $2. sort -V handles 3.10 vs 3.9 correctly,
# which a string or float comparison does not.
ver_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]; }

# ask "question" -> 0 for yes. --check-only and a non-interactive shell both
# answer no, so this script never installs anything unattended by accident.
ask() {
    if [ "$CHECK_ONLY" -eq 1 ]; then return 1; fi
    if [ "$ASSUME_YES" -eq 1 ]; then printf '  [ yes ]  %s\n' "$1"; return 0; fi
    if [ ! -t 0 ]; then
        printf '  [ note ] %s -- skipped, no terminal to ask on (use --yes)\n' "$1"
        return 1
    fi
    local reply
    printf '  %s [Y/n] ' "$1"
    read -r reply
    case "$reply" in [nN]*) return 1 ;; *) return 0 ;; esac
}

run() {
    info "$*"
    "$@"
}

# ---------------------------------------------------------------------------
# Platform
# ---------------------------------------------------------------------------
OS=""
PKG=""
IS_WSL=0

case "$(uname -s)" in
    Darwin)
        OS="macOS"
        command -v brew >/dev/null 2>&1 && PKG="brew"
        ;;
    Linux)
        OS="Linux"
        grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null && { IS_WSL=1; OS="WSL2"; }
        command -v apt-get >/dev/null 2>&1 && PKG="apt"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        die "Native Windows is not supported.

Git Bash and MSYS cannot run this project: the backend is served by gunicorn,
which needs the POSIX-only fcntl module, and the kill scripts need pgrep/lsof.

Install WSL2 with Ubuntu, then clone and run this script from inside it:

    wsl --install -d Ubuntu          (in PowerShell as Administrator, then reboot)
    wsl                              (opens the Ubuntu shell)
    git clone <this repo> && cd FindingFriends && bash setup.sh

See the README for the full walkthrough."
        ;;
    *)
        OS="$(uname -s)"
        warn "Unrecognised platform '$OS'. Continuing, but nothing here is tested on it."
        ;;
esac

printf '%sFinding Friends — setup%s\n' "$BOLD" "$RESET"
printf '  platform:   %s%s\n' "$OS" "$([ "$IS_WSL" -eq 1 ] && echo ' (Windows Subsystem for Linux)')"
printf '  packages:   %s\n' "${PKG:-none detected}"
printf '  python pin: %s (minimum %s)\n' "${PINNED_PYTHON:-unset}" "$MIN_PYTHON"
printf '  node pin:   %s (minimum %s)\n' "${PINNED_NODE:-unset}" "$MIN_NODE"
[ "$CHECK_ONLY" -eq 1 ] && printf '  mode:       check only, nothing will be changed\n'

sudo_apt() {
    # Ubuntu images used as containers often run as root with no sudo installed.
    if [ "$(id -u)" -eq 0 ]; then
        DEBIAN_FRONTEND=noninteractive apt-get "$@"
    else
        sudo DEBIAN_FRONTEND=noninteractive apt-get "$@"
    fi
}

APT_UPDATED=0
apt_install() {
    if [ "$APT_UPDATED" -eq 0 ]; then
        info "apt-get update"
        sudo_apt update -qq || return 1
        APT_UPDATED=1
    fi
    info "apt-get install -y $*"
    sudo_apt install -y "$@"
}

# ---------------------------------------------------------------------------
# A package manager to install things with
# ---------------------------------------------------------------------------
step "Package manager"

if [ -n "$PKG" ]; then
    ok "$PKG is available"
elif [ "$OS" = "macOS" ]; then
    bad "Homebrew is not installed (needed to install Python and Node)"
    if ask "Install Homebrew now?"; then
        run /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || die "Homebrew install failed."
        # A fresh install is not on PATH until the shell re-reads its profile.
        for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
            [ -x "$candidate" ] && eval "$("$candidate" shellenv)" && break
        done
        command -v brew >/dev/null 2>&1 && { PKG="brew"; ok "Homebrew installed"; GAP_COUNT=0; GAP_LIST=""; }
    else
        warn "Install it yourself from https://brew.sh, then re-run this script."
    fi
else
    warn "No supported package manager found. Prerequisites must be installed by hand."
fi

# ---------------------------------------------------------------------------
# Small tools the later steps and the run/kill scripts shell out to
#
# This runs BEFORE Python and Node on purpose: the nvm installer is fetched
# with curl, so a bare box that is missing curl cannot install Node at all.
# ---------------------------------------------------------------------------
step "Supporting tools"

# curl: needed below to fetch the nvm installer.
# git:  needed to clone, and by npm for any git-hosted dependency.
MISSING_TOOLS=""
for tool in curl git; do
    if command -v "$tool" >/dev/null 2>&1; then
        ok "$tool"
    else
        bad "$tool is not installed"
        MISSING_TOOLS="$MISSING_TOOLS $tool"
    fi
done

# pgrep and lsof: kill_backend.sh and kill_frontend.sh use both to find stray
# servers. Not fatal, but kill_all.sh silently does nothing without them.
MISSING_PROCS=""
command -v pgrep >/dev/null 2>&1 || MISSING_PROCS="$MISSING_PROCS procps"
command -v lsof  >/dev/null 2>&1 || MISSING_PROCS="$MISSING_PROCS lsof"
if [ -z "$MISSING_PROCS" ]; then
    ok "pgrep and lsof (used by the kill scripts)"
else
    bad "missing${MISSING_PROCS} — kill_all.sh will not find running servers"
fi

WANTED="${MISSING_TOOLS}${MISSING_PROCS}"
WANTED="${WANTED# }"
if [ -n "$WANTED" ]; then
    case "$PKG" in
        # Unquoted $WANTED on purpose: it is a word list, not one package name.
        apt)  ask "Install $WANTED?" && apt_install $WANTED ;;
        brew) ask "Install $WANTED?" && run brew install $WANTED ;;
        *)    warn "Install these by hand: $WANTED" ;;
    esac
fi

# ---------------------------------------------------------------------------
# Python
#
# pyenv is optional. run_flask_server.sh uses it when present to match the pin
# exactly, and falls back to whatever python3 is on PATH otherwise — so this
# script only insists on a python3 at or above MIN_PYTHON.
# ---------------------------------------------------------------------------
step "Python"

PYTHON=""

py_version() { "$1" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null; }

# pyenv compiles CPython from source, which needs headers the base image lacks.
# Skipping any of these does not fail the build loudly — it silently produces a
# Python without ssl, sqlite3 or lzma, which this project then fails to import.
install_cpython_build_deps() {
    [ "$PKG" = "apt" ] || return 0
    apt_install build-essential libssl-dev zlib1g-dev libbz2-dev \
        libreadline-dev libsqlite3-dev curl libncursesw5-dev \
        xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
}

# Install pyenv and build the pinned Python with it. For distributions whose
# own Python is too old — Ubuntu 22.04 ships 3.10, and is supported to 2027 —
# this is the only route to a usable interpreter that does not mean adding a
# third-party PPA or upgrading the release.
install_pyenv_and_python() {
    install_cpython_build_deps
    apt_install git >/dev/null 2>&1 || true

    if ! command -v curl >/dev/null 2>&1; then
        warn "curl is needed to fetch the pyenv installer."
        return 1
    fi
    run bash -c "curl -fsSL https://pyenv.run | bash" || return 1

    # pyenv is per-user under $HOME and is not on PATH until a profile is
    # re-read, so put it there for the rest of this run.
    PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
    export PYENV_ROOT
    export PATH="$PYENV_ROOT/bin:$PATH"
    command -v pyenv >/dev/null 2>&1 || { warn "pyenv did not land on PATH."; return 1; }

    run pyenv install -s "$PINNED_PYTHON" || return 1
    prefix="$(pyenv prefix "$PINNED_PYTHON" 2>/dev/null)"
    [ -x "$prefix/bin/python3" ] || return 1
    PYTHON="$prefix/bin/python3"

    warn "pyenv is installed but not yet in your shell profile. Add to ~/.bashrc:"
    warn '  export PYENV_ROOT="$HOME/.pyenv"'
    warn '  export PATH="$PYENV_ROOT/bin:$PATH"'
    warn '  eval "$(pyenv init -)"'
    return 0
}

# 1. pyenv, if the user already has it — it is the only way to get the exact pin.
if command -v pyenv >/dev/null 2>&1; then
    ok "pyenv is installed"
    if prefix="$(pyenv prefix "$PINNED_PYTHON" 2>/dev/null)" && [ -x "$prefix/bin/python3" ]; then
        PYTHON="$prefix/bin/python3"
        ok "Python $PINNED_PYTHON present via pyenv (matches the pin)"
    else
        bad "pyenv does not have the pinned Python $PINNED_PYTHON"
        if ask "Run 'pyenv install $PINNED_PYTHON'? (compiles from source, takes a few minutes)"; then
            install_cpython_build_deps
            if run pyenv install -s "$PINNED_PYTHON"; then
                prefix="$(pyenv prefix "$PINNED_PYTHON" 2>/dev/null)"
                [ -x "$prefix/bin/python3" ] && { PYTHON="$prefix/bin/python3"; ok "Python $PINNED_PYTHON installed"; }
            fi
        fi
    fi
fi

# 2. Otherwise the newest system python3 that clears the minimum.
if [ -z "$PYTHON" ]; then
    for candidate in python3.14 python3.13 python3.12 python3; do
        path="$(command -v "$candidate" 2>/dev/null)" || continue
        v="$(py_version "$path")" || continue
        [ -n "$v" ] || continue
        if ver_ge "$v" "$MIN_PYTHON"; then
            PYTHON="$path"
            if [ "$v" = "$PINNED_PYTHON" ]; then
                ok "Python $v at $path (matches the pin)"
            else
                ok "Python $v at $path"
                warn "Not the pinned $PINNED_PYTHON, but above the $MIN_PYTHON minimum. Install pyenv if you want an exact match."
            fi
            break
        fi
    done
fi

# 3. Nothing usable — offer to install one.
if [ -z "$PYTHON" ]; then
    found="$(command -v python3 >/dev/null 2>&1 && py_version python3 || echo none)"
    bad "No Python >= $MIN_PYTHON (found: $found)"
    case "$PKG" in
        brew)
            if ask "Install Python via 'brew install python@3.13'?"; then
                run brew install python@3.13 && PYTHON="$(command -v python3.13 || command -v python3)"
            fi
            ;;
        apt)
            # Ubuntu 24.04 ships 3.12; 22.04 ships 3.10 and needs pyenv or a PPA.
            if ask "Install Python via apt?"; then
                apt_install python3 python3-venv python3-pip
                cand="$(command -v python3)"
                if [ -n "$cand" ] && ver_ge "$(py_version "$cand")" "$MIN_PYTHON"; then
                    PYTHON="$cand"
                else
                    warn "This distribution's python3 is $(py_version "$cand"), older than $MIN_PYTHON."
                    warn "Ubuntu 22.04 and older ship a Python this project cannot use."
                    if ask "Install pyenv and build Python $PINNED_PYTHON from source? (several minutes)"; then
                        install_pyenv_and_python \
                            && ok "Python $PINNED_PYTHON built via pyenv" \
                            || warn "pyenv route failed — upgrade to Ubuntu 24.04+, or install Python $MIN_PYTHON+ by hand."
                    fi
                fi
            fi
            ;;
        *)
            warn "Install Python $PINNED_PYTHON by hand, then re-run this script."
            ;;
    esac
fi

[ -n "$PYTHON" ] && ok "Using $PYTHON ($(py_version "$PYTHON"))"

# venv is a separate package on Debian and Ubuntu, and its absence only shows
# up as a confusing ensurepip error partway through creating the environment.
if [ -n "$PYTHON" ] && [ "$PKG" = "apt" ]; then
    if ! "$PYTHON" -c 'import ensurepip' >/dev/null 2>&1; then
        bad "python3-venv is missing (needed to create the backend virtualenv)"
        if ask "Install python3-venv and python3-pip?"; then
            apt_install python3-venv python3-pip
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Node
#
# nvm is preferred because .nvmrc pins the version and run_frontend.sh reads it,
# but as with Python any Node above the minimum is accepted.
# ---------------------------------------------------------------------------
step "Node.js"

NODE_READY=0

load_nvm() {
    export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
    if [ -s "$NVM_DIR/nvm.sh" ]; then . "$NVM_DIR/nvm.sh"; return 0; fi
    # Homebrew installs nvm outside $HOME.
    if [ "$PKG" = "brew" ]; then
        local p; p="$(brew --prefix nvm 2>/dev/null)/nvm.sh"
        if [ -s "$p" ]; then export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"; . "$p"; return 0; fi
    fi
    return 1
}

# Install and select the pinned Node, IN THIS SHELL.
#
# nvm works by mutating PATH, so it cannot be run inside a subshell: a
# `( cd frontend_code && nvm use )` sets PATH only inside the parentheses and
# the change is gone by the time npm is needed. That is why the version is
# passed explicitly instead of letting `nvm install` discover .nvmrc by cwd —
# it keeps the call in the current shell without a cd.
nvm_activate() {
    nvm install "$PINNED_NODE" >/dev/null 2>&1 || return 1
    nvm use "$PINNED_NODE" >/dev/null 2>&1 || return 1
    command -v npm >/dev/null 2>&1
}

if load_nvm; then
    ok "nvm is installed"
    if nvm_activate; then
        ok "Node $(node -v) available via nvm (matches the .nvmrc pin of $PINNED_NODE)"
        NODE_READY=1
    else
        warn "nvm could not install Node $PINNED_NODE from frontend_code/.nvmrc"
    fi
fi

if [ "$NODE_READY" -eq 0 ] && command -v node >/dev/null 2>&1; then
    nv="$(node -v 2>/dev/null | sed 's/^v//')"
    if ver_ge "$nv" "$MIN_NODE"; then
        ok "Node $nv at $(command -v node)"
        [ "${nv%%.*}" = "$PINNED_NODE" ] || warn "Not the pinned major $PINNED_NODE, but above the $MIN_NODE minimum."
        NODE_READY=1
    else
        bad "Node $nv is below the $MIN_NODE minimum"
    fi
fi

if [ "$NODE_READY" -eq 0 ]; then
    command -v node >/dev/null 2>&1 || bad "Node.js is not installed"
    if ask "Install nvm and Node $PINNED_NODE? (nvm keeps it per-user, no sudo)"; then
        if command -v curl >/dev/null 2>&1; then
            run bash -c "curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/$NVM_INSTALL_TAG/install.sh | bash"
        elif command -v wget >/dev/null 2>&1; then
            run bash -c "wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/$NVM_INSTALL_TAG/install.sh | bash"
        else
            warn "Neither curl nor wget is available to fetch the nvm installer."
        fi
        if load_nvm && nvm_activate; then
            ok "Node $(node -v) installed via nvm"
            NODE_READY=1
            warn "nvm added itself to your shell profile, which this shell has already"
            warn "read. The rest of this script is fine, but for a new terminal later:"
            warn "  export NVM_DIR=\"\$HOME/.nvm\" && . \"\$NVM_DIR/nvm.sh\""
        fi
    elif [ "$PKG" = "brew" ] && ask "Install Node via 'brew install node' instead?"; then
        run brew install node && NODE_READY=1
    fi
fi

# ---------------------------------------------------------------------------
# Stop here if we are only reporting, or if a prerequisite is still missing
# ---------------------------------------------------------------------------
if [ "$CHECK_ONLY" -eq 1 ]; then
    step "Check complete"
    if [ "$GAP_COUNT" -eq 0 ]; then
        ok "Everything this project needs is present."
        exit 0
    fi
    printf '  %d thing(s) missing:\n' "$GAP_COUNT"
    printf '%b' "$GAP_LIST" | while IFS= read -r g; do
        [ -n "$g" ] && printf '    - %s\n' "$g"
    done
    printf '\n  Re-run without --check-only to be prompted through installing them.\n'
    exit 1
fi

[ -n "$PYTHON" ]        || die "No usable Python. Install Python >= $MIN_PYTHON and re-run."
[ "$NODE_READY" -eq 1 ] || die "No usable Node. Install Node >= $MIN_NODE and re-run."

# npm ships with node, but it is reachable only if the PATH work above landed.
command -v npm >/dev/null 2>&1 || die "node is available but npm is not on PATH.
Open a new terminal so your shell profile is re-read, then run this again."

# ---------------------------------------------------------------------------
# Backend dependencies
# ---------------------------------------------------------------------------
step "Backend dependencies"

VENV="$ROOT/backend_code/backend_venv"

# A virtualenv is only usable if pip works inside it. Checking for the
# interpreter alone is not enough, and the difference is not academic:
# `python3 -m venv` on a Debian/Ubuntu box without python3-venv still lays down
# bin/python and then fails at the ensurepip step, leaving a tree that looks
# complete and has no pip. A later run that installs python3-venv would happily
# reuse that tree and fall over on the first pip install.
#
# Also catches the older case this used to check for: a venv whose base Python
# has been removed or upgraded, leaving a dangling symlink.
venv_is_healthy() {
    [ -x "$1/bin/python" ] || return 1
    "$1/bin/python" -m pip --version >/dev/null 2>&1
}

create_venv() {
    run "$PYTHON" -m venv "$VENV" || return 1
    venv_is_healthy "$VENV" && return 0
    # The venv module can succeed while skipping pip. ensurepip recovers that
    # without a rebuild when the stdlib module is present.
    warn "Virtualenv has no pip; running ensurepip."
    "$VENV/bin/python" -m ensurepip --upgrade >/dev/null 2>&1
    venv_is_healthy "$VENV"
}

if [ -d "$VENV" ] && ! venv_is_healthy "$VENV"; then
    warn "Existing backend_venv has no working pip — rebuilding it."
    rm -rf "$VENV"
fi

if [ ! -d "$VENV" ]; then
    create_venv || die "Could not create a working virtualenv at $VENV.
The interpreter was built but pip is not available inside it.
On Ubuntu/Debian:  sudo apt-get install -y python3-venv python3-pip
Then remove backend_code/backend_venv and run this script again."
    ok "Created backend_code/backend_venv"
else
    ok "backend_code/backend_venv already exists"
    existing="$(sed -n 's/^version *= *//p' "$VENV/pyvenv.cfg" 2>/dev/null)"
    wanted="$(py_version "$PYTHON")"
    if [ -n "$existing" ] && [ "$existing" != "$wanted" ]; then
        warn "It was built with Python $existing, but $wanted is now selected."
        if ask "Rebuild it?"; then
            rm -rf "$VENV"
            create_venv || die "Could not recreate the virtualenv at $VENV"
        fi
    fi
fi

VENV_PY="$VENV/bin/python"
run "$VENV_PY" -m pip install --quiet --upgrade pip || warn "Could not upgrade pip; continuing."
# Dev dependencies too: this script, and run_flask_server.sh, both run pytest.
run "$VENV_PY" -m pip install --quiet \
    -r backend_code/requirement.txt \
    -r backend_code/requirement-dev.txt \
    || die "Installing backend dependencies failed."
ok "Backend dependencies installed"

# ---------------------------------------------------------------------------
# Frontend dependencies
# ---------------------------------------------------------------------------
step "Frontend dependencies"

if [ -f frontend_code/package-lock.json ]; then
    # npm ci is the reproducible one: it installs exactly the lockfile and
    # nothing else. It also deletes node_modules first, so it is only worth
    # paying for when the tree is absent or stale.
    if [ -d frontend_code/node_modules ]; then
        info "node_modules exists; running npm install to reconcile it with the lockfile"
        (cd frontend_code && npm install --no-fund --no-audit) || die "npm install failed."
    else
        (cd frontend_code && npm ci --no-fund --no-audit) || die "npm ci failed."
    fi
else
    warn "No package-lock.json — versions will be resolved fresh, so this machine"
    warn "may not get the same dependency tree as another. Commit the lockfile."
    (cd frontend_code && npm install --no-fund --no-audit) || die "npm install failed."
fi
ok "Frontend dependencies installed"

# ---------------------------------------------------------------------------
# Verify
#
# The point of running the suites here is to catch a bad install now, on a
# machine nobody has tried to play on yet, rather than at the first game.
# ---------------------------------------------------------------------------
TESTS_FAILED=0
if [ "$SKIP_TESTS" -eq 1 ]; then
    step "Verification"
    warn "Skipped (--skip-tests)."
else
    step "Verifying the backend"
    if (cd backend_code && "$VENV_PY" -m pytest -q); then
        ok "Backend tests passed"
    else
        TESTS_FAILED=1
        bad "Backend tests failed"
    fi

    step "Verifying the frontend"
    if (cd frontend_code && npm test --silent); then
        ok "Frontend tests passed"
    else
        TESTS_FAILED=1
        bad "Frontend tests failed"
    fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
step "Setup complete"

if [ "$TESTS_FAILED" -eq 1 ]; then
    printf '  Dependencies are installed, but the test suites did not pass.\n'
    printf '  The output above says which. Fix that before trying to play.\n\n'
fi

cat <<EOF
  Start the game:

      bash run_all.sh

  Then open http://localhost:3000 — one player creates a game and shares the
  code, and everyone else joins with it. Five players minimum.

  Stop it again:

      bash kill_all.sh

EOF

exit "$TESTS_FAILED"
