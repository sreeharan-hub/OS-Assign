"""Main experiment: 7 patterns x 6 policies x 11 memory levels.

Output: results/raw_main.csv  (one row per run; raw data is never discarded)

Repetitions: 10 trace seeds for the three stochastic patterns; the four
deterministic patterns have one trace, but the RANDOM policy (itself
stochastic) is repeated with 10 policy seeds on them.
"""
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import MEM_LEVELS, N_SEEDS, RESULTS, frames_for, n_workers, write_csv  # noqa: E402
from simulator import POLICIES, dedup, simulate  # noqa: E402
import traces  # noqa: E402

FIELDS = ["pattern", "trace_seed", "policy", "policy_seed", "mem_pct", "frames",
          "footprint", "refs", "faults", "fault_rate"]


def work(task):
    pattern, seed = task
    trace = dedup(traces.build(pattern, seed=seed))
    footprint = len(set(trace))
    rows = []
    for pct in MEM_LEVELS:
        m = frames_for(footprint, pct)
        for pol in POLICIES:
            if pol == "RANDOM":
                seeds = [seed] if pattern in traces.STOCHASTIC else range(N_SEEDS)
            else:
                seeds = [0]
            for ps in seeds:
                f = simulate(pol, trace, m, seed=ps)
                rows.append(dict(pattern=pattern, trace_seed=seed, policy=pol,
                                 policy_seed=ps, mem_pct=pct, frames=m,
                                 footprint=footprint, refs=len(trace), faults=f,
                                 fault_rate=f / len(trace)))
    return rows


def main():
    tasks = []
    for p in traces.ORDER:
        for s in (range(N_SEEDS) if p in traces.STOCHASTIC else [0]):
            tasks.append((p, s))
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=n_workers()) as ex:
        for r in ex.map(work, tasks):
            rows.extend(r)
    write_csv(RESULTS / "raw_main.csv", rows, FIELDS)
    print(f"raw_main.csv: {len(rows)} rows in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
