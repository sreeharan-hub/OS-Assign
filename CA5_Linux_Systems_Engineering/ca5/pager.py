"""CA-5 core: drive REAL Linux page faults with the simulator's replacement policies.

A user-space "pager" keeps at most `frames` pages of an anonymous mmap resident.  For every reference the policy decides
whether the page is already resident and, if it faults while memory is full, which page to evict.  The victim is evicted
with madvise(MADV_DONTNEED) - the kernel really drops the page - and the reference itself is a real store to the page, so
the *kernel* takes (and counts) a real page fault exactly when the simulator predicts one.

The kernel fault counter (/proc/<pid>/stat minflt) can therefore be compared with the simulator's prediction.
"""
import heapq
import mmap
import os
import sys
import time
from collections import OrderedDict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import procinfo  # noqa: E402

PAGE = os.sysconf("SC_PAGE_SIZE")


def relabel(trace):
    """Map arbitrary page ids to 0..footprint-1 (first-use order)."""
    ids = {}
    return [ids.setdefault(p, len(ids)) for p in trace], len(ids)


def victims_fifo(trace, frames):
    q, res, out, faults = deque(), set(), [], 0
    for p in trace:
        v = -1
        if p not in res:
            faults += 1
            if len(q) >= frames:
                v = q.popleft()
                res.discard(v)
            q.append(p)
            res.add(p)
        out.append(v)
    return out, faults


def victims_lru(trace, frames):
    od, out, faults = OrderedDict(), [], 0
    for p in trace:
        v = -1
        if p in od:
            od.move_to_end(p)
        else:
            faults += 1
            if len(od) >= frames:
                v, _ = od.popitem(last=False)
            od[p] = None
        out.append(v)
    return out, faults


def victims_opt(trace, frames):
    n = len(trace)
    nxt, last = [0] * n, {}
    for i in range(n - 1, -1, -1):
        nxt[i] = last.get(trace[i], n)
        last[trace[i]] = i
    resident, heap, out, faults = {}, [], [], 0
    for i, p in enumerate(trace):
        v = -1
        if p in resident:
            resident[p] = nxt[i]
            heapq.heappush(heap, (-nxt[i], p))
        else:
            faults += 1
            if len(resident) >= frames:
                while True:
                    neg, q = heapq.heappop(heap)
                    if resident.get(q) == -neg:
                        del resident[q]
                        v = q
                        break
            resident[p] = nxt[i]
            heapq.heappush(heap, (-nxt[i], p))
        out.append(v)
    return out, faults


POLICY_FN = {"FIFO": victims_fifo, "LRU": victims_lru, "OPT": victims_opt}


def new_region(npages, populate=False):
    flags = mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS | (mmap.MAP_POPULATE if populate else 0)
    m = mmap.mmap(-1, npages * PAGE, flags=flags)
    m.madvise(mmap.MADV_NOHUGEPAGE)          # keep the unit of residency one 4 KiB page
    return m


def replay(trace, victims, npages, sample_rss_every=0):
    """Run the reference string against a real mapping.  Returns measurements taken with /proc and the clock."""
    m = new_region(npages)
    dont = mmap.MADV_DONTNEED
    off = [p * PAGE for p in trace]
    vic = [v * PAGE if v >= 0 else -1 for v in victims]
    rss = []
    rss0 = procinfo.read_statm()['resident_pages']
    f0 = procinfo.minflt()
    g0 = procinfo.vmstat_pgfault()
    t0 = time.perf_counter()
    if sample_rss_every:
        for i, (o, v) in enumerate(zip(off, vic)):
            if v >= 0:
                m.madvise(dont, v, PAGE)
            m[o] = 1
            if i % sample_rss_every == 0:
                rss.append(procinfo.read_statm()["resident_pages"])
    else:
        for o, v in zip(off, vic):
            if v >= 0:
                m.madvise(dont, v, PAGE)
            m[o] = 1                          # the store: a real page fault if the page is not resident
    t1 = time.perf_counter()
    f1 = procinfo.minflt()
    g1 = procinfo.vmstat_pgfault()
    m.close()
    return dict(minflt=f1 - f0, vmstat_pgfault=g1 - g0, seconds=t1 - t0, rss_samples=rss, rss0=rss0)
