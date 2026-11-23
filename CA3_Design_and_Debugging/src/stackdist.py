"""LRU stack (reuse) distances via the Mattson stack algorithm.

For a reference to page p at time t, the stack distance is the number of
*distinct* pages referenced since p's previous reference, plus one (p's
position in the LRU stack).  A reference is a hit under LRU with m frames iff
its stack distance <= m.  First references (cold misses) get distance 0 here
and always fault.

Therefore:   LRU_faults(m) = #cold + #{references with distance > m}

This gives the whole LRU fault curve in one pass, and lets the simulator's LRU
be cross-checked against an independent calculation.
"""
from bisect import bisect_right


def stack_distances(trace):
    n = len(trace)
    tree = [0] * (n + 2)  # Fenwick tree over time indices

    def add(i, v):
        i += 1
        while i <= n:
            tree[i] += v
            i += i & -i

    def prefix(i):  # sum of markers at times 0..i
        i += 1
        s = 0
        while i > 0:
            s += tree[i]
            i -= i & -i
        return s

    last = {}
    dists = []
    for t, p in enumerate(trace):
        if p in last:
            lt = last[p]
            between = prefix(t - 1) - prefix(lt)  # markers strictly between
            dists.append(between + 1)
            add(lt, -1)
        else:
            dists.append(0)  # cold
        add(t, 1)
        last[p] = t
    return dists


def lru_faults_from_distances(dists, frames_list):
    """Return {frames: faults} using one sorted pass over the distances."""
    cold = sum(1 for d in dists if d == 0)
    warm = sorted(d for d in dists if d > 0)
    out = {}
    for m in frames_list:
        hits = bisect_right(warm, m)
        out[m] = cold + (len(warm) - hits)
    return out
