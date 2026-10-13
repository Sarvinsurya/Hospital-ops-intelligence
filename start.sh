#!/usr/bin/env bash
# Hospital Operations Intelligence System — macOS / Linux launcher
# Double-click or run:  ./start.sh
set -e
cd "$(dirname "$0")"

# Pick a usable Python to run the cross-platform launcher
PY=""
for c in python3.12 python3.11 python3.13 python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "Python 3 not found. Install Python 3.12 from https://www.python.org/downloads/"
  exit 1
fi

echo "Using $PY to launch…"
exec "$PY" launch.py "$@"
