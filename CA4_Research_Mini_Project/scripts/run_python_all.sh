#!/usr/bin/env bash
# Run the Python benchmark on the default (GIL) and free-threaded builds of the same CPython release.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
UV="$HOME/.local/bin/uv"
"$UV" python install 3.14 3.14t 2>&1 | tail -2
GIL_PY="$("$UV" python find --no-project 3.14 | head -1)"
FT_PY="$("$UV" python find --no-project 3.14t | head -1)"
rm -f results/py_gil.json results/py_ft.json results/py_all.done
echo "gil: $GIL_PY"; "$GIL_PY" -c "import sys;print(sys.version, 'GIL', sys._is_gil_enabled())"
echo "ft:  $FT_PY";  "$FT_PY"  -c "import sys;print(sys.version, 'GIL', sys._is_gil_enabled())"
"$GIL_PY" python/bench2.py --tag gil --out results/py_gil.json
"$FT_PY" python/bench2.py --tag ft --out results/py_ft.json
echo done > results/py_all.done
