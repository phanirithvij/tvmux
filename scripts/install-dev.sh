#!/usr/bin/env bash
source .venv/bin/activate
set -e

# Install uv if not present (should be installed by venv.sh)
if ! command -v uv >/dev/null 2>&1; then
    pip install uv
fi

if command -v uv >/dev/null 2>&1; then
    PIP="uv pip"
else
    PIP="python3 -m pip"
fi

$PIP install -e .[dev]

echo "Installed in dev mode"
touch .venv/.installed-dev
rm .venv/.installed 2>/dev/null || true
