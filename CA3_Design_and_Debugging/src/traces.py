"""Synthetic page-level reference strings that model ML-style memory behaviour.

All generators are deterministic given `seed`, use only the standard-library
`random` module (stable across Python versions), and return a list of integer
page ids.  Page ids are dense, so the footprint is len(set(trace)).

Workload definitions (defaults)
-------------------------------
sequential    512 pages read in a fixed order, 20 passes (epochs without shuffling)
random        10,240 independent uniform draws over 512 pages
shuffled      512 pages, 20 epochs, a fresh permutation each epoch
bursty        40 bursts; each = 400 random references to a 48-page hot set, then
              a 128-page cold scan taken from a 512-page cold region that advances
              by 128 pages per burst (so each cold page returns every 4 bursts)
matmul_naive  C = A x B, 64x64, i-j-k loops, row-major, 16 elements per page
              (3 matrices x 256 pages = 768 pages)
matmul_tiled  same matrices, 16x16 blocking (i/j/k tile loops)
fwd_bwd       64 layers x 4 pages: a forward pass through all layers then the
              backward pass in exact reverse order, 20 training iterations
"""
import random


def sequential_loop(seed=0, pages=512, passes=20):
    return list(range(pages)) * passes


def uniform_random(seed=0, pages=512, draws=10240):
    rng = random.Random(seed)
    return [rng.randrange(pages) for _ in range(draws)]


def shuffled_epochs(seed=0, pages=512, epochs=20):
    rng = random.Random(seed)
    out = []
    order = list(range(pages))
    for _ in range(epochs):
        rng.shuffle(order)
        out.extend(order)
    return out


def bursty(seed=0, bursts=40, hot=48, refs=400, scan=128, cold_region=512):
    rng = random.Random(seed)
    out = []
    for b in range(bursts):
        out.extend(rng.randrange(hot) for _ in range(refs))
        base = (b * scan) % cold_region
        out.extend(hot + (base + k) % cold_region for k in range(scan))
    return out


def _matmul(n, per_page, tile):
    """Reference string for C[i][j] += A[i][k] * B[k][j].  A[i][k] and B[k][j]
    are read every inner iteration; C[i][j] is touched once per k-loop.
    tile=None gives the naive i-j-k order."""
    pages_per_matrix = (n * n + per_page - 1) // per_page
    a_base, b_base, c_base = 0, pages_per_matrix, 2 * pages_per_matrix
    out = []
    app = out.append

    def inner(i_range, j_range, k_range):
        for i in i_range:
            for j in j_range:
                for k in k_range:
                    app(a_base + (i * n + k) // per_page)
                    app(b_base + (k * n + j) // per_page)
                # C[i][j] accumulates in a register and is written back once per
                # (i, j, k-range): the same convention as the research paper
                app(c_base + (i * n + j) // per_page)

    if tile is None:
        inner(range(n), range(n), range(n))
    else:
        for ii in range(0, n, tile):
            for jj in range(0, n, tile):
                for kk in range(0, n, tile):
                    inner(range(ii, min(ii + tile, n)),
                          range(jj, min(jj + tile, n)),
                          range(kk, min(kk + tile, n)))
    return out


def matmul_naive(seed=0, n=64, per_page=16):
    return _matmul(n, per_page, None)


def matmul_tiled(seed=0, n=64, per_page=16, tile=16):
    return _matmul(n, per_page, tile)


def forward_backward(seed=0, layers=64, pages_per_layer=4, iters=20):
    fwd = list(range(layers * pages_per_layer))
    step = fwd + fwd[::-1]
    return step * iters


PATTERNS = {
    "sequential":   dict(label="Sequential loop",   stochastic=False, gen=sequential_loop),
    "random":       dict(label="Uniform random",    stochastic=True,  gen=uniform_random),
    "shuffled":     dict(label="Shuffled epochs",   stochastic=True,  gen=shuffled_epochs),
    "bursty":       dict(label="Bursty reuse",      stochastic=True,  gen=bursty),
    "matmul_naive": dict(label="Matmul (naive)",    stochastic=False, gen=matmul_naive),
    "matmul_tiled": dict(label="Matmul (tiled)",    stochastic=False, gen=matmul_tiled),
    "fwd_bwd":      dict(label="Forward-backward",  stochastic=False, gen=forward_backward),
}
ORDER = list(PATTERNS)
STOCHASTIC = {k for k, v in PATTERNS.items() if v["stochastic"]}


def build(name, seed=0, **params):
    return PATTERNS[name]["gen"](seed=seed, **params)
