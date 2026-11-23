#!/usr/bin/env bash
# Reproduce every result and figure. Run inside Linux (native or WSL2 Ubuntu).
# Takes about 40 to 60 minutes. Do not run other heavy programs at the same time.
#   bash scripts/run_all.sh            full run
#   bash scripts/run_all.sh quick      skip the long Rust and Python sections (smoke test)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p results

echo "== Rust build =="
(cd rust && CARGO_TARGET_DIR="$HOME/ptbench-target" cargo build --release)

echo "== free-threaded Python (3.14t) via uv =="
bash scripts/setup_ft.sh
FT_PY="$("$HOME/.local/bin/uv" python find 3.14t)"
GIL_PY="python3"

if [ "$1" != "quick" ]; then
  echo "== Rust benchmark =="
  "$HOME/ptbench-target/release/ptbench" > results/rust_final.json
  echo "== Python benchmark, GIL build =="
  "$GIL_PY" python/bench2.py --tag gil --out results/py_gil.json
  echo "== Python benchmark, free-threaded build =="
  "$FT_PY" python/bench2.py --tag ft --out results/py_ft.json
else
  "$GIL_PY" python/bench2.py --tag gil --out results/py_gil.json --sections create,pingpong
fi

echo "== Page-fault and context-switch counters =="
python3 python/bench_counters.py > results/followup_counters.json

echo "Raw results are in results/. Build figures and the paper on Windows or Linux with:"
echo "  python -I python/figs2.py && python -I python/build_slides.py"
