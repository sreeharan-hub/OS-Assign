"""Page-replacement simulator (demand paging, one process, page identity only).

Every policy function takes a reference string (list of hashable page ids) and a
frame count and returns the number of page faults.  Nothing else is modelled:
no page size, no I/O time, no prefetching.

Policies
--------
FIFO    evict the page that has been resident longest
LRU     evict the least recently used page (a hit refreshes the page)
OPT     Belady's optimal: evict the page whose next use is farthest away
MRU     evict the most recently used page (diagnostic policy, good on loops)
RANDOM  evict a uniformly random resident page (seeded)
CLOCK   second-chance approximation of LRU with one reference bit per frame
"""
from collections import OrderedDict, deque
import heapq
import random

POLICIES = ("FIFO", "LRU", "OPT", "MRU", "RANDOM", "CLOCK")


def dedup(trace):
    """Drop immediately repeated references to the same page.

    A reference to the page that was just referenced can never fault (the page
    is certainly resident for any frame count >= 1) and cannot change the
    state of FIFO, LRU, OPT, MRU or CLOCK, so removing it does not change any
    fault count.  Fault *rates* are therefore reported per page-changing
    reference.
    """
    out = []
    prev = None
    first = True
    for p in trace:
        if first or p != prev:
            out.append(p)
            prev = p
            first = False
    return out


def fifo(trace, frames):
    resident = set()
    queue = deque()
    faults = 0
    for p in trace:
        if p in resident:
            continue
        faults += 1
        if len(queue) >= frames:
            resident.discard(queue.popleft())
        queue.append(p)
        resident.add(p)
    return faults


def lru(trace, frames):
    od = OrderedDict()
    faults = 0
    for p in trace:
        if p in od:
            od.move_to_end(p)
            continue
        faults += 1
        if len(od) >= frames:
            od.popitem(last=False)
        od[p] = None
    return faults


def mru(trace, frames):
    od = OrderedDict()
    faults = 0
    for p in trace:
        if p in od:
            od.move_to_end(p)
            continue
        faults += 1
        if len(od) >= frames:
            od.popitem(last=True)  # evict the most recently used page
        od[p] = None
    return faults


def opt(trace, frames):
    """Belady's OPT.  One backward pass computes each reference's next use,
    then a max-heap with lazy invalidation picks the farthest-next-use victim."""
    n = len(trace)
    nxt = [0] * n
    last = {}
    for i in range(n - 1, -1, -1):
        p = trace[i]
        nxt[i] = last.get(p, n)  # n means "never used again"
        last[p] = i
    resident = {}  # page -> its current next-use index
    heap = []
    faults = 0
    push, pop = heapq.heappush, heapq.heappop
    for i, p in enumerate(trace):
        if p in resident:
            resident[p] = nxt[i]
            push(heap, (-nxt[i], p))
            continue
        faults += 1
        if len(resident) >= frames:
            while True:
                neg, q = pop(heap)
                if resident.get(q) == -neg:  # entry is current, not stale
                    del resident[q]
                    break
        resident[p] = nxt[i]
        push(heap, (-nxt[i], p))
    return faults


def random_policy(trace, frames, seed=0):
    rng = random.Random(seed)
    slots = []  # resident pages
    where = {}  # page -> index in slots
    faults = 0
    for p in trace:
        if p in where:
            continue
        faults += 1
        if len(slots) >= frames:
            i = rng.randrange(len(slots))
            victim = slots[i]
            del where[victim]
            slots[i] = p
            where[p] = i
        else:
            where[p] = len(slots)
            slots.append(p)
    return faults


def clock(trace, frames):
    """Second-chance / CLOCK.  A page's reference bit is set when it is loaded
    (the faulting reference itself references it) and on every hit."""
    slots = [None] * frames
    ref = [0] * frames
    where = {}
    hand = 0
    filled = 0
    faults = 0
    for p in trace:
        i = where.get(p)
        if i is not None:
            ref[i] = 1
            continue
        faults += 1
        if filled < frames:
            i = filled
            filled += 1
        else:
            while ref[hand]:
                ref[hand] = 0
                hand = (hand + 1) % frames
            i = hand
            hand = (hand + 1) % frames
            del where[slots[i]]
        slots[i] = p
        ref[i] = 1
        where[p] = i
    return faults


def simulate(policy, trace, frames, seed=0):
    """Run one policy by name.  `trace` should already be de-duplicated."""
    if policy == "FIFO":
        return fifo(trace, frames)
    if policy == "LRU":
        return lru(trace, frames)
    if policy == "OPT":
        return opt(trace, frames)
    if policy == "MRU":
        return mru(trace, frames)
    if policy == "RANDOM":
        return random_policy(trace, frames, seed)
    if policy == "CLOCK":
        return clock(trace, frames)
    raise ValueError(f"unknown policy {policy!r}")
