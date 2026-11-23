"""CA-5 E1: demand paging on the real kernel.  One JSON line on stdout.

usage: python ca5/demand_worker.py PAGES [populate]

Modes: demand (default) or populate (MAP_POPULATE).
Phases (all counted with /proc/self/stat minflt, residency with /proc/self/status VmRSS):
  1 first touch in steps of `step` pages   2 second pass over the same pages
  3 madvise(MADV_DONTNEED) of the whole region then a third pass (refault)
"""
import json
import mmap
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pager  # noqa: E402
import procinfo  # noqa: E402

PAGE = pager.PAGE


def rss_kb():
    return procinfo.snapshot()["vmrss_kb"]


def main():
    n = int(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else "demand"
    base_rss = rss_kb()
    f_start = procinfo.minflt()
    t_total = time.perf_counter()
    m = pager.new_region(n, populate=(mode == "populate"))   # populate: the kernel pre-faults every page here
    t_create = time.perf_counter() - t_total
    f_create = procinfo.minflt() - f_start
    steps = []
    step = max(1, n // 10)
    for lo in range(0, n, step):
        hi = min(n, lo + step)
        f0, t0 = procinfo.minflt(), time.perf_counter()
        for p in range(lo, hi):
            m[p * PAGE] = 1
        dt = time.perf_counter() - t0
        steps.append(dict(pages=hi, faults=procinfo.minflt() - f0, cum_faults=procinfo.minflt() - f_start,
                          rss_kb=rss_kb() - base_rss, seconds=dt))
    first = dict(faults=procinfo.minflt() - f_start, seconds=time.perf_counter() - t_total,
                 faults_in_mmap_call=f_create, seconds_in_mmap_call=t_create)
    f0, t0 = procinfo.minflt(), time.perf_counter()
    for p in range(n):
        m[p * PAGE] = 1
    second = dict(faults=procinfo.minflt() - f0, seconds=time.perf_counter() - t0)
    rss_full = rss_kb() - base_rss
    m.madvise(mmap.MADV_DONTNEED)
    rss_dropped = rss_kb() - base_rss
    f0, t0 = procinfo.minflt(), time.perf_counter()
    for p in range(n):
        m[p * PAGE] = 1
    third = dict(faults=procinfo.minflt() - f0, seconds=time.perf_counter() - t0)
    print(json.dumps(dict(mode=mode, pages=n, steps=steps, first=first, second=second, third=third,
                          rss_full_kb=rss_full, rss_after_dontneed_kb=rss_dropped, f_at_start=f_start)))


if __name__ == "__main__":
    main()
