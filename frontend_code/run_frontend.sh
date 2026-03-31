#!/bin/bash
echo $PWD

if [ "$1" = "--reinstall" ]; then
    echo "Deleting and reinstalling node_modules..."
    rm -rf node_modules
    npm install
    echo "Node modules reinstalled."
else
    npm install
fi

npm start
