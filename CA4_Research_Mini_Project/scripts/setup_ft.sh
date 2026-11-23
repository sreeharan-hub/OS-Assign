#!/usr/bin/env bash
# Install uv and a free-threaded CPython 3.14t build (no GIL) for the experiments.
set -e
pip3 install --user --break-system-packages uv 2>&1 | tail -1
UV="$HOME/.local/bin/uv"
"$UV" python install 3.14t
"$UV" python find 3.14t
PY=$("$UV" python find 3.14t)
"$PY" -c "import sys; print(sys.version); print('GIL enabled:', sys._is_gil_enabled())"
