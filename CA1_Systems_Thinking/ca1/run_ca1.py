"""CA-1 experiments. Core code is standard-library only; figures need matplotlib (optional).
Run:  python3 run_ca1.py      -> results/ca1_results.json, results/ca1_tables.txt, figures/*.png
"""
import json, random, os
from policies import fifo, lru, mru, opt, POLICIES, effective_access_time
from workloads import epoch_scan, shuffled_epoch, sharded_epoch, hot_plus_stream, uniform_random
from working_set import wss_series, steady_fault_rate, cpu_utilisation

HERE = os.path.dirname(os.path.abspath(__file__))
W, F = 1200, 700                     # dataset pages, frames available to the application
MA, HDD, NVME = 200.0, 8_000_000.0, 100_000.0   # ns: memory access, fault service times (assumed)
TEXTBOOK = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
R = {"params": dict(W=W, F=F, ma_ns=MA, hdd_ns=HDD, nvme_ns=NVME)}
out = []


def say(s=""):
    print(s)
    out.append(s)


# ---------------------------------------------------------------- E1 textbook string (Challenge F2)
say("E1  Textbook reference string, 3 frames")
e1 = {}
for name, f in (("FIFO", fifo), ("LRU", lru), ("OPT", opt)):
    k = f(TEXTBOOK, 3)
    e1[name] = dict(faults=k, hit_ratio=round(1 - k / len(TEXTBOOK), 3))
    say(f"  {name:4s} faults={k:2d}  hit ratio={1 - k / len(TEXTBOOK):.2f}")
R["E1_textbook"] = e1

# ---------------------------------------------------------------- E2 policies x workloads at F frames
work = {
    "A epoch scan (same order)": epoch_scan(W, 6),
    "B shuffled epochs": shuffled_epoch(W, 6),
    "C sharded (shard 500, 3 passes)": sharded_epoch(W, 2, 500, 3),
    "D hot weights + stream": hot_plus_stream(W, 100, 6),
}
say(f"\nE2  Faults at F={F} of W={W} pages ({F / W:.0%} of dataset)")
say(f"  {'workload':34s}{'refs':>7s}" + "".join(f"{n:>8s}" for n in POLICIES) + f"{'p(LRU)':>9s}")
e2 = {}
for wn, tr in work.items():
    row = {n: f(tr, F) for n, f in POLICIES.items()}
    row["refs"] = len(tr)
    row["p_LRU"] = row["LRU"] / len(tr)
    row["distinct"] = len(set(tr))
    e2[wn] = row
    say(f"  {wn:34s}{len(tr):7d}" + "".join(f"{row[n]:8d}" for n in POLICIES) + f"{row['p_LRU']:9.3f}")
R["E2_policies"] = e2

# ---------------------------------------------------------------- E3 fault rate vs frames
say("\nE3  LRU fault rate vs frames")
frames_grid = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200]
e3 = {"frames": frames_grid}
for wn in ("A epoch scan (same order)", "B shuffled epochs", "C sharded (shard 500, 3 passes)", "D hot weights + stream"):
    e3[wn] = [round(lru(work[wn], f) / len(work[wn]), 4) for f in frames_grid]
    say(f"  {wn:34s}" + " ".join(f"{x:.3f}" for x in e3[wn]))
R["E3_frames_sweep"] = e3

# ---------------------------------------------------------------- E4 effective access time
say("\nE4  Effective access time (ma=200 ns) and slowdown vs all-in-RAM")
e4 = {}
for wn, row in e2.items():
    p = row["p_LRU"]
    e4[wn] = {"p": round(p, 4),
              "EAT_hdd_us": round(effective_access_time(p, MA, HDD) / 1000, 1),
              "slow_hdd": round(effective_access_time(p, MA, HDD) / MA),
              "EAT_nvme_us": round(effective_access_time(p, MA, NVME) / 1000, 1),
              "slow_nvme": round(effective_access_time(p, MA, NVME) / MA)}
    say(f"  {wn:34s} p={p:.3f}  HDD {e4[wn]['EAT_hdd_us']:9.1f} us ({e4[wn]['slow_hdd']}x)   NVMe {e4[wn]['EAT_nvme_us']:8.1f} us ({e4[wn]['slow_nvme']}x)")
p_hdd = 0.1 * MA / (HDD - MA)
p_nvme = 0.1 * MA / (NVME - MA)
R["E4_eat"] = e4
R["E4_max_p_for_10pct_slowdown"] = dict(hdd=p_hdd, nvme=p_nvme)
say(f"  max p for <=10% slowdown: HDD {p_hdd:.2e}   NVMe {p_nvme:.2e}")

# ---------------------------------------------------------------- E5 working set
say("\nE5  Working-set size WSS: distinct pages in a window of 1200 refs (one epoch = the reuse interval)")
e5 = {}
for wn, tr in work.items():
    s = wss_series(tr, W, 100)
    fit = sum(1 for v in s if v <= F) / len(s)
    e5[wn] = dict(mean=round(sum(s) / len(s)), max=max(s), min=min(s), fit_fraction=round(fit, 2))
    say(f"  {wn:34s} mean={e5[wn]['mean']:4d} max={e5[wn]['max']:4d}   windows with WSS<=F={F}: {fit:.0%}")
R["E5_wss"] = e5

# ---------------------------------------------------------------- E6 thrashing model
say("\nE6  Thrashing model: processes with w=100 pages each, M=1000 frames, LRU")
w, M = 100, 1000
tr = uniform_random(w, 30000)
cache = {}


def p_of(fr):
    if fr not in cache:
        cache[fr] = steady_fault_rate(tr, fr, 3000)
    return cache[fr]


e6 = []
for n in list(range(1, 21)) + [25, 30]:
    u, p = cpu_utilisation(n, M, p_of)
    e6.append(dict(N=n, frames_each=max(1, M // n), p=round(p, 4), util=round(u, 3)))
R["E6_thrashing"] = e6
for r in e6:
    if r["N"] in (1, 2, 5, 10, 11, 12, 14, 16, 20, 30):
        say(f"  N={r['N']:2d} frames each={r['frames_each']:4d} p={r['p']:.3f} CPU util={r['util']:.3f}")

# ---------------------------------------------------------------- E7 checking claims (AI verification)
say("\nE7  Checking common claims by random search (20,000 strings)")
rng = random.Random(7)
lru_worse = belady = lru_not_opt = 0
ex_lru_worse = None
for _ in range(20000):
    s = [rng.randrange(10) for _ in range(rng.randint(15, 50))]
    f = rng.randint(2, 6)
    a, b = fifo(s, f), lru(s, f)
    if b > a:
        lru_worse += 1
        ex_lru_worse = ex_lru_worse or (s, f, a, b)
    if fifo(s, f + 1) > a:
        belady += 1
    if opt(s, f) > min(a, b):
        lru_not_opt += 1
e7 = dict(trials=20000, lru_worse_than_fifo=lru_worse, fifo_more_frames_more_faults=belady, opt_worse_than_other=lru_not_opt)
R["E7_claims"] = e7
say(f"  LRU worse than FIFO on {lru_worse} strings; FIFO faulted MORE with one extra frame on {belady}; OPT beaten on {lru_not_opt}")
if ex_lru_worse:
    s, f, a, b = ex_lru_worse
    R["E7_example"] = dict(refs=s, frames=f, fifo=a, lru=b)
    say(f"  example where LRU loses: frames={f}, FIFO={a}, LRU={b}")

json.dump(R, open(os.path.join(HERE, "results", "ca1_results.json"), "w"), indent=1)
open(os.path.join(HERE, "results", "ca1_tables.txt"), "w").write("\n".join(out) + "\n")

# ---------------------------------------------------------------- figures (optional)
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("matplotlib not installed - figures skipped")
    raise SystemExit
BL, OR, AQ, VI = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})

fig, ax = plt.subplots(figsize=(6.4, 3.6))
for key, col, ls in (("A epoch scan (same order)", OR, "-"), ("B shuffled epochs", BL, "-"),
                     ("C sharded (shard 500, 3 passes)", AQ, "-"), ("D hot weights + stream", VI, "-")):
    ax.plot(e3["frames"], e3[key], color=col, lw=2, marker="o", ms=4, label=key)
ax.axvline(F, color="#888", ls="--", lw=1)
ax.text(F + 15, 0.93, "F = 700", color="#555", fontsize=8)
ax.set_xlabel("frames given to the application"); ax.set_ylabel("page-fault rate (LRU)")
ax.set_title("Fault rate falls only when frames approach the working set", fontsize=10)
ax.legend(fontsize=7, frameon=False); fig.tight_layout()
fig.savefig(os.path.join(HERE, "figures", "fig1_fault_rate_vs_frames.png"), dpi=200); plt.close(fig)

fig, ax = plt.subplots(figsize=(6.4, 3.6))
names = list(e2)
x = range(len(names)); wd = 0.2
for i, (pn, col) in enumerate((("FIFO", OR), ("LRU", BL), ("MRU", VI), ("OPT", AQ))):
    ax.bar([j + (i - 1.5) * wd for j in x], [e2[n][pn] / e2[n]["refs"] for n in names], wd - 0.02, color=col, label=pn)
ax.set_xticks(list(x)); ax.set_xticklabels([n.split(" (")[0].replace(" ", "\n", 1) for n in names], fontsize=7)
ax.set_ylabel("page-fault rate at F = 700"); ax.legend(fontsize=7, frameon=False, ncol=4)
ax.set_title("Policy matters less than access pattern", fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "figures", "fig2_policy_by_workload.png"), dpi=200); plt.close(fig)

fig, ax = plt.subplots(figsize=(6.4, 3.6))
ax.plot([r["N"] for r in e6], [r["util"] for r in e6], color=BL, lw=2, marker="o", ms=4)
ax.axvline(M // w, color="#888", ls="--", lw=1); ax.text(M // w + 0.3, 0.5, "N = M / w = 10", color="#555", fontsize=8)
ax.set_xlabel("degree of multiprogramming N"); ax.set_ylabel("CPU utilisation")
ax.set_title("Thrashing: utilisation collapses once N x w exceeds M", fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "figures", "fig3_thrashing.png"), dpi=200); plt.close(fig)
print("figures written")
