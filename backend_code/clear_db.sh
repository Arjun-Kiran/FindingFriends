#!/bin/bash
echo "Clearing SQLite database..."
# Relative to this script, so it works no matter where it is run from.
rm -f "$(dirname "$0")/game_state.db"
echo "Database cleared."
