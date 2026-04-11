#!/usr/bin/env bash
set -euo pipefail

DEPS="httpx feedparser beautifulsoup4"

echo "Installing dependencies: $DEPS"

if command -v uv &>/dev/null; then
    echo "Using uv..."
    uv pip install $DEPS
elif command -v pip3 &>/dev/null; then
    echo "Using pip3..."
    pip3 install $DEPS
elif command -v pip &>/dev/null; then
    echo "Using pip..."
    pip install $DEPS
else
    echo "Error: No pip or uv found. Please install Python 3.11+ first."
    exit 1
fi

echo "Done. Dependencies installed successfully."
