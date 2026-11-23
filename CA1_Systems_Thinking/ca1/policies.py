"""CA-1: page-replacement policies using only the Python standard library.

Every function takes a reference string (list of page numbers) and a frame count
and returns the number of page faults. `simulate` also returns the fault positions.
"""
from collections import OrderedDict, deque
import heapq


def _check(frames):
    if frames < 1:
        raise ValueError("frames must be >= 1")


def fifo(refs, frames, detail=False):
    _check(frames)
    mem, order, pos = set(), deque(), []
    for i, p in enumerate(refs):
        if p in mem:
            continue
        pos.append(i)
        if len(mem) == frames:
            mem.discard(order.popleft())
        mem.add(p)
        order.append(p)
    return (len(pos), pos) if detail else len(pos)


def lru(refs, frames, detail=False):
    _check(frames)
    mem, pos = OrderedDict(), []
    for i, p in enumerate(refs):
        if p in mem:
            mem.move_to_end(p)          # hit: becomes most recently used
            continue
        pos.append(i)
        if len(mem) == frames:
            mem.popitem(last=False)     # evict least recently used
        mem[p] = True
    return (len(pos), pos) if detail else len(pos)


def mru(refs, frames, detail=False):
    """Evict the most recently used page (good for pure cyclic scans)."""
    _check(frames)
    mem, pos = OrderedDict(), []
    for i, p in enumerate(refs):
        if p in mem:
            mem.move_to_end(p)
            continue
        pos.append(i)
        if len(mem) == frames:
            mem.popitem(last=True)
        mem[p] = True
    return (len(pos), pos) if detail else len(pos)


def opt(refs, frames, detail=False):
    """Belady's optimal: evict the page whose next use is farthest in the future."""
    _check(frames)
    n = len(refs)
    nxt, last = [n] * n, {}
    for i in range(n - 1, -1, -1):
        nxt[i] = last.get(refs[i], n)
        last[refs[i]] = i
    mem, heap, pos = {}, [], []          # mem: page -> next-use index
    for i, p in enumerate(refs):
        if p in mem:
            mem[p] = nxt[i]
            heapq.heappush(heap, (-nxt[i], p))
            continue
        pos.append(i)
        if len(mem) == frames:
            while True:                   # lazy deletion of stale heap entries
                negn, q = heapq.heappop(heap)
                if q in mem and mem[q] == -negn:
                    del mem[q]
                    break
        mem[p] = nxt[i]
        heapq.heappush(heap, (-nxt[i], p))
    return (len(pos), pos) if detail else len(pos)


POLICIES = {"FIFO": fifo, "LRU": lru, "MRU": mru, "OPT": opt}


def effective_access_time(p, ma_ns=200.0, service_ns=8_000_000.0):
    """EAT = (1 - p) * ma + p * service   (all in ns)."""
    return (1 - p) * ma_ns + p * service_ns
