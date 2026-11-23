"""CA-1: Denning working-set measurement and the thrashing (CPU utilisation) model."""
from policies import lru


def wss_series(refs, window, step=None):
    """|W(t, window)| = distinct pages among the last `window` references, sampled every `step`."""
    step = step or window
    counts, out = {}, []
    for i, p in enumerate(refs):
        counts[p] = counts.get(p, 0) + 1
        if i >= window:
            q = refs[i - window]
            counts[q] -= 1
            if counts[q] == 0:
                del counts[q]
        if i >= window - 1 and (i - window + 1) % step == 0:
            out.append(len(counts))
    return out


def steady_fault_rate(refs, frames, warmup):
    """LRU fault rate measured after `warmup` references (compulsory misses excluded)."""
    _, pos = lru(refs, frames, detail=True)
    n = len(refs) - warmup
    return sum(1 for x in pos if x >= warmup) / n


def cpu_utilisation(n_procs, total_frames, p_of_frames, t_cpu_us=1.0, t_other_us=1.0, service_us=8000.0):
    """Classic thrashing curve. Each process cycles: CPU t_cpu, other waiting t_other,
    plus p * service of page-fault waiting. Frames are shared equally.
    Utilisation = min(1, N * t_cpu / (t_cpu + t_other + p*service))."""
    frames_each = max(1, total_frames // n_procs)
    p = p_of_frames(frames_each)
    frac = t_cpu_us / (t_cpu_us + t_other_us + p * service_us)
    return min(1.0, n_procs * frac), p
