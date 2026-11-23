"""Reuse-distance analysis: tests the *mechanism* behind LRU's behaviour.

1. Computes LRU stack distances for every pattern.
2. Cross-validates: LRU faults predicted from the distances must equal the
   simulator's LRU faults at every memory level (independent implementations).
3. Saves a normalised distance histogram (distance / footprint) per pattern.

Outputs: results/reuse_check.csv, results/reuse_hist.csv, results/reuse_summary.csv
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import MEM_LEVELS, RESULTS, frames_for, write_csv  # noqa: E402
from simulator import dedup, lru  # noqa: E402
from stackdist import lru_faults_from_distances, stack_distances  # noqa: E402
import traces  # noqa: E402

BINS = 20


def main():
    check, hist, summ = [], [], []
    for name in traces.ORDER:
        trace = dedup(traces.build(name, seed=0))
        foot = len(set(trace))
        dists = stack_distances(trace)
        frames = [frames_for(foot, p) for p in MEM_LEVELS]
        pred = lru_faults_from_distances(dists, frames)
        for p, m in zip(MEM_LEVELS, frames):
            sim = lru(trace, m)
            check.append(dict(pattern=name, mem_pct=p, frames=m, lru_simulator=sim,
                              lru_from_distances=pred[m], match=int(sim == pred[m])))
        warm = [d for d in dists if d > 0]
        counts = [0] * BINS
        for d in warm:
            counts[min(BINS - 1, (d - 1) * BINS // foot)] += 1
        for b, c in enumerate(counts):
            hist.append(dict(pattern=name, bin_lo=b / BINS, bin_hi=(b + 1) / BINS,
                             count=c, fraction=c / len(warm)))
        warm_sorted = sorted(warm)
        summ.append(dict(pattern=name, footprint=foot, refs=len(trace),
                         cold_refs=len(dists) - len(warm),
                         median_distance_frac=warm_sorted[len(warm) // 2] / foot,
                         p90_distance_frac=warm_sorted[int(0.9 * len(warm))] / foot))
    write_csv(RESULTS / "reuse_check.csv", check,
              ["pattern", "mem_pct", "frames", "lru_simulator", "lru_from_distances", "match"])
    write_csv(RESULTS / "reuse_hist.csv", hist,
              ["pattern", "bin_lo", "bin_hi", "count", "fraction"])
    write_csv(RESULTS / "reuse_summary.csv", summ,
              ["pattern", "footprint", "refs", "cold_refs", "median_distance_frac",
               "p90_distance_frac"])
    bad = [c for c in check if not c["match"]]
    print(f"cross-check: {len(check) - len(bad)}/{len(check)} memory levels match exactly")
    if bad:
        print("MISMATCHES:", bad)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
