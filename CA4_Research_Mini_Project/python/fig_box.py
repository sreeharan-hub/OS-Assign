"""Box plot of the repeated creation-cost runs (CA-4: variability across repeated runs)."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(os.path.join(ROOT, "results", "rust_final.json"), encoding="utf-8"))
G = json.load(open(os.path.join(ROOT, "results", "py_gil.json"), encoding="utf-8"))

THREAD = "#f6c89f"    # light orange: threads
PROCESS = "#a9d9d0"   # light teal: processes
EDGE = "#4a4a4a"
MU = "µs"

panels = [
    ("Rust (20 runs)", [R["create_us"][k] for k in ("thread", "fork", "fork_exec")],
     ["thread", "fork", "fork+exec"], False),
    ("CPython 3.14 with GIL (5 to 15 runs)", [G["create"][k] for k in ("thread", "os.fork", "mp_fork", "mp_forkserver", "mp_spawn")],
     ["thread", "os.fork", "mp fork", "mp forkserver", "mp spawn"], True),
]

fig, axes = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={"width_ratios": [3, 5], "wspace": 0.22})
for ax, (title, data, labels, logy) in zip(axes, panels):
    bp = ax.boxplot(data, tick_labels=labels, showmeans=True, patch_artist=True, widths=0.55,
                    medianprops=dict(color="#333333", linewidth=1.4),
                    whiskerprops=dict(color=EDGE), capprops=dict(color=EDGE),
                    boxprops=dict(color=EDGE, linewidth=1.0),
                    flierprops=dict(marker="o", markerfacecolor="none", markeredgecolor=EDGE, markersize=5),
                    meanprops=dict(marker="^", markerfacecolor="#e07b39", markeredgecolor=EDGE, markersize=6))
    for i, box in enumerate(bp["boxes"]):
        box.set_facecolor(THREAD if i == 0 else PROCESS)
    if logy:
        ax.set_yscale("log")
    ax.set_title(title, fontsize=11, pad=8)
    ax.set_ylabel(f"create + join ({MU}{', log scale' if logy else ''})", fontsize=10)
    ax.grid(axis="y", color="#dddddd", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", labelsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
fig.text(0.5, 0.01, "orange box = thread, teal = process; triangle = mean, line = median, circle = outlier",
         ha="center", fontsize=8.5, color="#555555")
fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.17)
out = os.path.join(ROOT, "figures", "fig15_box_creation.png")
fig.savefig(out, dpi=200)
print(out)
