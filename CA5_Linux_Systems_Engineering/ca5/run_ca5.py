"""CA-5 experiments on a real Linux kernel.  Writes ca5/results/ca5_results.json and ca5/figures/*.png.

Run:  python ca5/run_ca5.py          (about 5-8 minutes; needs Linux, strace and taskset)
Safety: every mapping is <= 200 MiB, all processes are children created by this script, nothing system-wide is modified.
"""
import json
import os
import platform
import re
import shutil
import signal
import statistics as stt
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT / "src")]
import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import procinfo  # noqa: E402
import simulator as S  # noqa: E402
import traces  # noqa: E402

RES, FIG = HERE / "results", HERE / "figures"
RES.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)
PY = sys.executable
BLUE, ORANGE, AQUA, VIOLET, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6", "#008300"
INK, INK2, GRID = "#1a1a1a", "#555555", "#dddddd"
plt.rcParams.update({"axes.edgecolor": GRID, "axes.labelcolor": INK2, "text.color": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titlesize": 8.5, "axes.labelsize": 7.5, "xtick.labelsize": 7,
                     "ytick.labelsize": 7, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.6, "axes.titlelocation": "left", "legend.frameon": False,
                     "legend.fontsize": 7.5, "font.size": 8, "lines.linewidth": 1.5, "lines.markersize": 3.4})
OUT = {}
QUICK = "--quick" in sys.argv


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def worker(*args, wrap=()):
    r = sh([*wrap, PY, str(HERE / "replay_worker.py"), *map(str, args)], timeout=300)
    if r.returncode:
        raise RuntimeError(r.stderr[-400:])
    return json.loads(r.stdout.strip().splitlines()[-1])


# ============================================================ A. environment
def first_line(cmd):
    try:
        r = sh(cmd)
        return (r.stdout or r.stderr).strip().splitlines()[0]
    except Exception:  # noqa: BLE001
        return "unavailable"


def cpu_model():
    for line in open("/proc/cpuinfo"):
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return "unknown"


osr = dict(l.strip().split("=", 1) for l in open("/etc/os-release") if "=" in l)
OUT["env"] = dict(
    distribution=osr.get("PRETTY_NAME", "").strip('"'), kernel=platform.release(), kernel_full=" ".join(platform.uname()),
    cpu=cpu_model(), cpus=os.cpu_count(), affinity=sorted(os.sched_getaffinity(0)),
    ram_gb=round(int(open("/proc/meminfo").readline().split()[1]) / 1024 / 1024, 1),
    page_size=procinfo.PAGE, python=platform.python_version(), strace=first_line(["strace", "-V"]),
    taskset=first_line(["taskset", "--version"]), vmstat=first_line(["vmstat", "-V"]),
    thp=open("/sys/kernel/mm/transparent_hugepage/enabled").read().strip(),
    virtualisation="Firecracker micro-VM (cloud sandbox)" if "fc" in platform.release() else "unknown",
    rustc=first_line(["rustc", "--version"]), date=time.strftime("%Y-%m-%d"))
print("environment:", OUT["env"]["kernel"], OUT["env"]["cpus"], "CPUs")

# ============================================================ B. instrument validation + process lifecycle (L1/L3/L25)
child_code = r"""
import mmap, os, resource, sys
P = os.sysconf('SC_PAGE_SIZE'); n = 2000
m = mmap.mmap(-1, n * P)
for i in range(n): m[i * P] = 1
f = open('/proc/self/stat').read().rsplit(')', 1)[1].split()
print(resource.getrusage(resource.RUSAGE_SELF).ru_minflt, int(f[7]), flush=True)
sys.stdin.readline()          # block here: the counters are frozen while we measure from outside
"""
p = subprocess.Popen([PY, "-c", child_code], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
ru, st = map(int, p.stdout.readline().split())
time.sleep(0.2)
ps_min = int(sh(["ps", "-o", "min_flt=", "-p", str(p.pid)]).stdout.strip())
pi = procinfo.snapshot(p.pid)
states = [("blocked on stdin (read)", pi["state"])]
os.kill(p.pid, signal.SIGSTOP)
time.sleep(0.2)
states.append(("after SIGSTOP", procinfo.read_stat(p.pid)["state"]))
os.kill(p.pid, signal.SIGCONT)
time.sleep(0.2)
states.append(("after SIGCONT", procinfo.read_stat(p.pid)["state"]))
p.stdin.write("\n")
p.stdin.flush()
time.sleep(0.3)                                      # child exits; parent has not reaped it yet
try:
    states.append(("exited, not yet waited for", procinfo.read_stat(p.pid)["state"]))
except OSError:
    states.append(("exited, not yet waited for", "gone"))
ru_children = os.wait4(p.pid, 0)[2].ru_minflt
try:
    states.append(("after wait()", procinfo.read_stat(p.pid)["state"]))
except OSError:
    states.append(("after wait()", "(no /proc entry)"))
OUT["instruments"] = dict(getrusage_self=ru, proc_stat_self=st, ps_min_flt=ps_min, procinfo_external=pi["minflt"],
                          wait4_at_exit=ru_children, pages_touched=2000, states=states, ppid_of_child=pi["ppid"],
                          parent_pid=os.getpid(), threads=pi["threads"], vmrss_kb=pi["vmrss_kb"])
print("instruments:", OUT["instruments"]["getrusage_self"], OUT["instruments"]["ps_min_flt"], states)

# ============================================================ C. demand paging and memory growth
dem = {}
N_DEM, REPS = 50_000, (2 if QUICK else 5)
for mode in ("demand", "populate"):
    runs = []
    for _ in range(REPS):
        r = sh([PY, str(HERE / "demand_worker.py"), str(N_DEM), mode], timeout=300)
        runs.append(json.loads(r.stdout.strip().splitlines()[-1]))
    dem[mode] = runs
OUT["demand"] = dem
print("demand done")

# ============================================================ D. replay grid: simulator vs real kernel
LEVELS = (10, 30, 50, 70, 90)
POL = ("FIFO", "LRU", "OPT")
grid = []
t_grid = time.time()
for pat in traces.ORDER:
    for pol in POL:
        for mem in (LEVELS if not QUICK else (10, 50)):
            for rep in range(2 if not QUICK else 1):
                grid.append(dict(worker(pat, 0, pol, mem), rep=rep))
extra = []
for pat in ("random", "shuffled", "bursty"):
    for sd in (1, 2):
        for mem in (10, 50):
            extra.append(worker(pat, sd, "LRU", mem))
OUT["grid"] = [{k: v for k, v in g.items() if k != "rss_samples"} for g in grid]
OUT["extra_seeds"] = [{k: v for k, v in g.items() if k != "rss_samples"} for g in extra]
print("grid done", len(grid), "runs in", round(time.time() - t_grid), "s")

# ============================================================ E. strace cross-check (L24)
strace_rows = []
for pat, pol, mem in (("sequential", "LRU", 10), ("bursty", "LRU", 30), ("matmul_tiled", "FIFO", 10)):
    outf = RES / f"strace_{pat}_{pol}_{mem}.txt"
    cmd = ["strace", "-f", "-c", "-e", "trace=madvise,mmap,munmap", "-o", str(outf), PY,
           str(HERE / "replay_worker.py"), pat, "0", pol, str(mem)]
    r = sh(cmd, timeout=900)
    res = json.loads(r.stdout.strip().splitlines()[-1])
    txt = outf.read_text()
    calls = {}
    for line in txt.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[-1] in ("madvise", "mmap", "munmap") and parts[3].isdigit():
            calls[parts[-1]] = int(parts[3])
    strace_rows.append(dict(pattern=pat, policy=pol, mem=mem, evictions=res["evictions"], faults=res["predicted"],
                            madvise_calls=calls.get("madvise", 0), mmap_calls=calls.get("mmap", 0),
                            munmap_calls=calls.get("munmap", 0), minflt=res["minflt"]))
    print("strace", strace_rows[-1])
OUT["strace"] = strace_rows

# ============================================================ F. control: CPU affinity (taskset) and run-to-run variability
NR = 8 if QUICK else 20
free, pinned = [], []
for _ in range(NR):                                           # interleave to cancel drift
    free.append(worker("bursty", 0, "LRU", 30))
    pinned.append(worker("bursty", 0, "LRU", 30, wrap=("taskset", "-c", "0")))


def summ(rs):
    s = [r["seconds"] * 1e3 for r in rs]
    return dict(mean_ms=stt.mean(s), sd_ms=stt.stdev(s), cv=stt.stdev(s) / stt.mean(s), min_ms=min(s), max_ms=max(s),
                faults=sorted({r["minflt"] for r in rs}), n=len(s))


OUT["affinity"] = dict(unpinned=summ(free), pinned=summ(pinned),
                       mannwhitney_p=float(stats.mannwhitneyu([r["seconds"] for r in free], [r["seconds"] for r in pinned]).pvalue))
print("affinity", OUT["affinity"]["unpinned"]["cv"], OUT["affinity"]["pinned"]["cv"])

# ============================================================ G. memory vs workload: peak resident set vs frame budget
rssrows = []
for pat, mem in (("sequential", 10), ("sequential", 50), ("random", 10), ("random", 50), ("bursty", 10), ("bursty", 30), ("matmul_tiled", 10)):
    r = worker(pat, 0, "LRU", mem, "--rss", "64")
    peak = max(r["rss_samples"])
    rssrows.append(dict(pattern=pat, mem=mem, frames=r["frames"], footprint=r["footprint"], rss0=r["rss0"], peak=peak,
                        peak_growth=peak - r["rss0"], samples=r["rss_samples"][:: max(1, len(r["rss_samples"]) // 200)]))
OUT["rss"] = rssrows

# ============================================================ analysis + figures
G = OUT["grid"]
diff = [g["minflt"] - g["predicted"] for g in G]
OUT["summary"] = dict(runs=len(G), exact=sum(1 for d in diff if d == 0), offset_values=sorted(set(diff)),
                      max_abs_diff=max(abs(d) for d in diff), majflt_total=sum(g["majflt"] for g in G),
                      vm_diff=sorted({g["vmstat_pgfault"] - g["minflt"] for g in G}))
xs = np.array([g["minflt"] for g in G], float)
refs = np.array([g["refs"] for g in G], float)
ys = np.array([g["seconds"] for g in G], float)
A = np.column_stack([np.ones_like(xs), refs, xs])
coef, *_ = np.linalg.lstsq(A, ys, rcond=None)
pred_t = A @ coef
r2 = 1 - ((ys - pred_t) ** 2).sum() / ((ys - ys.mean()) ** 2).sum()
OUT["cost_fit"] = dict(intercept_ms=coef[0] * 1e3, ns_per_ref=coef[1] * 1e9, us_per_fault=coef[2] * 1e6, r2=float(r2))
slope, intercept, r_val = coef[2], coef[0], r2 ** 0.5
OUT["summary"]["min_predicted"] = min(g["predicted"] for g in G)
OUT["summary"]["max_rel_err"] = max(abs(g["minflt"] - g["predicted"]) / g["predicted"] for g in G)
# repeat consistency
by = {}
for g in G:
    by.setdefault((g["pattern"], g["policy"], g["mem"]), []).append(g["minflt"])
OUT["repeat_identical"] = sum(1 for v in by.values() if len(set(v)) == 1), len(by)

lab = {k: v["label"] for k, v in traces.PATTERNS.items()}
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0))
ax = axes[0]
ax.scatter([g["predicted"] for g in G], [g["minflt"] for g in G], s=9, color=BLUE, alpha=0.7)
mx = max(g["predicted"] for g in G) * 1.1
ax.plot([1, mx], [1, mx], color=ORANGE, ls="--", lw=1)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Simulator: predicted faults")
ax.set_ylabel("Linux kernel: measured minor faults")
ax.set_title("Fig 1a. Real vs predicted (210 runs)")
ax = axes[1]
vals = sorted(set(diff))
ax.bar(vals, [diff.count(v) for v in vals], width=0.6, color=BLUE)
ax.set_xticks(vals)
ax.set_xlabel("measured − predicted (faults)")
ax.set_ylabel("runs")
ax.set_title("Fig 1b. Difference per run")
fig.tight_layout()
fig.savefig(FIG / "fig1_real_vs_sim.png", dpi=200, bbox_inches="tight")
plt.close(fig)

fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.6))
for ax, pat in zip(axes, ("shuffled", "matmul_naive", "fwd_bwd")):
    for pol, c, mk in (("FIFO", ORANGE, "s"), ("LRU", BLUE, "o"), ("OPT", GREEN, "^")):
        pts = sorted({(g["mem"], g["minflt"]) for g in G if g["pattern"] == pat and g["policy"] == pol})
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=c, marker=mk, label=pol)
    ax.set_title(lab[pat])
    ax.set_xlabel("Memory (% of footprint)")
axes[0].set_ylabel("Kernel minor faults")
axes[0].legend()
fig.suptitle("Fig 2. Fault curves measured on the Linux kernel", x=0.01, ha="left", fontsize=8.5)
fig.tight_layout()
fig.savefig(FIG / "fig2_real_curves.png", dpi=200, bbox_inches="tight")
plt.close(fig)

d0 = dem["demand"][0]
fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.7))
pg = [s["pages"] for s in d0["steps"]]
axes[0].plot(pg, [s["cum_faults"] for s in d0["steps"]], color=BLUE, marker="o", label="cumulative minor faults")
axes[0].plot(pg, [s["rss_kb"] / 4 for s in d0["steps"]], color=ORANGE, ls="--", label="VmRSS / 4 KiB")
axes[0].set_xlabel("pages touched")
axes[0].set_ylabel("count")
axes[0].set_title("Fig 3a. Demand paging: faults and RSS track pages touched")
axes[0].legend()
md_ = [np.mean([r["first"]["seconds"] for r in dem[m]]) * 1e3 for m in ("demand", "populate")]
md_sd = [np.std([r["first"]["seconds"] for r in dem[m]], ddof=1) * 1e3 for m in ("demand", "populate")]
axes[1].bar(["demand", "MAP_POPULATE"], md_, yerr=md_sd, color=[BLUE, ORANGE], width=0.5, capsize=3)
axes[1].set_ylabel("ms to bring in 50,000 pages")
axes[1].set_title("Fig 3b. Intervention: pre-populating the mapping")
fig.tight_layout()
fig.savefig(FIG / "fig3_demand.png", dpi=200, bbox_inches="tight")
plt.close(fig)

fig, ax = plt.subplots(figsize=(6.4, 2.6))
ax.scatter(pred_t * 1e3, ys * 1e3, s=9, color=VIOLET, alpha=0.7)
mxx = ys.max() * 1e3
ax.plot([0, mxx], [0, mxx], color=ORANGE, ls="--", lw=1)
ax.set_xlabel("time predicted from references and faults (ms)")
ax.set_ylabel("measured elapsed time (ms)")
ax.set_title(f"Fig 4. Elapsed time = {coef[1] * 1e9:.0f} ns/reference + {coef[2] * 1e6:.2f} µs/fault (R² = {r2:.3f})")
fig.savefig(FIG / "fig4_time_vs_faults.png", dpi=200, bbox_inches="tight")
plt.close(fig)

fig, ax = plt.subplots(figsize=(6.4, 2.6))
for r, c in zip((x for x in rssrows if x["pattern"] in ("sequential", "bursty") and x["mem"] in (10, 30)), (BLUE, ORANGE)):
    ax.plot(np.arange(len(r["samples"])) / len(r["samples"]) * 100, [s - r["rss0"] for s in r["samples"]], color=c,
            label=f"{lab[r['pattern']]}, {r['frames']} frames ({r['mem']}%)")
    ax.axhline(r["frames"], color=c, ls=":", lw=1)
ax.set_xlabel("progress through the reference string (%)")
ax.set_ylabel("resident pages above start")
ax.set_title("Fig 5. Resident set rises to the frame budget and stays there (dotted = budget)")
ax.legend()
fig.savefig(FIG / "fig5_rss.png", dpi=200, bbox_inches="tight")
plt.close(fig)

(RES / "ca5_results.json").write_text(json.dumps(OUT, indent=1))
print("CA-5 results written:", OUT["summary"], OUT["cost_fit"])
