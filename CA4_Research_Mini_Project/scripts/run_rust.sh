#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$HOME/ptbench-target/release/ptbench" > "$ROOT/results/rust_final.json"
