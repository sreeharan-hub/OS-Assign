"""Sensitivity sweeps: does the FIFO/LRU/OPT picture survive a change of workload size?

  footprint  : sequential / random / shuffled with 256, 512, 1024 pages
  hot_set    : bursty with a 24, 48, 96-page hot set
  tile       : tiled matmul with 8x8, 16x16, 32x32 tiles

Output: results/raw_sweeps.csv
"""
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import MEM_LEVELS, N_SEEDS, RESULTS, frames_for, n_workers, write_csv  # noqa: E402
from simulator import dedup, simulate  # noqa: E402
import traces  # noqa: E402

POLS = ("FIFO", "LRU", "OPT")
FIELDS = ["sweep", "param_value", "pattern", "seed", "policy", "mem_pct", "frames",
          "footprint", "refs", "faults", "fault_rate"]


def make(sweep, value, pattern, seed):
    if sweep == "footprint":
        if pattern == "random":
            return traces.uniform_random(seed=seed, pages=value, draws=20 * value)
        if pattern == "sequential":
            return traces.sequential_loop(pages=value)
        return traces.shuffled_epochs(seed=seed, pages=value)
    if sweep == "hot_set":
        return traces.bursty(seed=seed, hot=value)
    if sweep == "tile":
        return traces.matmul_tiled(tile=value)
    raise ValueError(sweep)


def work(task):
    sweep, value, pattern, seed = task
    trace = dedup(make(sweep, value, pattern, seed))
    foot = len(set(trace))
    rows = []
    for pct in MEM_LEVELS:
        m = frames_for(foot, pct)
        for pol in POLS:
            f = simulate(pol, trace, m)
            rows.append(dict(sweep=sweep, param_value=value, pattern=pattern, seed=seed,
                             policy=pol, mem_pct=pct, frames=m, footprint=foot,
                             refs=len(trace), faults=f, fault_rate=f / len(trace)))
    return rows


def main():
    tasks = []
    for v in (256, 512, 1024):
        for p in ("sequential", "random", "shuffled"):
            for s in (range(N_SEEDS) if p in traces.STOCHASTIC else [0]):
                tasks.append(("footprint", v, p, s))
    for v in (24, 48, 96):
        for s in range(N_SEEDS):
            tasks.append(("hot_set", v, "bursty", s))
    for v in (8, 16, 32):
        tasks.append(("tile", v, "matmul_tiled", 0))
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=n_workers()) as ex:
        for r in ex.map(work, tasks):
            rows.extend(r)
    write_csv(RESULTS / "raw_sweeps.csv", rows, FIELDS)
    print(f"raw_sweeps.csv: {len(rows)} rows in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
