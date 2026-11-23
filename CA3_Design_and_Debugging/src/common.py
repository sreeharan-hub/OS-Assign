"""Shared constants and helpers for all experiment scripts."""
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"
for _d in (RESULTS, FIGURES):
    _d.mkdir(parents=True, exist_ok=True)

if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

# Memory size as a percentage of each trace's footprint (11 levels).
MEM_LEVELS = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
N_SEEDS = 10  # repetitions for stochastic workloads / the RANDOM policy


def frames_for(footprint, pct):
    """Frame count for a memory level; never fewer than 2 frames."""
    return max(2, round(pct / 100 * footprint))


def n_workers():
    return max(1, min(os.cpu_count() or 1, 8))


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
