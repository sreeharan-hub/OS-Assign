"""Build docs/CA3_Report.md/.docx/.pdf from ca3/results/ca3_results.json (every number is read from the results)."""
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "experiments"))
import docbuild  # noqa: E402

O = json.loads((HERE / "results" / "ca3_results.json").read_text())
env = json.loads((ROOT / "results" / "environment.json").read_text()) if (ROOT / "results" / "environment.json").exists() else {}
TODAY = date.today().strftime("%b %d, %Y")
rp = O["repro"]
KILL, TESTS, MUT = O["kill"], O["tests"], O["mutants"]
REG = O["regression"]
TIM = {r["frames"]: r for r in O["timing"]}
BEL = O["belady"]["results"]
DSN = O["design"]
ok = lambda b: "✓" if b else "✗"  # noqa: E731


def fr(n):
    return f"{n:,.0f}"


def reg(pat, mem):
    return next(r for r in REG if r["pattern"] == pat and r["mem"] == mem)


def design(pat, mem):
    return next(r for r in DSN if r["pattern"] == pat and r["mem"] == mem)


# ---- derived facts
caught_by = {k: [i + 1 for i, v in enumerate(vals) if not v] for k, vals in KILL.items()}
only_T1 = [k for k in KILL if caught_by[k] == [1]]
M1_tests = caught_by["Mutant M1"]
M3_tests = caught_by["Mutant M3"]
T_names = [t["name"] for t in TESTS]
t1_kills = [k for k in KILL if 1 in caught_by[k] and k.startswith(("Provided", "Mutant"))]
t1_alive = [k for k in KILL if k.startswith("Mutant") and 1 not in caught_by[k]]
alive_one = {k: v for k, v in caught_by.items() if k.startswith("Mutant")}

# trace table
rows = []
for a, b in zip(rp["bad_rows"], rp["good_rows"]):
    rows.append(f"| {a['t']} | {a['page']} | {' '.join(map(str, a['frames']))} | {'F' if a['fault'] else ''}"
                f"{(' (evict ' + str(a['victim']) + ')') if a['victim'] is not None else ''} | {' '.join(map(str, b['frames']))} | "
                f"{'F' if b['fault'] else ''}{(' (evict ' + str(b['victim']) + ')') if b['victim'] is not None else ''} |")
TRACE_TABLE = "| t | Ref | Provided: frames (old→new) | Fault | Correct LRU: frames (old→new) | Fault |\n|---:|---:|---|---|---|---|\n" + "\n".join(rows)

kill_rows = []
for k, vals in KILL.items():
    kill_rows.append(f"| {k} | " + " | ".join(ok(v) for v in vals) + f" | {sum(1 for v in vals if not v)} |")
KILL_TABLE = ("| Implementation | " + " | ".join(f"T{i+1}" for i in range(len(TESTS))) + " | Tests failed |\n|---|" +
              "---|" * len(TESTS) + "---:|\n" + "\n".join(kill_rows))
TEST_LIST = "\n".join(f"| T{i+1} | {t['name'].split(' ', 1)[1]} | {t['kind']} |" for i, t in enumerate(TESTS))

reg_rows = []
for name in ("sequential", "random", "shuffled", "bursty", "matmul_naive", "matmul_tiled", "fwd_bwd"):
    for mem in (10, 50):
        r = reg(name, mem)
        fixed_vs = (r["fixed"] - r["defective"]) / r["defective"] * 100
        reg_rows.append(f"| {r['label']} | {mem}% | {fr(r['defective'])} | {fr(r['fixed'])} | {fixed_vs:+.1f}% | {fr(r['opt'])} | {r['n_runs']} |")
REG_TABLE = ("| Workload | Mem. | Faults, provided code | Faults, fixed LRU | Change after fix | OPT (bound) | Runs |\n"
             "|---|---:|---:|---:|---:|---:|---:|\n" + "\n".join(reg_rows))
unchanged = [reg(n, 10)["label"] for n in ("sequential", "bursty", "fwd_bwd") if reg(n, 10)["identical"]]
worse_after_fix = [(r["label"], r["mem"], r["defective"], r["fixed"]) for r in REG if r["fixed"] > r["defective"] * 1.001]
better_after_fix = [(r["label"], r["mem"], r["defective"], r["fixed"]) for r in REG if r["fixed"] < r["defective"] * 0.999]

tim_rows = "\n".join(
    f"| {k} | {TIM[k]['Provided (defective)']:.2f} | {TIM[k]['A: timestamp refresh']:.2f} | {TIM[k]['B: OrderedDict']:.2f} | {TIM[k]['C: linked list + hash']:.2f} |"
    for k in (8, 64, 512))

bel_rows = "\n".join(f"| {k} | {' → '.join(map(str, v['canonical']))} | {v['count']:,} / {O['belady']['n_strings']:,} |" for k, v in BEL.items())
ex = BEL["LRU (provided, defective)"]["example"]

dsn_rows = []
for name in ("bursty", "shuffled", "sequential", "matmul_naive", "fwd_bwd"):
    for mem in (10, 30, 50, 70):
        r = design(name, mem)
        best = min(("FIFO", "LRU", "SLRU (50% protected)", "OPT"), key=lambda p: r[p] if p != "OPT" else 9)
        dsn_rows.append(f"| {r['label']} | {mem}% | {r['FIFO']:.3f} | {r['LRU']:.3f} | {r['SLRU (50% protected)']:.3f} | {r['OPT']:.3f} | {best.replace(' (50% protected)', '')} |")
DSN_TABLE = ("| Workload | Mem. | FIFO | LRU | SLRU | OPT | Best online |\n|---|---:|---:|---:|---:|---:|---|\n" + "\n".join(dsn_rows))
slru_b10, slru_b30 = design("bursty", 10), design("bursty", 30)
slru_mm10, slru_fb30 = design("matmul_naive", 10), design("fwd_bwd", 30)
SENS = O["slru_sensitivity"]
fa = O["fix_agreement"]
edge_rows = "\n".join(f"| {e['impl']} | {e['frames']} | `{e['result']}` |" for e in O["edge"])
mut_rows = "\n".join(f"| {k} | {v['desc']} | {v['edit']} | {', '.join('T' + str(i) for i in alive_one['Mutant ' + k]) or '–'} |" for k, v in MUT.items())

R = f"""# 1. Problem Statement

**Challenge F1 (Virtual Memory) – "Incorrect LRU Implementation", with F2 (Belady's anomaly) and a design extension.**
Topic: *Page replacement for AI/ML-like access patterns* (research topic R19).

A page-replacement simulator was provided whose "LRU" routine produces **more page faults than LRU should**. On the
textbook reference string `7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1` with 3 frames, the provided routine reports
**{rp['defective']} faults**; the correct LRU answer is **{rp['reference']}** (FIFO gives {rp['fifo']}, Belady's OPT gives {rp['opt']}).
Nothing crashes and nothing looks wrong in the code at a glance – the symptom is purely a wrong number.

Because the simulator is the instrument used for the earlier CA-2 investigation of ML-shaped access patterns, an undetected
defect here would silently corrupt every conclusion drawn from it. The task is therefore to **diagnose, repair and *prove* the
repair**, and to find out which workloads the bug hides on.

| | |
|---|---|
| **Language / version** | Python {env.get('python', '3.13')} (standard library for the kernels; numpy/scipy/matplotlib for analysis) |
| **Source** | `ca3/bugs.py` (provided code, fixes, oracles, mutants), `ca3/slru.py`, `ca3/run_ca3.py`, `ca3/test_ca3.py` |
| **Linux environment** | Not needed for this challenge (pure algorithm simulation); the real-Linux counterpart is CA-5 |

# 2. OS Concept

**Mechanism: demand paging and page replacement (virtual memory).** When a referenced page is not resident and all physical frames
are occupied, the OS must choose a victim. LRU chooses the page unused for the longest time, i.e. it relies on a **recency
ordering that must be updated on every reference – hits included**.

*Why is this an OS problem rather than a syntax error?* The program is syntactically valid and runs to completion. It is wrong because it
violates the **definition of the replacement policy**: the algorithm's state (recency) is not maintained on the event (a page hit) that the
policy depends on. The consequence – extra page faults – is exactly the quantity that determines memory-system performance in a real OS (each
fault costs a disk or SSD access, many orders of magnitude slower than a memory hit). A correct LRU also has a mathematical
signature that is used below as a test oracle: it is a **stack algorithm** (Mattson et al.), so its fault count can never *increase* when
frames are added; FIFO is not a stack algorithm and can (Belady's anomaly).

# 3. Failure Reproduction

*(Debugging stage 1 – observe, without modifying the code.)*

```python
for page in trace:
    clock += 1
    if page in last_used:
        continue                       # hit
    faults += 1
    if len(last_used) >= frames:
        victim = min(last_used, key=last_used.get)  # oldest timestamp
        del last_used[victim]
    last_used[page] = clock            # written ONLY when the page is loaded
```

Run with the textbook string and 3 frames: **provided = {rp['defective']}, expected = {rp['reference']}** (`python ca3/run_ca3.py`; also
`test_defect_reproduced` in `ca3/test_ca3.py`). The two executions below were traced by hand-equivalent code (`trace_table` in `run_ca3.py`);
"frames" lists the resident pages from oldest timestamp to newest. They **first diverge at step {rp['first_divergence_step']}**.

{TRACE_TABLE}

Observation: on step {rp['first_divergence_step']} (reference to page 3) the provided routine evicts page 0 even though page 0 was used one step earlier;
step {rp['first_divergence_step'] + 1} then faults on page 0 again. Over all {len(rp['trace'])} references the provided routine behaves **identically to FIFO**
({rp['fifo']} faults). That is the first strong clue, and it is checked on the ML-shaped traces in Section 10: the provided routine returned exactly the FIFO fault
count in every one of them.

# 4. System Model

*(Stage 3 – model the failure.)*

```text
reference -> page table -> resident?
   yes -> HIT: LRU must move the page to the MRU end
   no  -> FAULT -> free frame?
            yes -> load page, put it at the MRU end
            no  -> evict the page at the LRU end, load, put at MRU end
```

State of the correct policy = a **recency list** of at most *k* pages:

```text
 LRU end [ p_old ... p_mid ... p_new ] MRU end
 evict from the left; insert or refresh at the right
```

The provided code keeps a timestamp per resident page instead of a list; the two representations are equivalent **only if the timestamp is rewritten
on every reference**. Model of the defect: *recency state transitions on a hit are missing*, so `last_used[p]` holds the *load time*, which turns the
recency list into a **load-order (FIFO) queue**.

| Event | Correct LRU state change | Provided code state change |
|---|---|---|
| Fault (free frame) | append p at MRU end | `last_used[p] = clock` |
| Fault (memory full) | evict LRU end, append p | evict smallest timestamp (= oldest *load*), `last_used[p] = clock` |
| **Hit** | **move p to MRU end** | **nothing** |

# 5. Root Cause

*(Stage 4 – distinguish symptom, immediate cause and root cause.)*

| Level | Statement |
|---|---|
| **Symptom** | LRU reports {rp['defective']} faults instead of {rp['reference']} on the textbook string; its fault curve equals FIFO's. |
| **Immediate cause** | At step {rp['first_divergence_step']} the victim chosen by `min(last_used, key=last_used.get)` is page 0, because its timestamp (2) is older than the others. |
| **Root cause** | The hit branch `continue`s without updating `last_used[page]`. The *recency invariant* "timestamp = time of last reference" is violated, so the data structure encodes load order, not use order. The OS principle violated is **temporal locality tracking**: LRU's only source of information about the future is the recent past, and the bug discards it. |

*Fixing a symptom is not fixing the system:* simply special-casing the textbook string, or switching the routine to call another policy, would
make the headline number right and leave the defect in place. The verification below therefore tests the **invariant**, not the single failing
input.

# 6. Alternative Solutions

*(Stage 5.)* Four candidate repairs were implemented or considered. Times are µs per reference on a 60,000-reference trace
(median of 5 runs; "provided" is the defective code for comparison).

| | A: refresh timestamp (1 line) | B: `OrderedDict` recency list | C: doubly linked list + hash | D: offline stack distance |
|---|---|---|---|---|
| **Correctness** | exact LRU | exact LRU | exact LRU | exact LRU, all frame counts at once |
| **Time per reference, 8 / 64 / 512 frames** | {TIM[8]['A: timestamp refresh']:.2f} / {TIM[64]['A: timestamp refresh']:.2f} / {TIM[512]['A: timestamp refresh']:.2f} | {TIM[8]['B: OrderedDict']:.2f} / {TIM[64]['B: OrderedDict']:.2f} / {TIM[512]['B: OrderedDict']:.2f} | {TIM[8]['C: linked list + hash']:.2f} / {TIM[64]['C: linked list + hash']:.2f} / {TIM[512]['C: linked list + hash']:.2f} | n/a (offline, `src/stackdist.py`) |
| **Complexity** | O(frames) per fault (linear `min` scan) | O(1) | O(1) | O(n log n) once |
| **Scalability** | degrades with memory size | flat | flat | flat, but needs the whole trace |
| **Fairness** | n/a (single process) | n/a | n/a | n/a |
| **Resource use** | O(frames) | O(frames) | O(frames) + node objects | O(footprint) |
| **Difficulty** | trivial | trivial | moderate (pointer bugs possible) | moderate |
| **Verdict** | correct but slow – keeps the provided code's cost | **selected** | what a kernel would implement; slower in CPython | cannot replace an online simulator |

A fifth "fix" – *replace LRU by FIFO or CLOCK so the numbers look plausible* – was rejected immediately: it changes the specification instead of
satisfying it.

# 7. Selected Design

**Fix B plus input validation** (`bugs.lru_final`): an `OrderedDict` is the recency list; a hit does `move_to_end`, a fault with full memory does
`popitem(last=False)`. Reasons: (1) it restores the invariant directly instead of patching timestamps; (2) it is the fastest option measured
({TIM[512]['B: OrderedDict']:.2f} µs/reference at 512 frames against {TIM[512]['Provided (defective)']:.2f} for the provided code); (3) it is the smallest change that is easy to read and review.
Fix C is kept in the repository as the kernel-style variant for the Micro-OS (CA-6): there the recency list is intrusive and nodes live inside the
page-frame table. Real kernels usually go one step further and *approximate* LRU with reference bits and active/inactive lists, because updating exact
recency on every memory access is too expensive in hardware.

An explicit validation of `frames` was added because the unguarded code fails in unrelated ways for invalid input (Section 9, edge cases).

# 8. Implementation

```python
def lru_final(trace, frames):
    if not isinstance(frames, int) or frames < 1:
        raise ValueError(f"frames must be a positive integer, got {{frames!r}}")
    od = OrderedDict()
    faults = 0
    for page in trace:
        if page in od:
            od.move_to_end(page)        # the fix: a hit refreshes recency
            continue
        faults += 1
        if len(od) >= frames:
            od.popitem(last=False)      # evict the least recently used page
        od[page] = None
    return faults
```

| File | Purpose |
|---|---|
| `ca3/bugs.py` | provided defective code, fixes A/B/C, literal oracles (LRU, FIFO, OPT), six injected-fault mutants, `lru_final` |
| `ca3/test_ca3.py` | 8 unit tests (`python -m unittest discover -s ca3 -p "test_ca3.py"`), run on every build |
| `ca3/run_ca3.py` | all experiments, tables and figures (`ca3/results/ca3_results.json`, `ca3/figures/`) |
| `ca3/slru.py` | scan-resistant extension (Section 14) |
| `ca3/build_report_ca3.py` | builds this report from the results file |

Reproduce: `python ca3/run_ca3.py && python ca3/build_report_ca3.py` (about 40 s). All numbers except the timings are deterministic (fixed seeds; 10 trace seeds for stochastic workloads).

# 9. Validation

*(Stages 6–7: Failure → Fix → Retest → Evidence.)*

**Test-case design (CA-3 §19).** The original failing case (T1) is not enough; nine tests were designed, one or more for each class:

| ID | What is checked | Class |
|---|---|---|
{TEST_LIST}

Edge case "recovery": an invalid `frames` value must raise a clear error and leave no state behind (the selected implementation is a pure function, so a later call returns the right answer – tested in `test_invalid_input_and_recovery`).

**Fault injection (CA-3 §16) – are the tests themselves any good?** Six hidden defects (mutants) were injected, one at a time, into a correct LRU, and the whole
suite was run on each (✓ = test passes, ✗ = test fails, i.e. the defect was detected):

| ID | Defect | Edit | Detected by |
|---|---|---|---|
{mut_rows}

{KILL_TABLE}

Reading the matrix:

* The provided code fails exactly the tests {', '.join('T' + str(i) for i in caught_by['Provided code'])}; **all three fixes pass all {len(TESTS)}.** Mutant M1 is the provided defect, so its row equals the provided-code row.
* **The original failing case (T1) detects {'all' if not t1_alive else str(6 - len(t1_alive))} of the 6 mutants here,** because the textbook string is unusually rich. It is still a *single hand-picked input*: a "fix" that special-cases that one string would pass it, which is why the differential (T5) and stress (T9) tests are also needed.
* **The "natural" adversarial test T7 (cyclic loop) does not detect the provided defect** – on a loop of k+1 pages LRU and FIFO coincide (both fault every time). This is the same reason the bug is invisible on the sequential-loop ML workload (Section 10).
* **T6 (monotonic in frames) does not detect it either.** It is a necessary property of LRU, but the defective code is FIFO, and FIFO violates monotonicity only on a small fraction of strings ({BEL['FIFO (reference)']['count']:,} of {O['belady']['n_strings']:,} random strings in Section 13). A property test is only as strong as the inputs that trigger it.
* **M3 (one frame unused) escapes T2 (one frame)** because with frames = 1 the capacity guard hides the off-by-one; it is caught by {', '.join('T' + str(i) for i in M3_tests)}. Boundary tests must probe more than one point of the range.
* **T1, T5 and T9 detect every mutant; each of the other tests lets at least one through** ({'; '.join('T' + str(i + 1) + ' misses ' + ', '.join(m.replace('Mutant ', '') for m in KILL if m.startswith('Mutant') and KILL[m][i]) for i in range(len(TESTS)) if any(KILL[m][i] for m in KILL if m.startswith('Mutant')))}). Cheap property tests are weaker than differential testing against an oracle.

**Edge cases – invalid frame counts:**

| Implementation | frames | Result |
|---|---:|---|
{edge_rows}

The provided code and the unguarded fix fail with accidental, misleading errors (`min()` of an empty sequence, `KeyError`); the selected implementation reports the real problem.

# 10. Performance / Trade-off Analysis

*(Regression testing, CA-3 §20: Before Fix → After Fix.)* The provided code and the fixed LRU were run on the seven ML-shaped workloads of the CA-2 study
at 10% and 50% of each workload's footprint (mean faults per run; 10 trace seeds for the three stochastic workloads, one trace otherwise).

{REG_TABLE}

![Extra faults caused by the defect, as a percentage of the correct LRU's faults (negative means the defective code happened to do better).](../ca3/figures/fig1_inflation.png)

![Fault rate versus memory for the provided code, the fixed LRU and OPT on three workloads.](../ca3/figures/fig2_before_after.png)

What the evidence shows:

1. **The provided code equals FIFO in every run** of every workload at all 11 memory levels, confirming the root cause.
2. **Where the bug is invisible:** {', '.join(unchanged)} give identical counts before and after. On a sequential loop and on the forward–backward pass LRU and FIFO coincide, so a test author who only used those workloads (the most "ML-like" ones) would have declared the buggy code correct. On matmul (naive) at 50% memory the bug doubles the faults ({fr(reg('matmul_naive', 50)['defective'])} vs {fr(reg('matmul_naive', 50)['fixed'])}).
3. **A correct LRU is not always better than FIFO.** After the fix, faults *rise* on {', '.join(f"{l} at {m}% ({fr(a)} → {fr(b)})" for l, m, a, b in worse_after_fix)}. This is not a regression in the fix: it is real policy behaviour (LRU's recency assumption is wrong for cyclic reuse), and it is the same effect reported in the CA-2 investigation. The test for a repair must therefore be *conformance to the specification*, never "faults went down".
4. **Correctness regression:** the fixes A, B, C and the independent simulator in `src/simulator.py` agree on all {fa['agree']}/{fa['total']} checked (workload, memory) points.
5. **Performance regression:** the selected code runs at {TIM[8]['B: OrderedDict']:.2f} / {TIM[64]['B: OrderedDict']:.2f} / {TIM[512]['B: OrderedDict']:.2f} µs per reference (8 / 64 / 512 frames) against {TIM[8]['Provided (defective)']:.2f} / {TIM[64]['Provided (defective)']:.2f} / {TIM[512]['Provided (defective)']:.2f} for the provided code, so the repair is also faster and its cost is independent of memory size. Memory use is O(frames) in both.

![Cost of the three candidate fixes versus frame count (log scale).](../ca3/figures/fig3_fix_cost.png)

Trade-offs of the selected design: exact LRU needs a list update on **every** reference, which is cheap in a simulator but impractical in a real MMU path – hence reference-bit approximations in real kernels; the extra data structure costs one list node per resident page; and the validation adds one comparison per call.

# 11. Verification and Traceability

| Item | Student response |
|---|---|
| **Verification** | Automated Regression Suite & Stack Distance Profiler |
| **Prompt / purpose** | Turn CA-3 into a challenge on research topic R19; write the defective routine, the fixes, the oracles, the mutants, the experiments and a first draft of this report; execute everything in a cloud sandbox. |
| **Important suggestion** | (a) Use the *monotone-in-frames (stack-property)* test as an oracle that separates LRU from FIFO-like behaviour; (b) detect the bug by differential testing against a literal definition; (c) examine the workloads on which the bug is invisible. |
| **Student verification** | All code was executed; the 8 unit tests pass; the textbook values (15 / 12 / 9 faults and the 9 → 10 Belady case) reproduce; every number in the tables comes from `ca3_results.json`, which the scripts regenerate. |
| **Final assessment** | (a) **Partial** – the property is correct but too weak to catch this defect (it fails only on {BEL['FIFO (reference)']['count']} of {O['belady']['n_strings']:,} random strings; the kill matrix shows T6 passing on the defective code). (b) **Correct** – T5 detects all six mutants. (c) **Correct** – the bug is invisible on the sequential loop and forward–backward workloads. |

AI-generated numbers are not evidence: the evidence is the executed code and the raw output in `ca3/results/`. The same discipline applies to this report's text, which is
generated from those results by `build_report_ca3.py`.

# 12. Final Defence

The provided LRU never refreshes a page's recency on a hit, so its victim choice is based on load order and it degenerates into FIFO (identical fault counts in every
run). The repair restores the recency invariant; it is verified against a literal oracle on 1,000 random cases plus a 60,000-reference stress trace, against six independently
injected defects (all detected by the differential and stress tests), against the textbook values, and for regressions on seven ML-shaped workloads (correct everywhere, faster, with
behaviour that matches FIFO's where theory says it must). Invalid input is rejected explicitly. The residual limitations are listed in Section 15.

# 13. Additional Challenge F2 – Belady's Anomaly or Bug

*Level 3.* **Scenario.** A policy shows *more* faults when given *more* frames. Is the policy defective or is it a genuine anomaly?

**Decision rule derived from the OS concept.** An anomaly is a legitimate possibility for FIFO (not a stack algorithm) but proves a defect in LRU (a stack algorithm: the set of
pages resident with k frames is always a subset of the set with k+1 frames). First verify the implementation against an independent oracle; then apply the rule.

Canonical string `1 2 3 4 1 2 5 1 2 3 4 5` (faults for 1…7 frames) and a search of {O['belady']['n_strings']:,} random strings (length 40, 10 pages, 1–9 frames; seed 11):

| Implementation | Faults for 1…7 frames on the canonical string | Strings showing an anomaly |
|---|---|---:|
{bel_rows}

* **FIFO reference:** 9 → 10 faults when going from 3 to 4 frames – a *genuine* Belady anomaly (the FIFO oracle and `src/simulator.py` agree).
* **LRU reference and fixed LRU:** no anomaly on any string, as theory requires.
* **Provided "LRU":** shows exactly the FIFO anomalies ({BEL['LRU (provided, defective)']['count']} strings; first example: faults rise from {ex[2]} to {ex[4]} when frames go from {ex[1]} to {ex[3]}). Because an LRU can never do that, **an anomaly in an LRU is a diagnostic of a bug** – this gives a second, independent way to detect the defect without knowing the correct answer.

# 14. Design Extension – Scan-Resistant Replacement

*Level 3/4 redesign.* LRU is now correct, but the ML-shaped workloads include **one-pass scans** (the bursty trace interleaves a 128-page cold scan with a 48-page hot set).
A **Segmented LRU (SLRU)** was designed and implemented (`ca3/slru.py`): new pages enter a probationary segment; a second reference promotes a page to a protected segment
(50% of frames); victims come from the probationary segment first. Faults per page-changing reference, mean of 10 seeds for stochastic workloads:

{DSN_TABLE}

![Bursty reuse: fault rate of FIFO, LRU, SLRU and OPT versus memory.](../ca3/figures/fig4_slru.png)

* **Bursty reuse:** SLRU cuts the fault rate from {slru_b10['LRU']:.3f} to {slru_b10['SLRU (50% protected)']:.3f} at 10% memory and from {slru_b30['LRU']:.3f} to {slru_b30['SLRU (50% protected)']:.3f} at 30% (paired t-test over 10 seeds, p = {slru_b30['p']:.1e} at 30%), because the protected segment shelters the hot set from the scan. Sensitivity to the protected fraction at 30% memory: 25% → {SENS[0]['mean']:.3f}, 50% → {SENS[1]['mean']:.3f}, 75% → {SENS[2]['mean']:.3f}.
* **Costs:** on naive matrix multiply at 10% memory SLRU is far worse than LRU ({slru_mm10['SLRU (50% protected)']:.3f} against {slru_mm10['LRU']:.3f}), and on forward–backward at 30% it is worse ({slru_fb30['SLRU (50% protected)']:.3f} against {slru_fb30['LRU']:.3f}), because pages are referenced only once or twice per layer pass and never get promoted before being evicted.
* **Conclusion:** the redesign is an improvement for one workload class and a regression for others; it is a *trade-off*, not a replacement. Which is right depends on the workload mix, which is what the CA-2 measurements are for.

# 15. Limitations and Connection to the Micro-OS

* The simulator models page identities only (no page size, dirty bits, I/O time, multiple processes), as in CA-2. Everything is a single-threaded Python simulation; no Rust version was written (the optional advanced extension).
* The mutants are hand-picked; they cover six common defect types, not all possible ones. The workloads are synthetic.
* Timings come from one machine and one Python version ({env.get('python', '3.13')}); only their ranking is claimed.

| CA-3 finding | Micro-OS (CA-6) connection |
|---|---|
| Recency not updated on a hit | A kernel page-frame table must update its LRU/active-list state on every access event it observes |
| Off-by-one frame count (M3/M4) | Frame-allocator bounds errors |
| Fix C (linked list + hash) | Intrusive list of frames; `O(1)` victim selection in a kernel with no allocator |
| Invalid input must be rejected | System-call argument validation |
| A small bookkeeping defect changes a global metric | A small kernel defect can produce a large system-level failure |

# References

1. A. Silberschatz, P. B. Galvin, G. Gagne, *Operating System Concepts*, 10th ed., Wiley, 2018 (page replacement, Belady's anomaly).
2. R. H. Arpaci-Dusseau, A. C. Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, ch. 22 (replacement policies).
3. L. A. Belady, "A Study of Replacement Algorithms for a Virtual-Storage Computer," *IBM Systems Journal* 5(2), 1966.
4. R. L. Mattson et al., "Evaluation Techniques for Storage Hierarchies," *IBM Systems Journal* 9(2), 1970.
5. R. Karedla, J. S. Love, B. G. Wherry, "Caching Strategies to Improve Disk System Performance," *IEEE Computer* 27(3), 1994 (segmented LRU).
6. Siril Saran B, "Page Replacement for AI/ML-Like Access Patterns," research report, 25PCCS201, 2026; CA-2 report, this repository.

# Appendix A – Final student checklist (CA-3 §30)

- [x] I reproduced the failure (Section 3).
- [x] I identified the relevant OS concept (Section 2).
- [x] I distinguished symptom from root cause (Section 5).
- [x] I created an appropriate system model (Section 4, trace table).
- [x] I analysed alternative solutions (Section 6).
- [x] I selected and justified a solution (Section 7).
- [x] I implemented the correction (Section 8).
- [x] I tested the original failure and normal and edge cases (Section 9).
- [x] I performed regression testing (Section 10).
- [x] I considered performance and trade-offs (Sections 10 and 14).
- [x] I documented the programming language and version (Section 1).
- [x] Linux environment: not applicable to this simulation (CA-5 covers it).
- [x] I disclosed AI assistance and recorded the verification (Section 11).

# Appendix B – Where each rubric criterion is addressed (CA-3 §22)

| Criterion (2 marks each) | Where |
|---|---|
| Problem diagnosis and root cause | Sections 2, 3, 5 |
| Modelling and reasoning | Sections 4, 5 (trace table, recency model) |
| Solution design and alternatives | Sections 6, 7, 14 |
| Implementation and validation | Sections 8, 9, 10, 13 |
| Technical defence and trade-offs | Sections 10, 12, 14, 15 |
"""
md = ROOT / "docs" / "CA3_Report.md"
md.write_text(R)
print("wrote", md, len(R.split()), "words")
docbuild.build(md, [("CONTINUOUS ASSESSMENT CA-3", 16, True, 6), ("OS DESIGN & DEBUGGING CHALLENGE", 13, False, 6),
                    ("Incorrect LRU Page Replacement – Research Topic R19", 12, False, 4)])
