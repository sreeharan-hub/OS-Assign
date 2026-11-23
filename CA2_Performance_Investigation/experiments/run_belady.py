"""Belady's anomaly investigation.

Part A  the classic string (known positive control).
Part B  random reference strings: how common is the anomaly for FIFO, and does it
        ever occur for LRU or OPT (stack algorithms - it must not).
Part C  the ML-shaped traces: does FIFO ever fault MORE with more frames, checked
        at every frame count (matmul: 30 evenly spaced counts).

Outputs: results/belady_random.csv, results/belady_ml.csv, results/belady_examples.txt
"""
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import RESULTS, n_workers, write_csv  # noqa: E402
from simulator import dedup, fifo, lru, opt  # noqa: E402
import traces  # noqa: E402

N_STRINGS = 10_000
CLASSIC = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]


def anomalies(counts):
    """counts: list of (frames, faults) sorted by frames. Returns increases found."""
    inc = []
    for (m1, f1), (m2, f2) in zip(counts, counts[1:]):
        if f2 > f1:
            inc.append((m1, m2, f2 - f1))
    return inc


def random_family(kind, rng):
    if kind == "uniform":
        pages = rng.randint(5, 8)
        return [rng.randrange(pages) for _ in range(rng.randint(20, 40))]
    # "noisy_cycle": a cyclic scan over p pages with random substitutions, the
    # shape a looped dataset read with a little noise would have
    pages = rng.randint(5, 8)
    length = rng.randint(20, 40)
    s = []
    for i in range(length):
        s.append(rng.randrange(pages) if rng.random() < 0.2 else i % pages)
    return s


def part_b():
    rows, examples = [], []
    for kind in ("uniform", "noisy_cycle"):
        rng = random.Random(2026)
        hit = {"FIFO": 0, "LRU": 0, "OPT": 0}
        worst = {"FIFO": 0, "LRU": 0, "OPT": 0}
        for _ in range(N_STRINGS):
            s = dedup(random_family(kind, rng))
            top = len(set(s))
            for name, fn in (("FIFO", fifo), ("LRU", lru), ("OPT", opt)):
                counts = [(m, fn(s, m)) for m in range(1, top + 1)]
                inc = anomalies(counts)
                if inc:
                    hit[name] += 1
                    w = max(i[2] for i in inc)
                    if w > worst[name]:
                        worst[name] = w
                        if name == "FIFO":
                            examples.append((kind, w, s))
        for name in ("FIFO", "LRU", "OPT"):
            rows.append(dict(family=kind, policy=name, strings=N_STRINGS,
                             with_anomaly=hit[name], pct=100 * hit[name] / N_STRINGS,
                             worst_extra_faults=worst[name]))
    return rows, examples


def part_c_task(task):
    pattern, seed = task
    s = dedup(traces.build(pattern, seed=seed))
    foot = len(set(s))
    if pattern.startswith("matmul"):
        grid = sorted({max(2, round(foot * i / 30)) for i in range(1, 31)})
    else:
        grid = list(range(2, foot + 1))
    counts = [(m, fifo(s, m)) for m in grid]
    inc = anomalies(counts)
    return dict(pattern=pattern, seed=seed, footprint=foot, frame_counts_checked=len(grid),
                anomalies=len(inc), worst_extra_faults=max([i[2] for i in inc], default=0))


def main():
    # Part A
    a = (fifo(CLASSIC, 3), fifo(CLASSIC, 4))
    lines = [f"Part A  classic string {CLASSIC}",
             f"  FIFO faults with 3 frames = {a[0]}, with 4 frames = {a[1]}  "
             f"-> anomaly = {a[1] > a[0]}",
             f"  LRU  3 frames = {lru(CLASSIC, 3)}, 4 frames = {lru(CLASSIC, 4)}",
             f"  OPT  3 frames = {opt(CLASSIC, 3)}, 4 frames = {opt(CLASSIC, 4)}", ""]
    # Part B
    rows_b, examples = part_b()
    write_csv(RESULTS / "belady_random.csv", rows_b,
              ["family", "policy", "strings", "with_anomaly", "pct", "worst_extra_faults"])
    lines.append("Part B  worst FIFO anomaly examples found (family, extra faults, string)")
    seen = {}
    for kind, w, s in examples:
        seen[kind] = (w, s)
    for kind, (w, s) in seen.items():
        lines.append(f"  {kind}: +{w} faults  {s}")
    # Part C
    tasks = []
    for p in traces.ORDER:
        for sd in (range(3) if p in traces.STOCHASTIC else [0]):
            tasks.append((p, sd))
    with ProcessPoolExecutor(max_workers=n_workers()) as ex:
        rows_c = list(ex.map(part_c_task, tasks))
    write_csv(RESULTS / "belady_ml.csv", rows_c,
              ["pattern", "seed", "footprint", "frame_counts_checked", "anomalies",
               "worst_extra_faults"])
    (RESULTS / "belady_examples.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    for r in rows_b:
        print(r)
    for r in rows_c:
        print(r)


if __name__ == "__main__":
    main()
