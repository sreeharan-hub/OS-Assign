"""Draw all figures (with 95% confidence intervals) from results/*.json into figures/."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from analysis import (R, PG, PF, F_HEAP, F_CPU2, F_PARK, F_FORK_LIVE, F_POOL_IPC, F_TOPO, P_SYS,
                      ROOT, ci, keys, speedups, amdahl_fit, wall_per_task_us, overhead_fraction, W)

OUT = os.path.join(ROOT, "figures")
os.makedirs(OUT, exist_ok=True)
NAVY, THR, PRC, ASY, FT, GREY = "#1F3A5F", "#D9822B", "#2A9D8F", "#4C78A8", "#B8860B", "#8A8F98"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 150})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name), dpi=150)
    plt.close(fig)


def err(samples):
    m, h = ci(samples)
    return m, h


def bars(ax, labels, samples, colors, fmt="{:,.0f}", log=False):
    ms, hs = zip(*[err(s) for s in samples])
    b = ax.bar(labels, ms, yerr=hs, color=colors, capsize=3, error_kw={"lw": 1})
    if log:
        ax.set_yscale("log")
    top = max(m + h for m, h in zip(ms, hs))
    for r, m, h in zip(b, ms, hs):
        ax.text(r.get_x() + r.get_width() / 2, (m + h) * (1.15 if log else 1.0) + (0 if log else top * 0.015),
                fmt.format(m), ha="center", fontsize=8)
    ax.set_ylim(top=top * (5 if log else 1.15))
    return ms


# ---- Figure 1: concept ----
def fig1():
    fig, ax = plt.subplots(1, 2, figsize=(8.4, 3.0))
    for a in ax:
        a.set_xlim(0, 10); a.set_ylim(0, 6); a.axis("off")

    def box(a, x, y, w, h, t, fc, fs=8.5):
        a.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=fc, ec="none"))
        a.text(x + w / 2, y + h / 2, t, ha="center", va="center", color="white", fontsize=fs)

    a = ax[0]
    a.set_title("Threads: one process, shared address space", fontsize=9.5, color=NAVY)
    a.add_patch(FancyBboxPatch((0.3, 0.4), 9.4, 4.9, boxstyle="round,pad=0.05", fc="#EAF0F7", ec=NAVY))
    box(a, 0.8, 3.2, 8.4, 1.2, "code + heap + globals + open files (shared)", NAVY)
    for i in range(3):
        box(a, 0.8 + i * 2.9, 0.8, 2.5, 1.9, f"thread {i+1}\nown stack\n+ registers", THR)
    a = ax[1]
    a.set_title("Processes: separate address spaces", fontsize=9.5, color=NAVY)
    for i in range(3):
        x = 0.2 + i * 3.2
        a.add_patch(FancyBboxPatch((x, 0.4), 2.9, 4.9, boxstyle="round,pad=0.05", fc="#EAF0F7", ec=NAVY))
        box(a, x + 0.2, 3.2, 2.5, 1.2, "own memory\n(copy-on-write)", NAVY, 8)
        box(a, x + 0.2, 0.8, 2.5, 1.9, f"process {i+1}\nown stack\n+ registers", PRC)
    save(fig, "fig01_concept.png")


# ---- Figure 2: creation ----
def fig2():
    lab = ["Rust\nthread", "Rust\nfork", "Rust\nfork+exec", "Py\nthread", "Py\nos.fork", "Py mp\nfork", "Py mp\nforkserver", "Py mp\nspawn"]
    s = [R["create_us"]["thread"], R["create_us"]["fork"], R["create_us"]["fork_exec"],
         PG["create"]["thread"], PG["create"]["os.fork"], PG["create"]["mp_fork"],
         PG["create"]["mp_forkserver"], PG["create"]["mp_spawn"]]
    col = [THR, PRC, PRC, THR, PRC, PRC, PRC, PRC]
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    bars(ax, lab, s, col, log=True)
    ax.set_ylabel("time per create + join (µs, log)")
    save(fig, "fig02_creation.png")


# ---- Figure 3: fork and thread creation vs parent heap (both measured in the same run) ----
def fig3():
    fk, tk = F_HEAP["heap_fork_us"], F_HEAP["heap_thread_spawn_us"]
    ks = keys(fk)
    xs = [int(k) for k in ks]
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    for D, lab, col, mk in ((fk, "fork() (Rust)", PRC, "o-"), (tk, "thread spawn (Rust)", THR, "s-")):
        ms, hs = zip(*[err(D[k]) for k in ks])
        ax.errorbar(xs, ms, yerr=hs, fmt=mk, color=col, capsize=3, label=lab)
    ax.set_yscale("log")
    ax.set_xlabel("parent heap touched before creating the worker (MiB)")
    ax.set_ylabel("time per create + join (µs)")
    ax.legend()
    save(fig, "fig03_fork_heap.png")


# ---- Figure 4: CPU Rust ----
def fig4():
    fig, ax = plt.subplots(1, 2, figsize=(8.4, 3.4))
    for name, key, col, mk in (("threads", "cpu_threads_s", THR, "o-"), ("processes", "cpu_procs_s", PRC, "s--")):
        ws, sp, hw = speedups(R[key])
        ks = keys(R[key])
        m = [err(R[key][k])[0] for k in ks]
        ax[0].errorbar(ws, m, yerr=[err(R[key][k])[1] for k in ks], fmt=mk, color=col, capsize=2, label=name)
        ax[1].errorbar(ws, sp, yerr=hw, fmt=mk, color=col, capsize=2, label=name)
    ws = [int(k) for k in keys(R["cpu_threads_s"])]
    ax[1].plot(ws, ws, ":", color=GREY, label="ideal")
    ax[0].set_yscale("log")
    ax[0].set_xlabel("workers"); ax[0].set_ylabel("wall time for fixed work (s)"); ax[0].legend()
    ax[1].set_xlabel("workers"); ax[1].set_ylabel("speed-up vs 1 worker"); ax[1].legend()
    save(fig, "fig04_cpu_rust.png")


# ---- Figure 5: CPU Python (GIL, free-threaded, processes) ----
def fig5():
    fig, ax = plt.subplots(figsize=(6.6, 3.7))
    for lab, d, col, mk in (("threads, GIL build", PG["cpu"]["threads"], THR, "o-"),
                            ("threads, free-threaded 3.14t", PF["cpu"]["threads"] if PF else None, FT, "^-"),
                            ("processes (fork)", PG["cpu"]["procs"], PRC, "s--")):
        if d is None:
            continue
        ws, sp, hw = speedups(d)
        ax.errorbar(ws, sp, yerr=hw, fmt=mk, color=col, capsize=2, label=lab)
    ws = [int(k) for k in keys(PG["cpu"]["threads"])]
    ax.plot(ws, ws, ":", color=GREY, label="ideal")
    ax.set_xlabel("workers"); ax.set_ylabel("speed-up vs 1 worker"); ax.legend(fontsize=8)
    save(fig, "fig05_cpu_python.png")


# ---- Figure 6: I/O (Python) ----
def fig6():
    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    for lab, key, col, mk in (("threads", "threads", THR, "o-"), ("processes", "procs", PRC, "s--"), ("asyncio", "asyncio", ASY, "^-")):
        ks = keys(PG["io"][key])
        ax.errorbar([int(k) for k in ks], [err(PG["io"][key][k])[0] for k in ks],
                    yerr=[err(PG["io"][key][k])[1] for k in ks], fmt=mk, color=col, capsize=2, label=lab)
    ks = keys(PG["io"]["threads"])
    base = err(PG["io"]["threads"][ks[0]])[0]
    ax.plot([int(k) for k in ks], [base / int(k) for k in ks], ":", color=GREY, label="ideal")
    ax.set_xscale("log", base=2); ax.set_yscale("log")
    ax.set_xlabel("workers"); ax.set_ylabel("time for 240 blocking waits (s)"); ax.legend()
    save(fig, "fig06_io_python.png")


# ---- Figure 7: many concurrent sleepers (Rust) ----
def fig7():
    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    for lab, key, col, mk in (("threads", "sleepers_threads_s", THR, "o-"), ("processes", "sleepers_procs_s", PRC, "s--"),
                              ("Tokio tasks", "sleepers_tokio_s", ASY, "^-")):
        ks = keys(R[key])
        ax.errorbar([int(k) for k in ks], [err(R[key][k])[0] for k in ks], yerr=[err(R[key][k])[1] for k in ks],
                    fmt=mk, color=col, capsize=2, label=lab)
    ax.axhline(0.1, color=GREY, ls=":", label="ideal (100 ms)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("concurrent workers, each waiting 100 ms"); ax.set_ylabel("total wall time (s)"); ax.legend()
    save(fig, "fig07_sleepers.png")


# ---- Figure 8: memory ----
def fig8():
    lab = ["Rust\nthread", "Rust\nfork", "Py thread\n(GIL)", "Py thread\n(3.14t)", "Py\nfork", "Py\nspawn"]
    s = [R["mem_thread_pss_kib_each"]["100"], R["mem_proc_pss_kib_each"]["100"], PG["mem"]["thread_pss_kib_each"]["100"],
         (PF["mem"]["thread_pss_kib_each"]["100"] if PF else PG["mem"]["thread_pss_kib_each"]["100"]),
         PG["mem"]["fork_pss_kib_each"]["100"], PG["mem"]["spawn_pss_kib_each"]["50"]]
    col = [THR, PRC, THR, FT, PRC, PRC]
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    ms = [max(err(x)[0], 0.5) for x in s]
    b = ax.bar(lab, ms, color=col)
    ax.set_yscale("log")
    for r, m in zip(b, ms):
        ax.text(r.get_x() + r.get_width() / 2, m * 1.15, f"{m:,.1f}", ha="center", fontsize=8)
    ax.set_ylim(top=max(ms) * 5)
    ax.set_ylabel("extra PSS per idle worker (KiB, log)")
    save(fig, "fig08_memory.png")


# ---- Figure 9: copy-on-write ----
def fig9():
    s = R["shared64_total_pss_mib"]
    lab = ["threads\nread", "threads\nwrite", "processes\nread", "processes\nwrite"]
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    bars(ax, lab, [s["thread_read"], s["thread_write"], s["proc_read"], s["proc_write"]], [THR, THR, PRC, PRC])
    ax.set_ylabel("total PSS of 8 workers + parent (MiB)")
    save(fig, "fig09_cow.png")


# ---- Figure 10: ping-pong and pinning ----
def fig10():
    p = R["pingpong_us"]
    q = PG["pingpong"]
    fig, ax = plt.subplots(1, 2, figsize=(9.0, 3.5), sharey=False)
    x = np.arange(3)
    width = 0.25 if (F_PARK and "pingpong_park_us" in F_PARK) else 0.36
    ms_t, hs_t = zip(*[err(p[f"thread_{v}"]) for v in ("unpinned", "same_core", "diff_core")])
    ax[0].bar(x - width, ms_t, width, yerr=hs_t, color=THR, capsize=2, label="threads (mpsc channel)")
    if F_PARK and "pingpong_park_us" in F_PARK:
        pk = F_PARK["pingpong_park_us"]
        ms_pk, hs_pk = zip(*[err(pk[f"thread_{v}"]) for v in ("unpinned", "same_core", "diff_core")])
        ax[0].bar(x, ms_pk, width, yerr=hs_pk, color="#D4A373", capsize=2, label="threads (futex park)")
        ms_p, hs_p = zip(*[err(p[f"proc_{v}"]) for v in ("unpinned", "same_core", "diff_core")])
        ax[0].bar(x + width, ms_p, width, yerr=hs_p, color=PRC, capsize=2, label="processes (pipe)")
    else:
        ms_p, hs_p = zip(*[err(p[f"proc_{v}"]) for v in ("unpinned", "same_core", "diff_core")])
        ax[0].bar(x + width / 2, ms_p, width, yerr=hs_p, color=PRC, capsize=2, label="processes (pipe)")
    ax[0].set_xticks(x); ax[0].set_xticklabels(["unpinned", "same core", "different cores"])
    ax[0].set_title("Rust", fontsize=10); ax[0].set_ylabel("round trip (µs)"); ax[0].legend(fontsize=7.5)

    width_py = 0.36
    for i, (kind, col) in enumerate((("thread", THR), ("proc", PRC))):
        ms, hs = zip(*[err(q[f"{kind}_{v}"]) for v in ("unpinned", "same_core", "diff_core")])
        ax[1].bar(x + (i - 0.5) * width_py, ms, width_py, yerr=hs, color=col, capsize=2, label="threads" if kind == "thread" else "processes")
    ax[1].set_xticks(x); ax[1].set_xticklabels(["unpinned", "same core", "different cores"])
    ax[1].set_title("Python (GIL)", fontsize=10); ax[1].set_ylabel("round trip (µs)"); ax[1].legend(fontsize=8)
    save(fig, "fig10_pingpong.png")


# ---- Figure 11: switch cost vs working set ----
def fig11():
    ks = keys(R["switch_ws_thread_us"])
    xs = [int(k) / 1024 for k in ks]
    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    for lab, key, col, mk in (("threads (shared buffer)", "switch_ws_thread_us", THR, "o-"),
                              ("processes (private buffers)", "switch_ws_proc_us", PRC, "s--")):
        ax.errorbar([max(x, 4) for x in xs], [err(R[key][k])[0] for k in ks], yerr=[err(R[key][k])[1] for k in ks],
                    fmt=mk, color=col, capsize=2, label=lab)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("working set touched per message (KiB; 0 plotted at 4)")
    ax.set_ylabel("round trip on one core (µs)"); ax.legend()
    save(fig, "fig11_switch_ws.png")


# ---- Figure 12: wall time per task (Rust and Python) ----
def fig12():
    fig, ax = plt.subplots(1, 2, figsize=(9.2, 3.8))
    modes = (("per_thread", "thread per task", THR, "o-"), ("per_fork", "fork per task", PRC, "s-"),
             ("pool_threads", "thread pool", FT, "^--"), ("pool_procs", "process pool", "#1b6e63", "v--"),
             ("rayon", "Rayon", ASY, "D--"))
    for a, D, title, ms in ((ax[0], R, "Rust, 24 workers", modes), (ax[1], PG["pool"] if PG else None, "Python (GIL build), 24 workers", modes[:4])):
        tc = D["task_counts"]
        pref = "task_" if a is ax[0] else ""
        for key, lab, col, mk in ms:
            d = D[f"{pref}{key}_s"]
            ks = [k for k in keys(d) if int(k) > 0]
            a.plot([int(k) for k in ks], [wall_per_task_us(d[k], tc[k]) for k in ks], mk, color=col, label=lab)
        ks = [k for k in keys(tc) if int(k) > 0]
        a.plot([int(k) for k in ks], [int(k) / W for k in ks], ":", color=GREY, label="ideal (duration / 24)")
        a.set_xscale("log"); a.set_yscale("log")
        a.set_title(title, fontsize=10)
        a.set_xlabel("task duration (µs)")
    ax[0].set_ylabel("wall time per task (µs)")
    ax[0].legend(fontsize=7)
    save(fig, "fig12_pool_overhead.png")


# ---- Figure 13: break-even ----
def fig13():
    d = np.logspace(0, 6, 200)
    tm = ci(R["create_us"]["thread"])[0]
    fm = ci(R["create_us"]["fork"])[0]
    em = ci(R["create_us"]["fork_exec"])[0]
    pm_ = ci(PG["create"]["mp_fork"])[0]
    sp = ci(PG["create"]["mp_spawn"])[0]
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    for lab, c, col, ls in (("Rust thread", tm, THR, "-"), ("Rust fork", fm, PRC, "-"), ("Rust fork+exec", em, "#1b6e63", "-"),
                            ("Python mp fork", pm_, PRC, "--"), ("Python mp spawn", sp, "#1b6e63", "--")):
        ax.plot(d, 100 * overhead_fraction(c, d), ls, color=col, label=lab)
    ax.axhline(10, color=GREY, ls=":", lw=1)
    ax.text(1.2, 11.5, "10% overhead", color=GREY, fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("task duration (µs)")
    ax.set_ylabel("share of time spent creating the worker (%)")
    ax.legend(fontsize=8)
    save(fig, "fig13_breakeven.png")


# ---- Figure 14: TCP server models ----
def fig14():
    fig, ax = plt.subplots(1, 2, figsize=(9.0, 3.6))
    models = ["thread", "threadpool", "fork", "asyncio"]
    names = ["thread\nper conn", "thread\npool(32)", "fork\nper conn", "asyncio"]
    colors = [THR, FT, PRC, ASY]
    for a, cpu, title in ((ax[0], 0, "no CPU work per request"), (ax[1], 500, "0.5 ms CPU per request")):
        x = np.arange(4)
        for j, (D, off, lab) in enumerate(((PG, -0.2, "GIL build"), (PF, 0.2, "3.14t"))):
            if D is None:
                continue
            ms, hs = zip(*[err(D["tcp"][f"{m}_cpu{cpu}"]["req_per_s"]) for m in models])
            a.bar(x + off, ms, 0.4, yerr=hs, color=colors, alpha=0.95 if j == 0 else 0.55, capsize=2,
                  hatch="" if j == 0 else "//", label=lab)
        a.set_xticks(x); a.set_xticklabels(names, fontsize=8)
        a.set_title(title, fontsize=10); a.set_ylabel("requests / s")
        a.legend(fontsize=7)
    save(fig, "fig14_tcp.png")


if __name__ == "__main__":
    for f in (fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8, fig9, fig10, fig11, fig12, fig13, fig14):
        f()
        print(f.__name__, "ok")
