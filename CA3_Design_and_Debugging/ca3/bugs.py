"""CA-3 (Challenge F1/F2): a defective LRU page-replacement simulator, the fixes, and a fault-injection kit.

Everything here counts page faults for a reference string and a frame count, like src/simulator.py,
but is written *independently* of it so that it can serve as a differential-testing oracle.
"""
from collections import OrderedDict, deque

# --------------------------------------------------------------------------- the provided (defective) code
def lru_defective(trace, frames):
    """THE CHALLENGE CODE.  Looks like LRU, produces too many faults.

    Each resident page carries a 'last_used' timestamp and the victim is the page with the smallest one.
    """
    clock = 0
    last_used = {}
    faults = 0
    for page in trace:
        clock += 1
        if page in last_used:
            continue                                  # hit  <-- DEFECT: last_used[page] is never refreshed
        faults += 1
        if len(last_used) >= frames:
            victim = min(last_used, key=last_used.get)
            del last_used[victim]
        last_used[page] = clock
    return faults


# --------------------------------------------------------------------------- candidate fixes
def lru_fix_timestamp(trace, frames):
    """Fix A: same structure, refresh the timestamp on a hit.  O(frames) per fault (linear victim search)."""
    clock = 0
    last_used = {}
    faults = 0
    for page in trace:
        clock += 1
        if page in last_used:
            last_used[page] = clock                   # the one-line fix
            continue
        faults += 1
        if len(last_used) >= frames:
            victim = min(last_used, key=last_used.get)
            del last_used[victim]
        last_used[page] = clock
    return faults


def lru_fix_ordered(trace, frames):
    """Fix B: OrderedDict as a recency list; O(1) per reference."""
    od = OrderedDict()
    faults = 0
    for page in trace:
        if page in od:
            od.move_to_end(page)
            continue
        faults += 1
        if len(od) >= frames:
            od.popitem(last=False)
        od[page] = None
    return faults


class _Node:
    __slots__ = ("page", "prev", "next")

    def __init__(self, page):
        self.page, self.prev, self.next = page, None, None


def lru_fix_linked(trace, frames):
    """Fix C: hand-built doubly linked list + hash map (what a kernel would do); O(1) per reference."""
    head, tail = _Node(None), _Node(None)          # sentinels: head.next = LRU end, tail.prev = MRU end
    head.next, tail.prev = tail, head
    table = {}

    def unlink(n):
        n.prev.next, n.next.prev = n.next, n.prev

    def push_mru(n):
        n.prev, n.next = tail.prev, tail
        tail.prev.next = n
        tail.prev = n

    faults = 0
    for page in trace:
        n = table.get(page)
        if n is not None:
            unlink(n)
            push_mru(n)
            continue
        faults += 1
        if len(table) >= frames:
            victim = head.next
            unlink(victim)
            del table[victim.page]
        n = _Node(page)
        table[page] = n
        push_mru(n)
    return faults


def lru_reference(trace, frames):
    """Oracle for differential testing: the most literal definition (a list ordered by recency)."""
    stack = []                                       # stack[0] = least recently used
    faults = 0
    for page in trace:
        if page in stack:
            stack.remove(page)
            stack.append(page)
            continue
        faults += 1
        if len(stack) >= frames:
            stack.pop(0)
        stack.append(page)
    return faults


FIXES = {"A: timestamp refresh": lru_fix_timestamp, "B: OrderedDict": lru_fix_ordered,
         "C: linked list + hash": lru_fix_linked}


def fifo_reference(trace, frames):
    q, res, faults = deque(), set(), 0
    for page in trace:
        if page in res:
            continue
        faults += 1
        if len(q) >= frames:
            res.discard(q.popleft())
        q.append(page)
        res.add(page)
    return faults


def opt_reference(trace, frames):
    """Belady's OPT, O(n * frames) literal version (oracle)."""
    res, faults = set(), 0
    for i, page in enumerate(trace):
        if page in res:
            continue
        faults += 1
        if len(res) >= frames:
            def next_use(q):
                try:
                    return trace.index(q, i + 1)
                except ValueError:
                    return len(trace) + 1
            res.remove(max(res, key=next_use))
        res.add(page)
    return faults


# --------------------------------------------------------------------------- fault injection (mutants)
def make_mutant(kind):
    """Return an LRU implementation with ONE injected defect (a 'working system + one hidden defect')."""
    def mutant(trace, frames):
        od = OrderedDict()
        faults = 0
        cap = frames - 1 if kind == "M3" else frames + 1 if kind == "M4" else frames
        cap = max(cap, 1)
        evictions = 0
        for page in trace:
            if page in od:
                if kind == "M1":
                    pass                                      # no recency refresh on a hit
                elif kind == "M5":
                    od.move_to_end(next(iter(od)))            # refreshes the LRU page, not the hit page
                else:
                    od.move_to_end(page)
                continue
            faults += 1
            if len(od) >= cap:
                od.popitem(last=(kind == "M2"))               # M2: evicts the MRU page
                evictions += 1
            od[page] = None
        return evictions if kind == "M6" else faults          # M6: reports evictions, not faults
    return mutant


MUTANTS = {
    "M1": ("No recency refresh on a hit", "Remove `move_to_end` on a hit (the provided bug)"),
    "M2": ("Evicts the MRU page", "`popitem(last=False)` -> `last=True`"),
    "M3": ("Off-by-one: one frame unused", "capacity = frames - 1"),
    "M4": ("Off-by-one: one extra frame", "capacity = frames + 1"),
    "M5": ("Refreshes the wrong page on a hit", "Move the oldest page, not the hit page"),
    "M6": ("Bookkeeping: counts evictions", "Report evictions instead of faults"),
}
mutants = {k: make_mutant(k) for k in MUTANTS}


def lru_final(trace, frames):
    """THE SELECTED IMPLEMENTATION (Fix B + input validation).  O(1) per reference, O(frames) memory."""
    if not isinstance(frames, int) or frames < 1:
        raise ValueError(f"frames must be a positive integer, got {frames!r}")
    return lru_fix_ordered(trace, frames)
