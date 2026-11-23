"""Memory-pressure threshold ("knee") for matrix multiply.

Sweeps the *absolute* frame count in fine steps for the naive and tiled
multiplies and records FIFO / LRU / OPT fault rates, to locate where faults
collapse once memory covers the working set (Denning's working-set model).

Output: results/raw_knee.csv
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import RESULTS, n_workers, write_csv  # noqa: E402
from simulator import dedup, simulate  # noqa: E402
import traces  # noqa: E402

FRAMES = sorted(set(list(range(8, 40, 8)) + list(range(40, 121, 4)) + list(range(17, 24)) + [69, 70, 71]))
POLS = ("FIFO", "LRU", "OPT")


def work(pattern):
    trace = dedup(traces.build(pattern))
    rows = []
    for m in FRAMES:
        for pol in POLS:
            f = simulate(pol, trace, m)
            rows.append(dict(pattern=pattern, frames=m, policy=pol, refs=len(trace),
                             faults=f, fault_rate=f / len(trace)))
    return rows


def main():
    rows = []
    with ProcessPoolExecutor(max_workers=min(2, n_workers())) as ex:
        for r in ex.map(work, ["matmul_naive", "matmul_tiled"]):
            rows.extend(r)
    write_csv(RESULTS / "raw_knee.csv", rows,
              ["pattern", "frames", "policy", "refs", "faults", "fault_rate"])
    print(f"raw_knee.csv: {len(rows)} rows")


if __name__ == "__main__":
    main()
