"""Statistics shared by figs2.py, build_paper3.py and build_slides.py. Reads results/*.json."""
import json, os
import numpy as np
from scipy import stats, optimize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")


def load(name):
    p = os.path.join(RES, name)
    return json.load(open(p)) if os.path.exists(p) else None


R = load("rust_final.json")
PG = load("py_gil.json")
PF = load("py_ft.json")
F_HEAP = load("followup_heap_thread.json")
F_CPU2 = load("followup_cpu2.json")
F_PARK = load("followup_park.json")
F_FORK_LIVE = load("followup_fork_live.json")
F_POOL_IPC = load("followup_pool_ipc.json")
F_TOPO = load("followup_topo.json")
P_SYS = load("py_sys.json")


# ---------- statistics ----------
def ci(x, level=0.95):
    """mean and half-width of the t confidence interval"""
    x = np.asarray(x, float)
    n = len(x)
    m = x.mean()
    if n < 2:
        return m, 0.0
    h = stats.sem(x) * stats.t.ppf((1 + level) / 2, n - 1)
    return m, h


def mean(x): return float(np.mean(x))
def med(x): return float(np.median(x))


def mwu(a, b):
    """two-sided Mann-Whitney U p-value"""
    try:
        return float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue)
    except ValueError:
        return 1.0


def pfmt(p):
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def pm(x, d=1):
    m, h = ci(x)
    return f"{m:,.{d}f} ± {h:,.{d}f}"


def keys(d):
    return sorted(d, key=lambda k: int(k))


# ---------- Amdahl ----------
def amdahl_fit(ws, times):
    """serial fraction s from speed-up S(w)=1/(s+(1-s)/w); times are mean wall times"""
    ws = np.array(ws, float)
    t = np.array(times, float)
    sp = t[0] / t
    f = lambda w, s: 1.0 / (s + (1 - s) / w)
    try:
        s, _ = optimize.curve_fit(f, ws, sp, p0=[0.01], bounds=(0, 1))
        return float(s[0])
    except Exception:
        return float("nan")


def speedups(d):
    """d: {w: samples} -> (ws, mean speed-up vs w=1, half-width of CI on speed-up)"""
    ks = keys(d)
    base = np.array(d[ks[0]], float)
    ws, sp, hw = [], [], []
    for k in ks:
        x = np.array(d[k], float)
        r = base.mean() / x
        ws.append(int(k))
        sp.append(base.mean() / x.mean())
        # delta method for ratio of means
        n = len(x)
        se = (base.mean() / x.mean()) * np.sqrt((stats.sem(base) / base.mean()) ** 2 + (stats.sem(x) / x.mean()) ** 2) if n > 1 else 0
        hw.append(1.96 * se)
    return ws, sp, hw


# ---------- per-task overhead model ----------
W = 24


def per_task_overhead_us(times, n, d_us):
    """effective cost per task on W workers minus the task's own duration (microseconds)"""
    return np.mean(times) * W / n * 1e6 - d_us


def wall_per_task_us(times, n):
    """wall-clock microseconds per task for a run that completed n tasks"""
    return float(np.mean(times)) * 1e6 / n


def overhead_fraction(c_us, d_us):
    return c_us / (c_us + d_us)
