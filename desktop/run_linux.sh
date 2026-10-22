#!/usr/bin/env sh
set -eu
cd -- "$(dirname -- "$0")"
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3.10–3.13 o'rnating. Tavsiya: Python 3.12."
    exit 1
fi
exec python3 run.py "$@"
