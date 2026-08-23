#!/bin/bash
echo $PWD

# Switch to the Node version pinned in .nvmrc, if nvm is installed.
# Without this the script runs on whatever Node the shell happens to be on,
# which may be older than vite requires.
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    . "$NVM_DIR/nvm.sh"
    if ! nvm use; then
        echo "Warning: could not use the Node version in .nvmrc (try 'nvm install')."
        echo "Continuing with $(node -v)."
    fi
fi

if [ "$1" = "--reinstall" ]; then
    echo "Deleting and reinstalling node_modules..."
    rm -rf node_modules
    npm install
    echo "Node modules reinstalled."
else
    npm install
fi

npm start
