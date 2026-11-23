#!/usr/bin/env bash
# Follow-up experiments from the audit. One process per section so earlier sections cannot affect later ones.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
bash scripts/build_rust.sh
for s in topo heap_thread fork_live park pool_ipc cpu2; do
  echo "section $s"
  "$HOME/ptbench-target/release/ptbench" $s > "results/followup_$s.json" 2> "results/followup_$s.err"
done
# Python: spawn cost with the system interpreter, and per-core speed
python3 python/bench2.py --tag sys --out results/py_sys.json --sections create
echo done > results/followup.done
