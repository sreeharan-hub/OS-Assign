"""CA-3 experiments: reproduce the defect, kill matrix, regression on ML-shaped traces, fix cost, Belady, SLRU design.

Writes ca3/results/*.json|csv and ca3/figures/*.png.  Deterministic except the timing table.
Run:  python ca3/run_ca3.py
"""
import json
import math
import random
import statistics as stt
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT / "src"), str(ROOT / "experiments")]
import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import bugs  # noqa: E402
from bugs import (FIXES, MUTANTS, fifo_reference, lru_defective, lru_fix_ordered, lru_reference,  # noqa: E402
                  mutants, opt_reference)
from slru import slru  # noqa: E402
import simulator as S  # noqa: E402
import traces  # noqa: E402
from common import frames_for  # noqa: E402

RES, FIG = HERE / "results", HERE / "figures"
RES.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)
BLUE, ORANGE, AQUA, VIOLET, MAGENTA, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6", "#e87ba4", "#008300"
INK, INK2, GRID = "#1a1a1a", "#555555", "#dddddd"
plt.rcParams.update({"axes.edgecolor": GRID, "axes.labelcolor": INK2, "text.color": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titlesize": 8.5, "axes.labelsize": 7.5, "xtick.labelsize": 7,
                     "ytick.labelsize": 7, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.6, "axes.titlelocation": "left", "legend.frameon": False,
                     "legend.fontsize": 7.5, "font.size": 8, "lines.linewidth": 1.5, "lines.markersize": 3.4})
N_SEEDS = 10
TEXTBOOK = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
OUT = {}


def tcrit(n):
    return float(stats.t.ppf(0.975, n - 1))


def ci(xs):
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    return tcrit(len(xs)) * stt.stdev(xs) / math.sqrt(len(xs))


# =========================================================== 1. reproduce and trace the failure
def trace_table(impl_kind, trace, frames):
    """Frame contents after every reference for 'defective' (stamp only on load) or 'correct' LRU."""
    stamp, rows, faults = {}, [], 0
    for t, p in enumerate(trace, 1):
        fault = p not in stamp
        victim = None
        if fault:
            faults += 1
            if len(stamp) >= frames:
                victim = min(stamp, key=stamp.get)
                del stamp[victim]
            stamp[p] = t
        elif impl_kind == "correct":
            stamp[p] = t
        order = sorted(stamp, key=stamp.get)          # least -> most recent
        rows.append(dict(t=t, page=p, fault=fault, victim=victim, frames=order))
    return rows, faults


bad_rows, bad_f = trace_table("defective", TEXTBOOK, 3)
good_rows, good_f = trace_table("correct", TEXTBOOK, 3)
first_div = next(i for i, (a, b) in enumerate(zip(bad_rows, good_rows)) if a["victim"] != b["victim"])
OUT["repro"] = dict(trace=TEXTBOOK, frames=3, defective=lru_defective(TEXTBOOK, 3), reference=lru_reference(TEXTBOOK, 3),
                    fifo=fifo_reference(TEXTBOOK, 3), opt=opt_reference(TEXTBOOK, 3), first_divergence_step=first_div + 1,
                    bad_rows=bad_rows, good_rows=good_rows)

# =========================================================== 2. test-case design + kill matrix
rng0 = random.Random(2026)
RND = [[rng0.randrange(12) for _ in range(rng0.randrange(0, 61))] for _ in range(200)]
MONO = [[rng0.randrange(10) for _ in range(rng0.randrange(20, 80))] for _ in range(50)]
ZIPF = [min(int(rng0.paretovariate(1.2)), 400) for _ in range(60000)]


def t_textbook(f):  # normal
    return f(TEXTBOOK, 3) == 12


def t_frames1(f):  # boundary: one frame -> a fault at every page change
    tr = RND[7] + RND[11]
    return f(tr, 1) == sum(1 for i, p in enumerate(tr) if i == 0 or p != tr[i - 1])


def t_enough(f):  # boundary: frames >= distinct pages -> only compulsory faults
    return all(f(t, 12) == len(set(t)) and f(t, 40) == len(set(t)) for t in RND[:60])


def t_trivial(f):  # boundary: empty and single-page traces
    return f([], 3) == 0 and f([5], 3) == 1 and f([5] * 9, 2) == 1


def t_differential(f):  # differential test against the literal oracle
    return all(f(t, k) == lru_reference(t, k) for t in RND for k in (1, 2, 3, 5, 8))


def t_monotone(f):  # property: LRU is a stack algorithm -> never more faults with more frames
    for t in MONO:
        prev = None
        for k in range(1, 13):
            v = f(t, k)
            if prev is not None and v > prev:
                return False
            prev = v
    return True


def t_cyclic(f):  # adversarial: loop of k+1 pages through k frames -> every reference faults
    return all(f(list(range(k + 1)) * 6, k) == (k + 1) * 6 for k in (2, 3, 5, 9))


def t_bounds(f):  # property: OPT <= LRU <= number of references
    return all(opt_reference(t, k) <= f(t, k) <= len(t) for t in RND[:40] for k in (2, 4))


def t_stress(f):  # stress: 60,000 references, heavy-tailed popularity
    return f(ZIPF, 64) == lru_fix_ordered(ZIPF, 64)


TESTS = [("T1 textbook string (original failing case)", "normal", t_textbook),
         ("T2 one frame", "boundary", t_frames1),
         ("T3 frames >= distinct pages", "boundary", t_enough),
         ("T4 empty / single-page trace", "boundary", t_trivial),
         ("T5 differential vs literal oracle (1,000 cases)", "differential", t_differential),
         ("T6 monotone in frames (stack property)", "property", t_monotone),
         ("T7 cyclic loop of k+1 pages", "adversarial", t_cyclic),
         ("T8 OPT <= LRU <= n", "property", t_bounds),
         ("T9 60,000-reference heavy-tailed trace", "stress", t_stress)]
IMPLS = [("Provided code", lru_defective)] + [(f"Mutant {k}", mutants[k]) for k in MUTANTS] + \
        [(f"Fix {k}", v) for k, v in FIXES.items()]
kill = {}
for iname, fn in IMPLS:
    kill[iname] = [bool(t[2](fn)) for t in TESTS]      # True = test passes
OUT["tests"] = [dict(name=t[0], kind=t[1]) for t in TESTS]
OUT["kill"] = kill
OUT["mutants"] = {k: dict(desc=v[0], edit=v[1]) for k, v in MUTANTS.items()}

# invalid-input behaviour (recovery / edge case)
edge = []
for label, fn in (("Provided (defective)", lru_defective), ("Fix B (unguarded)", lru_fix_ordered), ("Selected (validated)", bugs.lru_final)):
    for bad in (0, -1):
        try:
            fn(TEXTBOOK, bad)
            res = "returns a number"
        except Exception as e:  # noqa: BLE001
            res = f"{type(e).__name__}: {e}"
        edge.append(dict(impl=label, frames=bad, result=res))
OUT["edge"] = edge

# =========================================================== 3. regression on ML-shaped workloads
MEMS = [10, 50]
reg = []
curves = {}
for name in traces.ORDER:
    seeds = range(N_SEEDS) if name in traces.STOCHASTIC else [0]
    per = {m: dict(bad=[], good=[], opt=[], fifo=[], n=[]) for m in (5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)}
    mism = 0
    for sd in seeds:
        tr = S.dedup(traces.build(name, seed=sd))
        fp = len(set(tr))
        for m in per:
            k = frames_for(fp, m)
            b, g = lru_defective(tr, k), lru_fix_ordered(tr, k)
            if m in (10, 50, 90) and sd == 0 and len(tr) < 200000:
                pass
            per[m]["bad"].append(b)
            per[m]["good"].append(g)
            per[m]["opt"].append(S.opt(tr, k))
            per[m]["fifo"].append(S.fifo(tr, k))
            per[m]["n"].append(len(tr))
            if b != S.fifo(tr, k):                   # the defective code must equal FIFO exactly
                mism += 1
    curves[name] = {m: {k: float(np.mean(v)) for k, v in d.items()} for m, d in per.items()}
    for m in MEMS:
        d = per[m]
        bad, good = np.mean(d["bad"]), np.mean(d["good"])
        reg.append(dict(pattern=name, label=traces.PATTERNS[name]["label"], mem=m, defective=float(bad), fixed=float(good),
                        opt=float(np.mean(d["opt"])), delta_pct=float((bad - good) / good * 100) if good else 0.0,
                        ci_bad_minus_good=float(ci([b - g for b, g in zip(d["bad"], d["good"])])),
                        n_runs=len(d["bad"]), identical=bool(all(b == g for b, g in zip(d["bad"], d["good"]))),
                        defective_is_fifo=(mism == 0)))
OUT["regression"] = reg
OUT["curves"] = curves

# cross-check: the three fixes and the src simulator agree with the oracle on every ML trace at every level
agree, total = 0, 0
for name in traces.ORDER:
    tr = S.dedup(traces.build(name, seed=0))
    fp = len(set(tr))
    for m in (5, 20, 50, 80, 100):
        k = frames_for(fp, m)
        vals = [lru_fix_ordered(tr, k), S.lru(tr, k), bugs.lru_fix_linked(tr, k)]
        if len(tr) * k < 3_000_000:
            vals += [bugs.lru_fix_timestamp(tr, k)]
        total += 1
        agree += int(len(set(vals)) == 1)
OUT["fix_agreement"] = dict(agree=agree, total=total)

# =========================================================== 4. cost of the candidate fixes
def bench(fn, trace, k, reps=5):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn(trace, k)
        ts.append(time.perf_counter() - t0)
    return stt.median(ts)


rr = random.Random(7)
timing = []
for k in (8, 64, 512):
    tr = [rr.randrange(2 * k) for _ in range(60000)]
    row = dict(frames=k, faults=lru_fix_ordered(tr, k))
    for nm, fn in FIXES.items():
        row[nm] = bench(fn, tr, k) / len(tr) * 1e6          # microseconds per reference
    row["Provided (defective)"] = bench(lru_defective, tr, k) / len(tr) * 1e6
    timing.append(row)
OUT["timing"] = timing

# =========================================================== 5. Belady / F2
def anomalies(fn, strings, maxk=9):
    n, ex = 0, None
    for s in strings:
        prev, hit = None, False
        for k in range(1, maxk + 1):
            v = fn(s, k)
            if prev is not None and v > prev:
                hit = True
                if ex is None:
                    ex = (s, k - 1, prev, k, v)
            prev = v
        n += hit
    return n, ex


rb = random.Random(11)
BSTR = [[rb.randrange(10) for _ in range(40)] for _ in range(5000)]
CAN = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
bel = {}
for nm, fn in (("FIFO (reference)", fifo_reference), ("LRU (reference)", lru_reference),
               ("LRU (provided, defective)", lru_defective), ("LRU (fix B)", lru_fix_ordered)):
    n, ex = anomalies(fn, BSTR)
    bel[nm] = dict(count=n, example=ex, canonical=[fn(CAN, k) for k in range(1, 8)])
OUT["belady"] = dict(results=bel, n_strings=len(BSTR), canonical=CAN)

# =========================================================== 6. design extension: scan-resistant SLRU
pols = {"FIFO": S.fifo, "LRU": S.lru, "SLRU (50% protected)": lambda t, k: slru(t, k, 0.5), "OPT": S.opt}
dsn = []
for name in ("bursty", "shuffled", "sequential", "matmul_naive", "fwd_bwd"):
    if name not in traces.PATTERNS:
        continue
    seeds = range(N_SEEDS) if name in traces.STOCHASTIC else [0]
    for m in (10, 30, 50, 70):
        res = {p: [] for p in pols}
        for sd in seeds:
            tr = S.dedup(traces.build(name, seed=sd))
            k = frames_for(len(set(tr)), m)
            for p, fn in pols.items():
                res[p].append(fn(tr, k) / len(tr))
        row = dict(pattern=name, label=traces.PATTERNS[name]["label"], mem=m)
        for p in pols:
            row[p] = float(np.mean(res[p]))
            row[p + "_ci"] = float(ci(res[p]))
        diff = [a - b for a, b in zip(res["LRU"], res["SLRU (50% protected)"])]
        row["lru_minus_slru"] = float(np.mean(diff))
        row["p"] = float(stats.ttest_rel(res["LRU"], res["SLRU (50% protected)"]).pvalue) if len(diff) > 1 and np.std(diff) > 0 else None
        row["n"] = len(diff)
        dsn.append(row)
OUT["design"] = dsn
sens = []
for frac in (0.25, 0.5, 0.75):
    xs = []
    for sd in range(N_SEEDS):
        tr = S.dedup(traces.build("bursty", seed=sd))
        k = frames_for(len(set(tr)), 30)
        xs.append(slru(tr, k, frac) / len(tr))
    sens.append(dict(frac=frac, mean=float(np.mean(xs)), ci=float(ci(xs))))
OUT["slru_sensitivity"] = sens

# =========================================================== figures
lab = {k: v["label"] for k, v in traces.PATTERNS.items()}
fig, ax = plt.subplots(figsize=(6.6, 2.7))
names = traces.ORDER
x = np.arange(len(names))
b10 = [next(r for r in reg if r["pattern"] == n and r["mem"] == 10) for n in names]
b50 = [next(r for r in reg if r["pattern"] == n and r["mem"] == 50) for n in names]
ax.bar(x - 0.2, [r["delta_pct"] for r in b10], 0.36, color=BLUE, label="10% memory")
ax.bar(x + 0.2, [r["delta_pct"] for r in b50], 0.36, color=ORANGE, label="50% memory")
ax.set_xticks(x)
ax.set_xticklabels([lab[n].replace(" ", "\n", 1) for n in names])
ax.set_ylabel("Extra faults from the bug (%)")
ax.set_title("Fig 1. How many extra page faults the defective LRU causes")
ax.legend()
fig.savefig(FIG / "fig1_inflation.png", dpi=200, bbox_inches="tight")
plt.close(fig)

fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.5))
for ax, name in zip(axes, ("shuffled", "bursty", "fwd_bwd")):
    ms = sorted(curves[name])
    ax.plot(ms, [curves[name][m]["bad"] / curves[name][m]["n"] for m in ms], color=ORANGE, label="Provided (defective)")
    ax.plot(ms, [curves[name][m]["good"] / curves[name][m]["n"] for m in ms], color=BLUE, label="Fixed LRU")
    ax.plot(ms, [curves[name][m]["opt"] / curves[name][m]["n"] for m in ms], color=GREEN, ls="--", label="OPT")
    ax.set_title(lab[name])
    ax.set_xlabel("Memory (% of footprint)")
axes[0].set_ylabel("Fault rate")
axes[0].legend(loc="upper right")
fig.suptitle("Fig 2. Before vs after the fix", x=0.01, ha="left", fontsize=8.5)
fig.tight_layout()
fig.savefig(FIG / "fig2_before_after.png", dpi=200, bbox_inches="tight")
plt.close(fig)

fig, ax = plt.subplots(figsize=(6.6, 2.5))
w = 0.27
for i, (nm, c) in enumerate(zip(FIXES, (ORANGE, BLUE, AQUA))):
    ax.bar(np.arange(3) + (i - 1) * w, [r[nm] for r in timing], w, color=c, label=nm)
ax.set_xticks(range(3))
ax.set_xticklabels([f"{r['frames']} frames" for r in timing])
ax.set_ylabel("µs per reference")
ax.set_yscale("log")
ax.set_title("Fig 3. Cost of the candidate fixes (lower is better)")
ax.legend()
fig.savefig(FIG / "fig3_fix_cost.png", dpi=200, bbox_inches="tight")
plt.close(fig)

fig, ax = plt.subplots(figsize=(6.6, 2.6))
ms = (10, 30, 50, 70)
for p, c, mk in (("FIFO", ORANGE, "s"), ("LRU", BLUE, "o"), ("SLRU (50% protected)", VIOLET, "^"), ("OPT", GREEN, "")):
    ax.plot(ms, [next(r for r in dsn if r["pattern"] == "bursty" and r["mem"] == m)[p] for m in ms], color=c,
            marker=mk, label=p, ls="--" if p == "OPT" else "-")
ax.set_xlabel("Memory (% of footprint)")
ax.set_ylabel("Fault rate")
ax.set_title("Fig 4. Bursty reuse: a scan-resistant alternative (mean of 10 seeds)")
ax.legend()
fig.savefig(FIG / "fig4_slru.png", dpi=200, bbox_inches="tight")
plt.close(fig)

(RES / "ca3_results.json").write_text(json.dumps(OUT, indent=1, default=str))
print("CA-3 results written;", "defective ==", OUT["repro"]["defective"], "reference ==", OUT["repro"]["reference"])
