"""Design extension (CA-3 Level 3/4): scan-resistant alternatives to plain LRU."""
from collections import OrderedDict


def slru(trace, frames, protected_frac=0.5):
    """Segmented LRU: a page enters a probationary segment; a second reference promotes it to a protected
    segment.  A one-pass scan can only evict probationary pages, so the protected hot set survives it."""
    prot_cap = max(1, int(frames * protected_frac))
    if frames < 2:
        prot_cap = 0
    prob, prot = OrderedDict(), OrderedDict()
    faults = 0
    for p in trace:
        if p in prot:
            prot.move_to_end(p)
            continue
        if p in prob:                                    # second touch: promote
            del prob[p]
            prot[p] = None
            if len(prot) > prot_cap:                     # demote the LRU protected page
                q, _ = prot.popitem(last=False)
                prob[q] = None
            continue
        faults += 1
        if len(prob) + len(prot) >= frames:
            if prob:
                prob.popitem(last=False)
            else:
                prot.popitem(last=False)
        prob[p] = None
    return faults
