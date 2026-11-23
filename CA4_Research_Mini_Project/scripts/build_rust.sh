#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../rust"
CARGO_TARGET_DIR=$HOME/ptbench-target cargo build --release 2>&1 | grep -E "^(error|warning: unused)|Finished|-->" | head -30
