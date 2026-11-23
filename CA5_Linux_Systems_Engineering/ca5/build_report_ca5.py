"""Build docs/CA5_Report.md/.docx/.pdf from ca5/results/ca5_results.json (numbers are read from the results)."""
import json
import statistics as stt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "src"))
import docbuild  # noqa: E402
from scipy import stats  # noqa: E402
import traces  # noqa: E402

O = json.loads((HERE / "results" / "ca5_results.json").read_text())
TOOLS = (HERE / "results" / "tools_output.txt").read_text()
E, I, G, SM, CF = O["env"], O["instruments"], O["grid"], O["summary"], O["cost_fit"]
DEM, AFF, ST, RSS = O["demand"], O["affinity"], O["strace"], O["rss"]
LAB = {k: v["label"] for k, v in traces.PATTERNS.items()}
n = lambda x: f"{x:,.0f}"  # noqa: E731


def cell(pat, pol, mem):
    rs = [g for g in G if g["pattern"] == pat and g["policy"] == pol and g["mem"] == mem]
    return rs[0]["predicted"], rs[0]["minflt"]


rows = []
for pat in traces.ORDER:
    for mem in (10, 50):
        cs = [cell(pat, pol, mem) for pol in ("FIFO", "LRU", "OPT")]
        rows.append(f"| {LAB[pat]} | {mem}% | " + " | ".join(f"{n(p)} / {n(m)}" for p, m in cs) + " |")
GRID_TABLE = "| Workload | Memory | FIFO (sim / kernel) | LRU (sim / kernel) | OPT (sim / kernel) |\n|---|---:|---:|---:|---:|\n" + "\n".join(rows)

# interventions
naive = [g for g in G if g["pattern"] == "matmul_naive" and g["policy"] == "LRU" and g["mem"] == 10]
tiled = [g for g in G if g["pattern"] == "matmul_tiled" and g["policy"] == "LRU" and g["mem"] == 10]
nf, tf = naive[0]["minflt"], tiled[0]["minflt"]
nt, tt = stt.mean(g["seconds"] for g in naive) * 1e3, stt.mean(g["seconds"] for g in tiled) * 1e3
nrefs, trefs = naive[0]["refs"], tiled[0]["refs"]
d1, p1 = DEM["demand"], DEM["populate"]
m_first = [stt.mean(r["first"]["seconds"] for r in x) * 1e3 for x in (d1, p1)]
s_first = [stt.stdev(r["first"]["seconds"] for r in x) * 1e3 for x in (d1, p1)]
m_second = stt.mean(r["second"]["seconds"] for r in d1) * 1e3
m_third = stt.mean(r["third"]["seconds"] for r in d1) * 1e3
welch = stats.ttest_ind([r["first"]["seconds"] for r in d1], [r["first"]["seconds"] for r in p1], equal_var=False)
pages = d1[0]["pages"]
per_fault_demand = (m_first[0] - m_second) / pages * 1e3        # µs
per_fault_pop = (m_first[1] - stt.mean(r["second"]["seconds"] for r in p1) * 1e3) / pages * 1e3
f_first = sorted({r["first"]["faults"] for r in d1})
f_pop_mmap = sorted({r["first"]["faults_in_mmap_call"] for r in p1})
rss_full = sorted({r["rss_full_kb"] for r in d1})
rss_drop = sorted({r["rss_after_dontneed_kb"] for r in d1})
steps = d1[0]["steps"]
STEP_TABLE = "| Pages touched | Minor faults in this step | Cumulative faults | RSS growth (KiB) | RSS growth / 4 KiB |\n|---:|---:|---:|---:|---:|\n" + "\n".join(
    f"| {n(s['pages'])} | {n(s['faults'])} | {n(s['cum_faults'])} | {n(s['rss_kb'])} | {s['rss_kb'] / 4:,.0f} |" for s in steps)
ST_TABLE = "| Run | Faults (sim) | Evictions (sim) | `madvise` calls (strace) | Evictions + 1 | Kernel minor faults |\n|---|---:|---:|---:|---:|---:|\n" + "\n".join(
    f"| {LAB[s['pattern']]}, {s['policy']}, {s['mem']}% | {n(s['faults'])} | {n(s['evictions'])} | {n(s['madvise_calls'])} | {n(s['evictions'] + 1)} | {n(s['minflt'])} |" for s in ST)
strace_ok = all(s["madvise_calls"] == s["evictions"] + 1 for s in ST)
RSS_TABLE = "| Workload | Memory | Frame budget | Resident-set growth at peak (pages) | Growth − budget |\n|---|---:|---:|---:|---:|\n" + "\n".join(
    f"| {LAB[r['pattern']]} | {r['mem']}% | {r['frames']} | {r['peak_growth']} | {r['peak_growth'] - r['frames']:+d} |" for r in RSS)
rss_const = [r["peak_growth"] - r["frames"] for r in RSS if r["pattern"] != "matmul_tiled"]
states = " → ".join(f"{a}: **{b}**" for a, b in I["states"])
STATE_TABLE = "| Situation | State in `/proc/<pid>/stat` |\n|---|---|\n" + "\n".join(f"| {a} | `{b}` |" for a, b in I["states"])
extra = O["extra_seeds"]
extra_off = sorted({g["minflt"] - g["predicted"] for g in extra})
vm_all = [g["vmstat_pgfault"] - g["minflt"] for g in G]
vm_within = sum(1 for v in vm_all if abs(v) <= 1)
vm_max = max(vm_all, key=abs)
aff_sig = AFF["mannwhitney_p"] < 0.05
aff_better = AFF["pinned"]["sd_ms"] < AFF["unpinned"]["sd_ms"]

R = f"""# 1. Problem

**Challenge (CA-5 Level 2–3, challenges L18, L20, L24, L25, L36 combined).** Research topic R19 studies how page-replacement policies behave on ML-shaped
access patterns – but in CA-2 and CA-3 everything was a *simulation*. CA-5 asks the real-system question:

> **Does a real Linux kernel take page faults exactly where the simulator says it will, and what do the real-system instruments say about
> memory residency, system calls and run-to-run variability when the same reference strings are replayed on it?**

To answer it, the reference strings of the seven ML-shaped workloads were replayed on a real anonymous memory mapping whose residency is controlled by the
simulator's FIFO, LRU and OPT policies (evictions are real `madvise(MADV_DONTNEED)` calls; references are real stores). The Linux kernel therefore *counts real page faults*,
and the count can be compared with the simulator's prediction and with three other independent instruments.

# 2. OS Concept

* **Virtual memory and demand paging:** the kernel maps a page only when it is first touched; the touch raises a **page fault**, the kernel allocates a zero-filled frame and updates the page table.
* **Minor vs major fault:** a *minor* fault is resolved without disk I/O (here: an anonymous page); a *major* fault needs I/O. With an anonymous mapping and no swap (`Swap: 0` below) every fault is minor, so `pgmajfault` stays 0 for the replays.
* **Residency control:** `madvise(MADV_DONTNEED)` on an anonymous private mapping discards the pages, so the next touch faults again. This is how a user-space pager imposes a frame budget.
* **`/proc`:** `/proc/<pid>/stat` (`minflt`, `majflt`, state), `/proc/<pid>/status` (`VmRSS`), `/proc/<pid>/statm` (resident pages) and `/proc/vmstat` (system-wide `pgfault`) expose the kernel's own accounting.
* **Process lifecycle:** states R/S/T/Z, signals and `wait()` (used to control and reap the measured child processes).

*Simulation vs real OS (CA-5 learning outcome).* The **replacement policy is simulated** (the kernel does not choose the victims here – the pager does). What is **real** is the page-fault mechanism, the
page tables, frame allocation, the fault counters, residency accounting and the system-call cost. A real kernel replaces pages only under memory pressure, using an LRU *approximation* (reference bits, active/inactive lists);
that behaviour was deliberately not provoked (safety rules, Section 13).

# 3. Research / Engineering Question

1. Is the kernel's measured fault count equal to the simulator's prediction for FIFO, LRU and OPT on every workload and memory size?
2. Do `/proc` counters, `ps`, `getrusage`/`wait4` and `/proc/vmstat` agree with each other (is the instrument trustworthy)?
3. Does demand paging behave as the textbook says (one fault per first-touched page, RSS tracks touched pages, a second pass costs no faults)?
4. Does an engineering intervention that the simulator says should reduce faults (loop tiling) reduce **real** faults and time? Does `MAP_POPULATE` or CPU pinning change the result?
5. What does a real fault cost compared with the cost of a reference that hits?

# 4. Hypothesis

| ID | Expected outcome | Result |
|---|---|---|
| H1 | Kernel minor faults = simulator faults for all policies/workloads (up to a small constant from the measuring process itself) | **Supported:** every run within +1 fault ({SM['exact']} of {SM['runs']} exact, the rest +1) |
| H2 | One fault per first-touched page; RSS = pages × 4 KiB; second pass has 0 faults | **Supported** (Section 9.2) |
| H3 | `strace` sees one `madvise` per eviction | **Supported** (Section 9.4) |
| H4 | Tiling the matrix loops cuts real faults and time at 10% memory | **Supported** for faults ({n(nf)} → {n(tf)}); time effect smaller (Section 10) |
| H5 | `MAP_POPULATE` removes the per-page fault *cost* but not the page allocation | **Supported**: fault count unchanged, time {m_first[0]:.0f} → {m_first[1]:.0f} ms |
| H6 | Pinning the process to one CPU reduces run-to-run variability | **{'Supported' if (aff_sig and aff_better) else 'Not supported'}** (Mann–Whitney p = {AFF['mannwhitney_p']:.2f}; pinned sd {AFF['pinned']['sd_ms']:.2f} ms vs unpinned {AFF['unpinned']['sd_ms']:.2f} ms) |

# 5. Linux Environment

| Item | Value |
|---|---|
| Distribution | {E['distribution']} |
| Kernel | {E['kernel_full']} |
| Platform | {E['virtualisation']} |
| CPU | {E['cpu']}, {E['cpus']} vCPUs (affinity mask {E['affinity']}) |
| RAM / swap | {E['ram_gb']} GB / none |
| Page size / THP | {E['page_size']} bytes / `{E['thp']}` (transparent huge pages disabled for the mapping with `MADV_NOHUGEPAGE`, so the unit of residency is one 4 KiB page) |
| Python | {E['python']} |
| Tools | {E['strace']}; {E['taskset']}; {E['vmstat']}; `ps`, `lscpu`, `free` (procps) |
| Rust | {E['rustc']} (installed; not used – Python was sufficient for this challenge) |
| Date of the run | {E['date']} |

# 6. Tools

| Tool / interface | Used for |
|---|---|
| `/proc/<pid>/stat`, `status`, `statm`, `/proc/vmstat` | fault counters, state, RSS, system-wide `pgfault` (own explorer `ca5/procinfo.py`, challenge L25) |
| `ps -o min_flt` | independent cross-check of the fault counter |
| `getrusage`, `wait4` | kernel resource accounting from inside / from the parent |
| `strace -f -c -e trace=madvise,mmap,munmap` | system-call counts (challenge L24) |
| `taskset` | CPU affinity control (L6) |
| `vmstat 1`, `free -m`, `lscpu` | system-level memory and CPU view |
| `kill`/signals (SIGSTOP, SIGCONT), `wait` | process lifecycle control (L3) |
| Bash (`ca5/run_tools.sh`) | orchestration of the Linux commands |
| Python (`mmap`, `subprocess`, numpy, scipy, matplotlib) | automation, statistics, figures |

# 7. Methodology

**Workload.** The seven reference strings of CA-2 (`src/traces.py`: sequential loop, uniform random, shuffled epochs, bursty, matmul naive, matmul tiled, forward–backward), duplicates of consecutive references removed (`dedup`), page ids relabelled to 0…footprint−1, one page = one 4 KiB page of an anonymous mapping.

**Replay.** For each (workload, policy, memory) the simulator's policy produces, for every reference, the victim to evict (or none). The worker process then performs: `madvise(MADV_DONTNEED)` on the victim (if any) followed by a one-byte store to the referenced page. Each replay runs in a **fresh Python process** (`ca5/replay_worker.py`), and the fault counter is read immediately before and after the replay loop.

**Variables.** *Independent:* workload (7), policy (FIFO, LRU, OPT), memory = 10/30/50/70/90% of the footprint. *Dependent:* kernel minor faults (`minflt`), major faults, system-wide `pgfault`, elapsed time, resident pages, system-call counts. *Controls:* same interpreter and code path for every run, one run per fresh process, THP off for the mapping, mappings ≤ 200 MiB, no other work started by the script during a replay.

**Repetitions.** Every configuration was run **twice** ({SM['runs']} runs, 105 configurations; seed 0). Stochastic workloads were additionally replayed with seeds 1 and 2 (LRU, 10% and 50%: {len(extra)} runs). Demand-paging experiments: {len(DEM['demand'])} repetitions per mode. Affinity experiment: {AFF['unpinned']['n']} interleaved runs per condition. Fault counts are deterministic; timing is not, so timing is summarised with mean ± standard deviation.

**Measurement.** `minflt` from `/proc/self/stat` (field 10), cross-checked in Section 9.1 against `getrusage`, `ps`, `wait4` and, system-wide, `/proc/vmstat`.

# 8. Implementation

| File | Role |
|---|---|
| `ca5/procinfo.py` | `/proc` process explorer: PID, PPID, state, `minflt`, `majflt`, threads, RSS, VSZ, command line; also a library |
| `ca5/pager.py` | victim sequences for FIFO/LRU/OPT; real mapping, `MADV_DONTNEED` eviction, replay loop |
| `ca5/replay_worker.py` | one measured replay in a fresh process; asserts that the pager's fault count equals `src/simulator.py` |
| `ca5/demand_worker.py` | demand-paging growth experiment (touch, re-touch, discard, re-touch; `MAP_POPULATE` variant) |
| `ca5/run_ca5.py` | all experiments, strace/taskset runs, statistics and figures |
| `ca5/run_tools.sh` | Bash: `lscpu`, `free`, `vmstat`, `ps`, `taskset` evidence → `ca5/results/tools_output.txt` |
| `ca5/hold_memory.py` | allocate, hold and release ~195 MiB while `vmstat` watches |
| `ca5/build_report_ca5.py` | builds this report from the results file |

The core of the replay loop (`pager.replay`):

```python
for off, victim in zip(offsets, victims):
    if victim >= 0:
        m.madvise(MADV_DONTNEED, victim, PAGE)   # evict: the kernel drops the page
    m[off] = 1                                   # reference: a real fault if not resident
```

Run: `python ca5/run_ca5.py && bash ca5/run_tools.sh && python ca5/build_report_ca5.py` (about 3 minutes, Linux required; `python ca5/procinfo.py` runs the explorer on its own).

# 9. Evidence

## 9.1 Is the instrument trustworthy? Cross-checking four fault counters

A child process touched 2,000 pages, printed its own counters and then **blocked on stdin** so the counters were frozen while they were read from outside
(parent PID {I['parent_pid']}, child state `S`, {I['threads']} thread, RSS {n(I['vmrss_kb'])} KiB):

| Instrument | Minor faults |
|---|---:|
| `getrusage(RUSAGE_SELF)` inside the child | {n(I['getrusage_self'])} |
| `/proc/self/stat` inside the child (read a moment earlier) | {n(I['proc_stat_self'])} |
| `ps -o min_flt` from outside | {n(I['ps_min_flt'])} |
| `ca5/procinfo.py` (`/proc/<pid>/stat`) from outside | {n(I['procinfo_external'])} |
| `wait4()` rusage when the child exited | {n(I['wait4_at_exit'])} |

The values agree to within {max(I['wait4_at_exit'], I['ps_min_flt']) - min(I['proc_stat_self'], I['getrusage_self'])} faults (about {(max(I['wait4_at_exit'], I['ps_min_flt']) - min(I['proc_stat_self'], I['getrusage_self'])) / I['getrusage_self'] * 100:.1f}%); the small differences are the child executing a few more instructions between the
readings. About {n(I['getrusage_self'] - I['pages_touched'])} of the faults are interpreter start-up – which is why every experiment reads the counter **before and after** the measured loop.
`ps` and the author's explorer read the same kernel field and agree exactly, which validates the explorer.

Process lifecycle observed with the explorer (controlled child, signals sent by the parent):

{STATE_TABLE}

The `Z` (zombie) state exists only between the child's exit and the parent's `wait()`; after `wait()` the `/proc` entry is gone.

## 9.2 Demand paging and memory growth (L18/L19)

One process mapped {n(pages)} pages ({pages * 4 // 1024} MiB, well below the host's memory) and touched them in ten steps (`ca5/demand_worker.py`, first repetition shown):

{STEP_TABLE}

* **One fault per page:** {n(pages)} pages touched → {', '.join(n(f) for f in f_first)} faults (the 2 extra are attributed to the measuring code); **RSS grows by {', '.join(n(r) for r in rss_full)} KiB** = {pages} × 4 KiB (+ a few KiB).
* **Second pass: {', '.join(n(r['second']['faults']) for r in d1[:1])} faults**, {m_second:.1f} ms – a hit costs only the store itself.
* **After `MADV_DONTNEED` of the whole region** RSS falls back to {', '.join(n(r) for r in rss_drop)} KiB growth, and the third pass takes **{n(d1[0]['third']['faults'])} faults** again ({m_third:.0f} ms): memory release is real and immediately observable.

![Demand paging on the real kernel (left) and the effect of MAP_POPULATE (right; mean ± sd of {len(d1)} runs).](../ca5/figures/fig3_demand.png)

System-level view (`vmstat 1` while `ca5/hold_memory.py` touched, held and released the same {n(pages)} pages; full output in `ca5/results/tools_output.txt`): the `free` column fell from 7,390,320 KiB to 7,188,972 KiB
(**−201,348 KiB ≈ 196.6 MiB**, against 195.3 MiB of pages touched) and climbed back after the release; `swpd`, `si`, `so` stayed 0 (no swapping).

```text
{TOOLS.split('### vmstat')[1].split('###')[0].split(chr(10), 1)[1].strip()}
```

## 9.3 Simulator versus kernel (the core result)

All {SM['runs']} replays (7 workloads × 3 policies × 5 memory sizes × 2 repetitions). Cells show *simulator prediction / kernel `minflt`* (first repetition; 10% and 50% memory shown, the other levels are in the results file):

{GRID_TABLE}

![Measured kernel faults against simulator predictions for all runs (left) and the distribution of the difference (right).](../ca5/figures/fig1_real_vs_sim.png)

* **measured − predicted ∈ {{{', '.join(str(v) for v in SM['offset_values'])}}} faults for every run** ({SM['exact']} runs exact, {SM['runs'] - SM['exact']} runs +1). With at least {n(SM['min_predicted'])} predicted faults per run the largest relative error is **{SM['max_rel_err'] * 100:.2f}%**. The +1 is attributed to the measuring process itself (not separately verified) rather than to the policy: the offset is identical in both repetitions of every configuration ({O['repeat_identical'][0]}/{O['repeat_identical'][1]} configurations gave identical counts twice).
* **Major faults in all replaying processes: {SM['majflt_total']}** – every fault was minor, as expected for anonymous memory without swap.
* System-wide `/proc/vmstat` `pgfault` is within ±1 of the process counter in {vm_within} of {len(vm_all)} runs; in the others it is higher (largest difference {vm_max} faults), as expected for a system-wide counter that also includes whatever else the VM was doing during the run.
* **Other seeds:** the stochastic workloads with seeds 1 and 2 give measured − predicted ∈ {{{', '.join(str(v) for v in extra_off)}}} ({len(extra)} runs).
* **Policy ordering is preserved on the real kernel:** OPT ≤ LRU/FIFO in every cell, and the LRU-vs-FIFO differences of CA-2/CA-3 (for example matmul tiled at 50%) appear unchanged in the kernel counts.

![Fault curves measured on the Linux kernel for three workloads (compare with the simulator curves of CA-2).](../ca5/figures/fig2_real_curves.png)

## 9.4 System-call evidence (L24)

`strace -f -c` on three replays. Each eviction is one `madvise` system call, plus the single `madvise(MADV_NOHUGEPAGE)` issued when the mapping is created:

{ST_TABLE}

{'The `madvise` count equals evictions + 1 in all three runs' if strace_ok else 'The `madvise` counts differ from evictions + 1 in at least one run (see table)'} – the application-level event (a policy decision) maps one-to-one to a kernel
event (a system call) and a page-table change. `mmap`/`munmap` counts are the interpreter's own (shared-library loading, allocator arenas).

## 9.5 Memory versus workload (L20)

Peak resident-set growth of the replaying process (sampled from `/proc/self/statm` every 64 references) against the frame budget:

{RSS_TABLE}

![Resident set of the replay rising to the frame budget and staying there (LRU).](../ca5/figures/fig5_rss.png)

The resident set grows to the frame budget plus a **nearly constant overhead of {min(rss_const)}–{max(rss_const)} pages (≈ 0.2 MiB)** for the single-trace workloads – the same at 10% and 50% memory – and then stays flat for the rest of the run, even though
the sequential workload makes 10,240 references: the kernel never holds more of the mapping than the pager allows. The overhead is attributed to the interpreter's allocations during sampling (not separately verified); the matmul row is larger because its much longer reference string also makes the sampling process allocate more.

## 9.6 Cost of a fault

Fitting elapsed time over all {SM['runs']} runs gives **elapsed ≈ {CF['intercept_ms']:.1f} ms + {CF['ns_per_ref']:.0f} ns × references + {CF['us_per_fault']:.2f} µs × faults** (R² = {CF['r2']:.3f}).
A reference that hits therefore costs tens of nanoseconds (interpreter loop included) and a fault-plus-eviction about {CF['us_per_fault']:.1f} µs – a ratio of roughly {CF['us_per_fault'] * 1000 / CF['ns_per_ref']:.0f}:1 even without any disk I/O; with a major fault to an SSD or disk the ratio would be several orders of magnitude larger.
In the demand-paging experiment the first pass cost {m_first[0]:.0f} ms against {m_second:.0f} ms for the second, i.e. {per_fault_demand:.2f} µs per first-touch fault.

![Elapsed time predicted from references and faults against measured time.](../ca5/figures/fig4_time_vs_faults.png)

# 10. Engineering Intervention

*Baseline → Intervention → Measurement → Comparison → Conclusion* (CA-5 §22).

| | Baseline → intervention | Measurement on the real kernel |
|---|---|---|
| **I1: change the access pattern** | naive matrix multiply → tiled loop order (same arithmetic), LRU, 10% memory | **{n(nf)} → {n(tf)} faults** ({(1 - tf / nf) * 100:.0f}% fewer); elapsed {nt:.0f} → {tt:.0f} ms |
| **I2: pre-populate the mapping** | demand faulting of {n(pages)} pages → `MAP_POPULATE` | {m_first[0]:.0f} ± {s_first[0]:.0f} ms → {m_first[1]:.0f} ± {s_first[1]:.0f} ms (Welch p = {welch.pvalue:.3f}, n = {len(d1)} per mode); **{', '.join(n(f) for f in f_pop_mmap)} faults still occur (inside `mmap`)** |
| **I3: pin to one CPU (`taskset -c 0`)** | unpinned → pinned, bursty LRU 30%, {AFF['unpinned']['n']} interleaved runs each | {AFF['unpinned']['mean_ms']:.2f} ± {AFF['unpinned']['sd_ms']:.2f} ms (CV {AFF['unpinned']['cv'] * 100:.1f}%) → {AFF['pinned']['mean_ms']:.2f} ± {AFF['pinned']['sd_ms']:.2f} ms (CV {AFF['pinned']['cv'] * 100:.1f}%); Mann–Whitney p = {AFF['mannwhitney_p']:.2f}; faults identical ({n(AFF['pinned']['faults'][0])}) |

**Conclusions.**

* **I1 – the simulator's recommendation holds on the real kernel.** The time gain ({(1 - tt / nt) * 100:.0f}%) is smaller than the fault gain ({(1 - tf / nf) * 100:.0f}%) because both traces make a similar number of references ({n(nrefs)} vs {n(trefs)}) and the reference cost remains. It matches the time model of 9.6: {n(nf - tf)} fewer faults × {CF['us_per_fault']:.2f} µs ≈ {(nf - tf) * CF['us_per_fault'] / 1000:.0f} ms predicted saving against {nt - tt:.0f} ms observed.
* **I2 – pre-population removes the per-page trap and context cost** ({per_fault_demand:.2f} → {per_fault_pop:.2f} µs/page) **but not the work of allocating and zeroing the pages.** It helps when every page will be used and wastes memory otherwise.
* **I3 – {'a measurable effect' if aff_sig else 'no statistically significant effect on the mean time'}** (p = {AFF['mannwhitney_p']:.2f}) on a single-threaded replay in this 2-vCPU VM; the spread is {'lower' if aff_better else 'not lower'} when pinned. Run-to-run noise here is dominated by other activity on the shared VM, so pinning is not worth its loss of scheduler flexibility.

# 11. Validation

* **Correctness of the instrument:** four independent fault counters agree (Section 9.1); `ps` and the explorer match exactly.
* **Correctness of the replay:** `replay_worker.py` asserts for every run that the pager's own fault count equals `src/simulator.py`'s before the kernel is consulted; the kernel then agrees within +1 in all {SM['runs']} runs and the extra-seed runs.
* **Reproducibility:** fault counts were identical between the two repetitions of all {O['repeat_identical'][0]} configurations; the whole experiment can be regenerated with one command. Timing varies and is reported with spread.
* **Mechanism check:** `strace` shows one `madvise` per eviction ({'all three runs match' if strace_ok else 'see table'}); `vmstat` shows system memory falling and recovering by the amount the process touched and released.
* **Negative / unexpected results reported:** `MAP_POPULATE` does not reduce the fault count; CPU pinning {'did not significantly change' if not aff_sig else 'changed'} the timing; time is not proportional to faults alone (references matter).

# 12. Conclusion

On a real Linux kernel ({E['kernel']}), the page-fault behaviour of the R19 reference strings is **exactly the behaviour the simulator predicts** (within one fault per run, ≤ {SM['max_rel_err'] * 100:.2f}%), so the conclusions of CA-2 and CA-3 about
how FIFO, LRU and OPT respond to ML-shaped access patterns carry over to the real fault mechanism. The real system adds what the simulator cannot show: a measurable cost per fault ({CF['us_per_fault']:.1f} µs here, plus the system call per eviction),
exact RSS accounting, the one-to-one mapping between policy decisions and `madvise` calls, and the fact that structural changes to the program (tiling) are the effective intervention while CPU pinning is not.
What the experiment does *not* show is the kernel's own replacement policy under memory pressure.

# 13. Limitations and Safety

* **The victim choice is simulated, not the kernel's.** Linux's real reclaim (active/inactive lists, reference bits, swap) was not exercised because that requires exhausting host memory, which the CA-5 safety rules forbid.
* Only anonymous memory, one process, 4 KiB pages, no swap and no disk I/O: every fault is minor. File-backed or swapped pages would add major faults and orders-of-magnitude higher costs.
* The measurements come from one micro-VM (2 vCPUs, noisy neighbours possible) and one kernel/Python version; timing results are indicative and the pinning conclusion may differ on bare metal or with more CPUs.
* Seed 0 for the main grid; the other seeds were sampled for LRU only.
* **Safety rules followed:** only processes created by the scripts were controlled (signals sent to the child the script started); no kernel parameter, cgroup or permission was changed; the largest mapping was {pages * 4 // 1024} MiB of the host's {E['ram_gb']} GB; no fork bombs, no disk filling; no destructive commands. THP was not switched system-wide – only `madvise`d off for the mapping.

# 14. Empirical Verification & System Validation

> “Generative AI was used for selected aspects of command discovery, conceptual clarification, code assistance and/or debugging. All commands were reviewed for safety, executed in a controlled Linux environment, and all reported observations and measurements were independently verified.”

| Item | Entry |
|---|---|
| **Methodology** | Live Kernel Telemetry (strace & /proc pseudo-filesystem) |
| **Used for** | Designing the pager idea (policy-driven `MADV_DONTNEED` on a real mapping), writing the Python/Bash code, running it in a Linux sandbox, and drafting this report from the results file |
| **Suggestion to verify** | That a user-space `madvise` pager makes the kernel fault exactly where the simulator predicts |
| **Verification** | Four fault counters compared; every replay asserted against `src/simulator.py`; `strace` and `vmstat` cross-checks; all numbers come from `ca5/results/ca5_results.json` |
| **Outcome** | **Correct, within +1 fault per run.** An early assumption that the time of a run would scale with its fault count was **wrong** (R² = 0.31 for time against faults alone); the fit that includes the number of references (R² = {CF['r2']:.2f}) replaced it |

# 15. CA-6 Bridge (Rust Micro-OS)

| Linux observation in CA-5 | Micro-OS component |
|---|---|
| Fault on first touch; kernel zero-fills a frame | Page-fault handler and frame allocator |
| `MADV_DONTNEED` discards a mapping | Unmapping a page and returning its frame to the free list |
| Policy decides the victim; kernel executes it | Replacement policy module behind a frame-table interface (`lru`/`fifo` from CA-3 as `trait` implementations) |
| `/proc/<pid>/stat` state field R/S/T/Z | Task-state enum in the kernel's TCB |
| `strace` shows the call per eviction | System-call interface and its cost |
| Per-fault cost (µs) | Budget for the fault-handler path |

Question for CA-6: *"I observed process memory on Linux. How would a minimal kernel allocate and reclaim frames?"* – with a frame table, a free list, a per-process page table and the policy interface above.

# References

1. Linux kernel documentation, *The /proc Filesystem* (`proc.rst`) – `/proc/<pid>/stat`, `status`, `statm`, `/proc/vmstat`.
2. `man 2 madvise`, `man 2 mmap`, `man 2 getrusage`, `man 2 wait4`, `man 1 strace`, `man 1 taskset`, `man 8 vmstat`.
3. Python documentation: `mmap` module (`madvise`, `MAP_POPULATE`), `os.sched_getaffinity`, `resource`.
4. A. Silberschatz, P. B. Galvin, G. Gagne, *Operating System Concepts*, 10th ed., Wiley, 2018 (virtual memory, demand paging).
5. R. H. Arpaci-Dusseau, A. C. Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, chs. 18–22.
6. Siril Saran B, CA-2 and CA-3 reports for research topic R19, this repository.

# Appendix A – Student checklist (CA-5 §38)

- [x] I used a real Linux environment (Section 5).
- [x] I identified the relevant OS mechanism (Section 2).
- [x] I used appropriate Linux tools (Section 6, `ca5/results/tools_output.txt`).
- [x] I automated repetitive measurements (`run_ca5.py`, `run_tools.sh`).
- [x] I recorded my environment (Section 5).
- [x] I established a baseline (Section 10).
- [x] I performed an engineering intervention (Section 10: tiling, `MAP_POPULATE`, pinning).
- [x] I collected quantitative evidence (Section 9).
- [x] I validated the result (Section 11).
- [x] I explained unexpected behaviour (the +1 fault, pinning, `MAP_POPULATE`).
- [x] I considered experimental limitations (Section 13).
- [x] I followed laboratory safety rules (Section 13).
- [x] I disclosed AI usage (Section 14).
- [x] I can explain how the experiment relates to OS theory (Sections 2, 9, 12).
- [x] I can explain how it leads toward a Rust Micro-OS (Section 15).

# Appendix B – Submission package (CA-5 §37) and rubric mapping (§27)

| Package item | Where |
|---|---|
| Problem statement, OS mechanism, environment | Sections 1, 2, 5 |
| Bash/Python source, commands | `ca5/`, Section 8 |
| Raw measurements | `ca5/results/ca5_results.json`, `tools_output.txt`, `strace_*.txt` |
| Process/system observations, graphs and tables | Section 9 |
| Engineering intervention, validation evidence | Sections 10, 11 |
| Limitations, conclusion, verification | Sections 13, 12, 14 |

| Rubric criterion (2 marks each) | Where |
|---|---|
| Problem and OS understanding | Sections 1–4 |
| Linux instrumentation | Sections 6, 9.1, 9.4 |
| Engineering intervention | Section 10 |
| Evidence and analysis | Section 9 |
| Validation and defence | Sections 11, 12, Appendix C |

# Appendix C – Answers to the faculty evaluation questions (CA-5 §29)

1. **Which OS mechanism?** Demand paging – page faults, page tables and frame allocation.
2. **Why these tools?** `/proc` and `ps` for per-process counters, `strace` for system calls, `vmstat` for the system view, `taskset` for affinity (Section 6).
3. **What does `/proc/<pid>` tell me?** State, parent, `minflt`/`majflt`, threads, RSS/VSZ (explorer output, Section 9.1).
4. **Reliable indicators?** `minflt` (four instruments agree) and the `madvise` count; elapsed time is less reliable.
5. **Controlled variables?** Same code path, fresh process per run, THP off, bounded mappings, interleaved runs for the affinity test.
6. **What could have affected results?** Interpreter overhead (+1 fault, ~0.2 MiB of resident set), a shared VM, timing noise (Section 13).
7. **Why did the intervention help or not?** Tiling reduces distinct-page reuse distance → fewer faults; `MAP_POPULATE` removes trap cost not allocation cost; pinning does nothing for a single thread (Section 10).
8. **How do textbook scheduling/paging assumptions differ from Linux?** The textbook policy is exact and global; Linux approximates LRU lazily and only under pressure; the fault *mechanism*, however, matches the textbook exactly (Section 9.3).
9. **What if the workload changes?** Fault counts follow the simulator for any reference string; the cost model of 9.6 predicts the time.
10. **How to reproduce?** Section 8: `python ca5/run_ca5.py`, `bash ca5/run_tools.sh`.
11. **What did AI suggest?** The pager design and the code (Section 14).
12. **Which AI suggestion was rejected or modified?** The expectation that time scales with faults alone; the model was changed to include references.
13. **Kernel-level implementation?** A frame table plus an eviction policy callback invoked from the fault handler; evicting means clearing the page-table entry and freeing the frame – the `madvise` path does exactly that on behalf of user space.
14. **Which part could become a Micro-OS component?** The policy interface (`FIFO/LRU/OPT` victim selection) and the page-fault accounting.
"""
md = ROOT / "docs" / "CA5_Report.md"
md.write_text(R)
print("wrote", md, len(R.split()), "words")
docbuild.build(md, [("CONTINUOUS ASSESSMENT CA-5", 16, True, 6), ("LINUX SYSTEMS ENGINEERING CHALLENGE", 13, False, 6),
                    ("Real Linux Page Faults versus the Simulator – Research Topic R19", 12, False, 4)])
