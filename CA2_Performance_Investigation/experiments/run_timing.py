"""Bookkeeping-cost measurement (wall-clock, 5 repetitions after a warm-up).

IMPORTANT: this times the *Python simulator*, not an operating system.  It shows
the relative cost of the policies' bookkeeping (FIFO: update on faults only;
LRU/CLOCK: touch state on every reference; OPT: needs the whole future trace and a
heap).  Absolute times depend on the machine - rerun on your own and report your
own numbers.  Run this script with nothing else heavy running.

Output: results/raw_timing.csv (every repetition kept)
"""
import gc
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import RESULTS, write_csv  # noqa: E402
from simulator import clock, dedup, fifo, lru, opt  # noqa: E402

REPS = 5
PAGES = 512
FRAMES = 128  # 25% of the footprint
LENGTHS = (10_000, 50_000, 200_000)
POLS = (("FIFO", fifo), ("LRU", lru), ("CLOCK", clock), ("OPT", opt))


def main():
    rows = []
    for n in LENGTHS:
        rng = random.Random(0)
        trace = dedup([rng.randrange(PAGES) for _ in range(n)])
        for name, fn in POLS:
            fn(trace, FRAMES)  # warm-up
            for rep in range(REPS):
                gc.collect()
                gc.disable()
                t0 = time.perf_counter()
                faults = fn(trace, FRAMES)
                dt = time.perf_counter() - t0
                gc.enable()
                rows.append(dict(policy=name, draws=n, refs=len(trace), frames=FRAMES,
                                 rep=rep, seconds=dt, faults=faults,
                                 us_per_ref=1e6 * dt / len(trace)))
    write_csv(RESULTS / "raw_timing.csv", rows,
              ["policy", "draws", "refs", "frames", "rep", "seconds", "faults", "us_per_ref"])
    print(f"raw_timing.csv: {len(rows)} rows")


if __name__ == "__main__":
    main()
