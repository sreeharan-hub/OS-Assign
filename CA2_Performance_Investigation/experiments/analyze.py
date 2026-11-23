"""Statistics, tables and figures from the raw CSVs.

Outputs
  results/summary_main.csv        mean / sd / 95% CI per (pattern, policy, memory)
  results/stats_fifo_vs_lru.csv   paired t-tests (FIFO vs LRU) at 10/50/90 %
  results/tables/*.md             markdown tables used by the report
  results/figures/*.png           figures used by the report
"""
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import FIGURES, MEM_LEVELS, RESULTS  # noqa: E402
import traces  # noqa: E402

TABLES = RESULTS / "tables"
TABLES.mkdir(exist_ok=True)
LABEL = {k: v["label"] for k, v in traces.PATTERNS.items()}
ORDER = traces.ORDER
KEY_MEM = [10, 50, 90]

# categorical slots from the validated reference palette (fixed order, not cycled)
COL = {"FIFO": "#2a78d6", "LRU": "#eb6834", "OPT": "#1baf7a",
       "MRU": "#6250d6", "RANDOM": "#e87ba4", "CLOCK": "#008300"}
DASH = {"FIFO": "-", "LRU": "-", "OPT": "-", "MRU": "--", "RANDOM": ":", "CLOCK": "-."}
MARK = {"FIFO": "o", "LRU": "s", "OPT": "^", "MRU": "v", "RANDOM": "D", "CLOCK": "P"}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.titlesize": 8.5,
    "axes.labelsize": 7.5, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.titlelocation": "left", "legend.frameon": False, "legend.fontsize": 7.5,
    "font.size": 8, "lines.linewidth": 1.5, "lines.markersize": 3.4,
})


def tcrit(n):
    return stats.t.ppf(0.975, n - 1) if n > 1 else float("nan")


def md_table(df, floatfmt="{:.3f}"):
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |",
           "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append("–" if math.isnan(v) else floatfmt.format(v))
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def grid(n_panels, ncols=3, width=7.6, row_h=2.75):
    """Panel grid sized for a 6.5-inch report column; spare cells are blanked
    (the first spare cell is used for the legend)."""
    nrows = -(-(n_panels + 1) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(width, row_h * nrows + 0.5))
    axes = list(axes.ravel())
    for ax in axes[n_panels:]:
        ax.axis("off")
    return fig, axes


def save_fig(fig, name):
    fig.savefig(FIGURES / name, dpi=200, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------- main
def load_main():
    d = pd.read_csv(RESULTS / "raw_main.csv")
    d["replicate"] = np.where(d.pattern.isin(traces.STOCHASTIC), d.trace_seed, d.policy_seed)
    return d


def summarise(d):
    rows = []
    for (pat, pol, mem), g in d.groupby(["pattern", "policy", "mem_pct"]):
        x = g.fault_rate.to_numpy()
        n = len(x)
        sd = x.std(ddof=1) if n > 1 else float("nan")
        ci = tcrit(n) * sd / math.sqrt(n) if n > 1 else float("nan")
        rows.append(dict(pattern=pat, policy=pol, mem_pct=mem, n=n, mean=x.mean(),
                         sd=sd, ci95=ci, frames=int(g.frames.iloc[0]),
                         footprint=int(g.footprint.iloc[0])))
    s = pd.DataFrame(rows)
    s.to_csv(RESULTS / "summary_main.csv", index=False)
    return s


def table_main(s):
    rows = []
    for pat in ORDER:
        for mem in KEY_MEM:
            r = dict(Pattern=LABEL[pat], Memory=f"{mem}%")
            for pol in ("FIFO", "LRU", "OPT"):
                x = s[(s.pattern == pat) & (s.policy == pol) & (s.mem_pct == mem)].iloc[0]
                r[pol] = (f"{x['mean']:.3f} ±{x.ci95:.3f}" if x.n > 1 else f"{x['mean']:.3f}")
            rows.append(r)
    t = pd.DataFrame(rows)
    (TABLES / "table1_main.md").write_text(md_table(t))
    return t


def stats_fifo_lru(d):
    rows = []
    for pat in ORDER:
        for mem in KEY_MEM:
            g = d[(d.pattern == pat) & (d.mem_pct == mem)]
            a = g[g.policy == "FIFO"].sort_values("trace_seed").fault_rate.to_numpy()
            b = g[g.policy == "LRU"].sort_values("trace_seed").fault_rate.to_numpy()
            diff = b - a
            p = dz = float("nan")
            if len(a) > 1 and np.ptp(diff) > 0:
                p = stats.ttest_rel(b, a).pvalue
                dz = diff.mean() / diff.std(ddof=1)
            if len(a) == 1:
                note = "single run"
            elif np.ptp(diff) == 0:
                note = "identical in every seed" if diff[0] == 0 else "same difference in every seed"
            else:
                note = ""
            rows.append(dict(pattern=pat, mem_pct=mem, n=len(a), fifo=a.mean(), lru=b.mean(),
                             lru_minus_fifo=diff.mean(), p_value=p, cohens_dz=dz,
                             seeds_lru_better=int((diff < 0).sum()),
                             seeds_lru_worse=int((diff > 0).sum()), note=note))
    t = pd.DataFrame(rows)
    t.to_csv(RESULTS / "stats_fifo_vs_lru.csv", index=False)
    show = pd.DataFrame({
        "Pattern": t.pattern.map(LABEL), "Mem %": t.mem_pct, "n": t.n,
        "FIFO": t.fifo.map("{:.4f}".format), "LRU": t.lru.map("{:.4f}".format),
        "LRU−FIFO": t.lru_minus_fifo.map("{:+.4f}".format),
        "LRU better / worse (seeds)": [f"{a} / {b}" if n > 1 else "–"
                                       for a, b, n in zip(t.seeds_lru_better, t.seeds_lru_worse, t.n)],
        "p (paired t)": [nt if nt and math.isnan(p) else ("<0.001" if p < 0.001 else f"{p:.3f}")
                         for nt, p in zip(t.note, t.p_value)],
    })
    (TABLES / "table2_fifo_vs_lru.md").write_text(md_table(show))
    return t


def table_ratio(s):
    rows = []
    for pat in ORDER:
        for mem in KEY_MEM:
            def m(pol):
                return s[(s.pattern == pat) & (s.policy == pol) & (s.mem_pct == mem)].iloc[0]["mean"]
            rows.append({"Pattern": LABEL[pat], "Mem %": mem,
                         "FIFO/OPT": m("FIFO") / m("OPT"), "LRU/OPT": m("LRU") / m("OPT")})
    (TABLES / "table3_ratio_to_opt.md").write_text(md_table(pd.DataFrame(rows), "{:.2f}"))


def table_policies(s):
    rows = []
    for pat in ORDER:
        r = {"Pattern": LABEL[pat]}
        for pol in ("FIFO", "LRU", "CLOCK", "RANDOM", "MRU", "OPT"):
            r[pol] = s[(s.pattern == pat) & (s.policy == pol) & (s.mem_pct == 50)].iloc[0]["mean"]
        rows.append(r)
    (TABLES / "table4_all_policies_50pct.md").write_text(md_table(pd.DataFrame(rows)))


def fig_main(s):
    fig, axes = grid(len(ORDER))
    for ax, pat in zip(axes, ORDER):
        for pol in ("FIFO", "LRU", "OPT"):
            g = s[(s.pattern == pat) & (s.policy == pol)].sort_values("mem_pct")
            ax.plot(g.mem_pct, g["mean"], DASH[pol], color=COL[pol], marker=MARK[pol], label=pol)
            if g.n.iloc[0] > 1:
                ax.fill_between(g.mem_pct, g["mean"] - g.ci95, g["mean"] + g.ci95,
                                color=COL[pol], alpha=0.18, linewidth=0)
        ax.set_title(LABEL[pat])
        ax.set_xlabel("memory (% of footprint)")
        if pat.startswith("matmul"):
            ax.set_yscale("log")
            ax.set_ylabel("fault rate (log)")
        else:
            ax.set_ylim(-0.02, 1.05)
            ax.set_ylabel("fault rate")
    h, l = axes[0].get_legend_handles_labels()
    axes[len(ORDER)].legend(h, l, loc="center", fontsize=8.5, title="policy")
    fig.suptitle("Fig 1. Page-fault rate vs memory size (95% CI bands where n = 10 seeds)",
                 x=0.01, ha="left", fontsize=9)
    fig.tight_layout()
    save_fig(fig, "fig1_fault_rate_vs_memory.png")


def fig_ratio(s):
    fig, axes = grid(len(ORDER))
    for ax, pat in zip(axes, ORDER):
        o = s[(s.pattern == pat) & (s.policy == "OPT")].sort_values("mem_pct")["mean"].to_numpy()
        for pol in ("FIFO", "LRU"):
            g = s[(s.pattern == pat) & (s.policy == pol)].sort_values("mem_pct")
            ax.plot(g.mem_pct, g["mean"].to_numpy() / o, DASH[pol], color=COL[pol],
                    marker=MARK[pol], label=pol)
        ax.axhline(1, color=COL["OPT"], lw=1.2)
        ax.set_yscale("log")
        ax.set_title(LABEL[pat])
        ax.set_xlabel("memory (% of footprint)")
        ax.set_ylabel("faults ÷ OPT (log)")
    h, l = axes[0].get_legend_handles_labels()
    axes[len(ORDER)].legend(h + [plt.Line2D([], [], color=COL["OPT"])], l + ["OPT (= 1)"],
                            loc="center", fontsize=8.5, title="policy")
    fig.suptitle("Fig 2. Distance above the OPT lower bound", x=0.01, ha="left", fontsize=9)
    fig.tight_layout()
    save_fig(fig, "fig2_ratio_to_opt.png")


def fig_policies(s):
    pats = ["sequential", "random", "shuffled", "bursty", "fwd_bwd"]
    fig, axes = grid(len(pats))
    for ax, pat in zip(axes, pats):
        for pol in ("FIFO", "LRU", "CLOCK", "RANDOM", "MRU", "OPT"):
            g = s[(s.pattern == pat) & (s.policy == pol)].sort_values("mem_pct")
            ax.plot(g.mem_pct, g["mean"], DASH[pol], color=COL[pol], marker=MARK[pol],
                    label=pol, lw=2.2 if pol in ("LRU", "OPT") else 1.5)
        ax.set_title(LABEL[pat])
        ax.set_xlabel("memory (% of footprint)")
        ax.set_ylabel("fault rate")
        ax.set_ylim(-0.02, 1.05)
    h, l = axes[0].get_legend_handles_labels()
    axes[len(pats)].legend(h, l, loc="center", fontsize=8.5, title="policy")
    fig.suptitle("Fig 3. Extra policies (MRU, RANDOM, CLOCK) used to test the mechanism",
                 x=0.01, ha="left", fontsize=9)
    fig.tight_layout()
    save_fig(fig, "fig3_extra_policies.png")


# ------------------------------------------------------------------------- reuse
def fig_reuse():
    h = pd.read_csv(RESULTS / "reuse_hist.csv")
    summ = pd.read_csv(RESULTS / "reuse_summary.csv").set_index("pattern")
    fig, axes = grid(len(ORDER))
    for ax, pat in zip(axes, ORDER):
        g = h[h.pattern == pat]
        ax.bar(g.bin_lo + 0.025, g.fraction, width=0.045, color=COL["FIFO"])
        cold0 = summ.loc[pat, "cold_refs"] / summ.loc[pat, "refs"]
        ax.set_title(f"{LABEL[pat]}  (cold {100 * cold0:.1f}%)")
        ax.set_xlabel("reuse distance ÷ footprint")
        ax.set_ylabel("share of reuses")
        ax.set_xlim(0, 1)
    axes[len(ORDER)].text(0.0, 0.5, "LRU hits a reference only if\nits reuse distance ≤ memory.\n"
                          "Mass at distance ≈ footprint\n(sequential, shuffled) means\nLRU misses until memory\n"
                          "≈ 100% of the footprint.", fontsize=7.5, color=INK2, va="center")
    fig.suptitle("Fig 4. LRU reuse-distance distributions (seed 0)", x=0.01, ha="left", fontsize=9)
    fig.tight_layout()
    save_fig(fig, "fig4_reuse_distance.png")


def table_reuse():
    c = pd.read_csv(RESULTS / "reuse_check.csv")
    ok = int(c.match.sum())
    s = pd.read_csv(RESULTS / "reuse_summary.csv")
    s["pattern"] = s.pattern.map(LABEL)
    s["cold %"] = 100 * s.cold_refs / s.refs
    t = s[["pattern", "footprint", "refs", "cold %", "median_distance_frac", "p90_distance_frac"]]
    t.columns = ["Pattern", "Footprint", "Refs", "Cold %", "Median dist ÷ footprint",
                 "P90 dist ÷ footprint"]
    (TABLES / "table6_reuse.md").write_text(
        md_table(t, "{:.3f}") + f"\nCross-check: LRU faults from distances = simulator LRU "
        f"at **{ok}/{len(c)}** (pattern, memory) points.\n")


# ------------------------------------------------------------------------ belady
def table_belady():
    r = pd.read_csv(RESULTS / "belady_random.csv")
    r.columns = ["String family", "Policy", "Strings", "With anomaly", "% with anomaly",
                 "Worst extra faults"]
    (TABLES / "table5a_belady_random.md").write_text(md_table(r, "{:.2f}"))
    m = pd.read_csv(RESULTS / "belady_ml.csv")
    m["pattern"] = m.pattern.map(LABEL)
    m.columns = ["Pattern", "Seed", "Footprint", "Frame counts checked",
                 "FIFO anomalies", "Worst extra faults"]
    (TABLES / "table5b_belady_ml.md").write_text(md_table(m, "{:.0f}"))


def fig_belady():
    r = pd.read_csv(RESULTS / "belady_random.csv")
    m = pd.read_csv(RESULTS / "belady_ml.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.6, 3.2), gridspec_kw={"width_ratios": [1, 1.6]})
    f = r[r.policy == "FIFO"]
    a.bar(range(len(f)), f.pct, color=COL["FIFO"], width=0.5)
    for i, v in enumerate(f.pct):
        a.text(i, v, f"{v:.2f}%", ha="center", va="bottom", fontsize=9, color=INK)
    a.set_xticks(range(len(f)))
    a.set_xticklabels(["uniform\nrandom", "noisy\ncyclic"])
    a.set_ylabel("% of 10,000 strings")
    a.set_title("Random strings (LRU, OPT: 0%)")
    g = m.groupby("pattern", sort=False).anomalies.sum()
    g = g.reindex(ORDER)
    b.bar(range(len(g)), g.values, color=COL["FIFO"], width=0.55)
    for i, v in enumerate(g.values):
        b.text(i, v, str(int(v)), ha="center", va="bottom", fontsize=9, color=INK)
    b.set_xticks(range(len(g)))
    b.set_xticklabels([LABEL[p].replace("Forward-backward", "Forward-\nbackward").replace(" ", "\n", 1)
                        for p in g.index], fontsize=6, rotation=0)
    b.set_ylabel("FIFO anomalies found\n(summed over seeds)")
    b.set_title("ML-shaped traces, every frame count")
    fig.suptitle("Fig 6. Belady's anomaly", x=0.01, ha="left", fontsize=9)
    fig.tight_layout()
    save_fig(fig, "fig6_belady.png")


# ------------------------------------------------------------------------ sweeps
def fig_sweeps():
    d = pd.read_csv(RESULTS / "raw_sweeps.csv")
    pc = ["#2a78d6", "#eb6834", "#1baf7a"]

    def diff_series(sub):
        piv = sub.pivot_table(index=["seed", "mem_pct"], columns="policy", values="fault_rate")
        dd = (piv["LRU"] - piv["FIFO"]).groupby("mem_pct").mean()
        return dd

    fig, axes = grid(5)
    for ax, pat in zip(axes[:3], ["sequential", "random", "shuffled"]):
        for c, v in zip(pc, (256, 512, 1024)):
            sub = d[(d["sweep"] == "footprint") & (d.pattern == pat) & (d.param_value == v)]
            dd = diff_series(sub)
            ax.plot(dd.index, dd.values, "-o", color=c, label=f"{v} pages")
        ax.axhline(0, color=INK2, lw=0.8)
        ax.set_title(f"{LABEL[pat]}: LRU − FIFO")
        ax.set_xlabel("memory (% of footprint)")
        ax.set_ylabel("fault-rate difference")
    ax = axes[3]
    for c, v in zip(pc, (24, 48, 96)):
        sub = d[(d["sweep"] == "hot_set") & (d.param_value == v)]
        dd = diff_series(sub)
        ax.plot(dd.index, dd.values, "-o", color=c, label=f"hot set {v}")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_title("Bursty: LRU − FIFO")
    ax.set_xlabel("memory (% of footprint)")
    ax.set_ylabel("fault-rate difference")
    ax = axes[4]
    for c, v in zip(pc, (8, 16, 32)):
        sub = d[(d["sweep"] == "tile") & (d.param_value == v) & (d.policy == "LRU")].sort_values("mem_pct")
        ax.plot(sub.mem_pct, sub.fault_rate, "-o", color=c, label=f"tile {v}×{v}")
    ax.set_yscale("log")
    ax.set_title("Tiled matmul: LRU fault rate")
    ax.set_xlabel("memory (% of footprint)")
    ax.set_ylabel("fault rate (log)")
    for a in (axes[0], axes[3], axes[4]):
        a.legend(loc="best")
    fig.suptitle("Fig 5. Sensitivity sweeps (mean over 10 seeds where stochastic)",
                 x=0.01, ha="left", fontsize=9)
    fig.tight_layout()
    save_fig(fig, "fig5_sensitivity.png")

    # table: LRU - FIFO at 50% memory across sweep values
    rows = []
    for sweep, pats in (("footprint", ["sequential", "random", "shuffled"]),
                        ("hot_set", ["bursty"])):
        for pat in pats:
            for v in sorted(d[(d["sweep"] == sweep) & (d.pattern == pat)].param_value.unique()):
                sub = d[(d["sweep"] == sweep) & (d.pattern == pat) & (d.param_value == v)]
                dd = diff_series(sub)
                o = sub[(sub.policy == "OPT") & (sub.mem_pct == 50)].fault_rate.mean()
                rows.append({"Sweep": sweep, "Pattern": LABEL[pat], "Value": v,
                             "LRU−FIFO @50%": dd.loc[50],
                             "LRU−FIFO @90%": dd.loc[90], "OPT @50%": o})
    for v in (8, 16, 32):
        sub = d[(d["sweep"] == "tile") & (d.param_value == v) & (d.mem_pct == 5)]
        rows.append({"Sweep": "tile", "Pattern": "Matmul (tiled), LRU @5%", "Value": v,
                     "LRU−FIFO @50%": float("nan"), "LRU−FIFO @90%": float("nan"),
                     "OPT @50%": sub[sub.policy == "LRU"].fault_rate.iloc[0]})
    t = pd.DataFrame(rows)
    t.columns = ["Sweep", "Pattern", "Value", "LRU−FIFO @50%", "LRU−FIFO @90%",
                 "OPT @50% (or LRU @5% for tile)"]
    (TABLES / "table7_sweeps.md").write_text(md_table(t))


# ------------------------------------------------------------------------ timing
def fig_timing():
    d = pd.read_csv(RESULTS / "raw_timing.csv")
    g = d.groupby(["policy", "draws"]).agg(
        refs=("refs", "first"), med=("seconds", "median"), lo=("seconds", "min"),
        hi=("seconds", "max"), us=("us_per_ref", "median")).reset_index()
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    for pol in ("FIFO", "LRU", "CLOCK", "OPT"):
        x = g[g.policy == pol].sort_values("refs")
        ax.errorbar(x.refs, x.med, yerr=[x.med - x.lo, x.hi - x.med], fmt=MARK[pol] + DASH[pol],
                    color=COL[pol], capsize=3, label=pol)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("references (after de-duplication)")
    ax.set_ylabel("simulation time, s (median, min–max of 5)")
    ax.set_title("Fig 7. Bookkeeping cost of the Python simulator\n(512 pages, 128 frames)")
    ax.legend()
    fig.tight_layout()
    save_fig(fig, "fig7_timing.png")
    t = g[["policy", "refs", "med", "lo", "hi", "us"]].copy()
    t["policy"] = pd.Categorical(t.policy, ["FIFO", "CLOCK", "LRU", "OPT"])
    t = t.sort_values(["refs", "policy"])
    t.columns = ["Policy", "Refs", "Median s", "Min s", "Max s", "µs / ref (median)"]
    (TABLES / "table8_timing.md").write_text(md_table(t, "{:.4f}"))


# ------------------------------------------------------------------------- knee
def fig_knee():
    k = pd.read_csv(RESULTS / "raw_knee.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.4))
    pred = {"matmul_naive": (69, "predicted 69 = 64 (B column) + 4 (A row) + 1 (C)"),
            "matmul_tiled": (18, "predicted 18 = 16 (B tile) + 1 (A) + 1 (C)")}
    for ax, pat in zip(axes, ("matmul_naive", "matmul_tiled")):
        for pol in ("FIFO", "LRU", "OPT"):
            g = k[(k.pattern == pat) & (k.policy == pol)].sort_values("frames")
            ax.plot(g.frames, g.fault_rate, DASH[pol], color=COL[pol], marker=MARK[pol], label=pol)
        ax.axvline(pred[pat][0], color=INK2, lw=1, ls=":",
                   label=f"predicted knee: {pred[pat][0]} frames")
        ax.set_yscale("log")
        ax.set_title(LABEL[pat])
        ax.set_xlabel("physical frames")
        ax.set_ylabel("fault rate (log)")
        ax.legend(loc="upper right")
    fig.suptitle("Fig 8. Memory-pressure knee: faults collapse once frames cover the working set",
                 x=0.01, ha="left", fontsize=9)
    fig.tight_layout()
    save_fig(fig, "fig8_knee.png")
    rows = []
    for pat in ("matmul_naive", "matmul_tiled"):
        for pol in ("FIFO", "LRU", "OPT"):
            g = k[(k.pattern == pat) & (k.policy == pol)].sort_values("frames")
            lo = g.fault_rate.iloc[0]
            # first frame count where the fault rate has fallen below a quarter of the plateau
            plateau = g[g.frames <= 16].fault_rate.max()
            hit = g[g.fault_rate < plateau / 4]
            rows.append({"Pattern": LABEL[pat], "Policy": pol,
                         "Frames at knee (rate < ¼ of small-memory plateau)": int(hit.frames.iloc[0]),
                         "Predicted": pred[pat][0]})
    (TABLES / "table9_knee.md").write_text(md_table(pd.DataFrame(rows), "{:.0f}"))


def table_env():
    e = json.loads((RESULTS / "environment.json").read_text())
    t = pd.DataFrame([("Programming language", f'Python {e["python"]} (Rust not used)'),
                      ("OS", e["os"]), ("CPU", e["cpu"]),
                      ("Logical cores", e["logical_cores"]), ("RAM (GB)", e["ram_gb"]),
                      ("numpy / scipy / matplotlib / pandas",
                       f'{e["numpy"]} / {e["scipy"]} / {e["matplotlib"]} / {e["pandas"]}'),
                      ("Dataset", "synthetic seeded reference strings (src/traces.py)"),
                      ("Run date", e["date"]), ("Code version", e["git_commit"]),
                      ("Repetitions", "10 seeds (stochastic); 5 timing reps")],
                     columns=["Parameter", "Value"])
    (TABLES / "table0_environment.md").write_text(md_table(t))


def main():
    d = load_main()
    s = summarise(d)
    table_main(s)
    stats_fifo_lru(d)
    table_ratio(s)
    table_policies(s)
    fig_main(s)
    fig_ratio(s)
    fig_policies(s)
    fig_reuse()
    table_reuse()
    table_belady()
    fig_belady()
    fig_sweeps()
    fig_timing()
    fig_knee()
    table_env()
    print("analysis complete:", sorted(p.name for p in TABLES.iterdir()))


if __name__ == "__main__":
    main()
