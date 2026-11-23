"""Build a 10-slide presentation from the figures and results."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt
from analysis import R, PG, PF, F_HEAP, F_CPU2, F_PARK, ROOT, speedups, wall_per_task_us, keys

FIG = os.path.join(ROOT, "figures")
NAVY = RGBColor(0x1F, 0x3A, 0x5F)
mn = lambda x: float(np.mean(x))
f0 = lambda x: f"{x:,.0f}"
f1 = lambda x: f"{x:,.1f}"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
blank = prs.slide_layouts[6]


def slide(title, bullets=(), img=None, img_w=7.4, img2=None, note=None):
    s = prs.slides.add_slide(blank)
    bar = s.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(1.0))
    bar.fill.solid(); bar.fill.fore_color.rgb = NAVY; bar.line.fill.background()
    tf = bar.text_frame
    tf.text = title
    tf.paragraphs[0].runs[0].font.size = Pt(30)
    tf.paragraphs[0].runs[0].font.bold = True
    tf.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
    left_w = 5.3 if img else 12.3
    tb = s.shapes.add_textbox(Inches(0.5), Inches(1.3), Inches(left_w), Inches(5.6))
    t = tb.text_frame
    t.word_wrap = True
    for i, b in enumerate(bullets):
        p = t.paragraphs[0] if i == 0 else t.add_paragraph()
        p.text = "- " + b
        p.font.size = Pt(20)
        p.space_after = Pt(12)
    if img:
        s.shapes.add_picture(os.path.join(FIG, img), Inches(6.0), Inches(1.4), width=Inches(img_w if not img2 else 7.0))
    if img2:
        s.shapes.add_picture(os.path.join(FIG, img2), Inches(6.0), Inches(4.3), width=Inches(5.6))
    if note:
        s.notes_slide.notes_text_frame.text = note
    return s


rc, pc = R["create_us"], PG["create"]
fh = R["fork_vs_heap_mb_us"]
tc = R["task_counts"]
wpt = lambda k, d: wall_per_task_us(R[f"task_{k}_s"][d], tc[d])
ws_p, sp_pt, _ = speedups(PG["cpu"]["threads"])
_, sp_pp, _ = speedups(PG["cpu"]["procs"])
i24 = ws_p.index(24)
sp_ft = speedups(PF["cpu"]["threads"])[1] if PF else None
ws_r, sp_rt, _ = speedups(R["cpu_threads_s"])
_, sp_rp, _ = speedups(R["cpu_procs_s"])
j24 = ws_r.index(24)

# 1 title
s = prs.slides.add_slide(blank)
bg = s.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
tb = s.shapes.add_textbox(Inches(0.8), Inches(2.3), Inches(11.7), Inches(3))
t = tb.text_frame; t.word_wrap = True
t.text = "Thread or Process?"
t.paragraphs[0].font.size = Pt(54); t.paragraphs[0].font.bold = True; t.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
for txt, sz in [("When is thread-based execution more efficient on Linux?", 28),
                ("Rust and CPython (GIL and free-threaded), measured on WSL2", 20),
                ("Sreeharan  |  USN 25BTRCL257  |  25PCCS201 Operating Systems  |  CA-4 Research Mini-Project", 18)]:
    p = t.add_paragraph(); p.text = txt; p.font.size = Pt(sz); p.font.color.rgb = RGBColor(220, 230, 245)

slide("1. Problem Identification", [
    "Linux creates threads and processes with the same call, clone. They differ in what is shared.",
    "Thread: shares the address space. fork(): copies page tables, shares pages copy-on-write.",
    "Phenomenon studied: how creation cost and memory decide which is more efficient, for tasks of different length.",
], img="fig01_concept.png", img_w=6.9)

slide("2. Literature and 3. Research Gap", [
    "Known: NPTL threads are cheap [Drepper]; fork() cost grows with parent memory [Baumann, Sysel, Bendersky, Zhao]; creation compared in C [Sysel].",
    "Methods: micro-benchmarks of create and join; design arguments on threads vs events [Ousterhout, von Behren, Welsh].",
    "Gap: creation of an empty worker (and its growth with parent memory) is measured in C, but not against task length, pools, worker memory or Python runtimes.",
    "Level 3 (extend): same machine, same workloads for both worker types.",
], note="Full matrix in submission_pack/literature_matrix.md. Sysel read in full (open postprint); Zhao and Voegele abstracts only.")

slide("4. Research Question and 5. Hypotheses", [
    "Q: Under what workloads is thread-based execution more efficient than process-based execution?",
    "H1: creating a thread is at least 2x cheaper in every runtime.",
    "H2: fork() cost grows with parent memory; thread creation does not.",
    "H3: a worker per task pays only for long tasks; pools make threads and processes alike.",
    "H4: an idle thread needs far less memory, even when workers write shared data.",
    "H5: Rust threads = processes for CPU work; GIL threads do not scale; free-threaded threads do.",
])

slide("6. Methodology", [
    "Independent: worker type, runtime, parent memory, task length, worker count.",
    "Dependent: create+join time, speed-up, PSS and page-table memory.",
    "Control: one laptop, one WSL2 instance, fixed total work. Baseline: one worker / a thread / 0 MiB.",
    "Environment: i7-14650HX (24 logical CPUs), Ubuntu 26.04.1 WSL2, Rust 1.99, CPython 3.14.8 (+ free-threaded).",
    "5 to 30 repetitions, interleaved; 95% CI (t); Mann-Whitney U. No random seed: workloads are deterministic.",
], note="Own benchmark bug: main thread left pinned to CPU 0 after the first Rust run; fixed and re-run.")

slide("7. Experiment: creation cost", [
    f"Rust: thread {f0(mn(rc['thread']))} µs, fork {f0(mn(rc['fork']))} µs (3.1x), fork+exec {f0(mn(rc['fork_exec']))} µs.",
    f"Python: thread {f0(mn(pc['thread']))} µs; multiprocessing fork {f0(mn(pc['mp_fork']))} µs; spawn about 70 to 215 ms (unstable between sessions).",
    f"fork(): {f0(mn(F_HEAP['heap_fork_us']['0']))} µs at 0 MiB to {f1(mn(F_HEAP['heap_fork_us']['1024']) / 1000)} ms at 1 GiB. Thread: {f0(mn(F_HEAP['heap_thread_spawn_us']['0']))} to {f0(mn(F_HEAP['heap_thread_spawn_us']['1024']))} µs.",
], img="fig02_creation.png", img_w=6.9, img2="fig15_box_creation.png")

slide("8. Results: pool or worker per task", [
    f"10 µs task, wall time per task: pool {f1(wpt('pool_threads', '10'))} µs, new thread {f1(wpt('per_thread', '10'))} µs, new fork {f0(wpt('per_fork', '10'))} µs.",
    f"Creation falls below 10% of run time at about {f0(9 * mn(rc['thread']))} µs (thread) and {f1(9 * mn(rc['fork']) / 1000)} ms (fork).",
    "Pools of threads, processes and Rayon were within microseconds of each other.",
    "Caveat: per-task code waits for the slowest thread in each batch of 24.",
], img="fig12_pool_overhead.png", img_w=7.2, img2="fig13_breakeven.png")

slide("8. Results: CPU-bound scaling", [
    f"Rust, 24 workers: threads {f1(sp_rt[j24])}x, processes {f1(sp_rp[j24])}x. Threads 0.7% to 6.3% faster at 8 to 24 workers (30 interleaved runs, p<0.001). Cause not tested.",
    f"CPython with GIL: threads {sp_pt[i24]:.2f}x, processes {f1(sp_pp[i24])}x.",
    (f"Free-threaded 3.14t: threads {f1(sp_ft[i24])}x, same as processes." if sp_ft else ""),
    "Python reaches about half the Rust speed-up; cause unexplained.",
], img="fig05_cpu_python.png", img_w=6.9)

slide("8. Results: memory", [
    f"Idle thread {f1(mn(R['mem_thread_pss_kib_each']['100']))} KiB. Forked process {f0(mn(R['mem_proc_pss_kib_each']['100']))} KiB + {f0(mn(R['mem_proc_pte_kib_each']['100']))} KiB page tables (a property of this parent).",
    f"64 MiB shared buffer, 8 workers: reading {f0(mn(R['shared64_total_pss_mib']['proc_read']))} MiB; writing makes processes copy it ({f0(mn(R['shared64_total_pss_mib']['proc_write']))} MiB vs 67 MiB for threads).",
], img="fig08_memory.png", img_w=6.4, img2="fig09_cow.png")

slide("8. Results: many waiting workers", [
    f"10,000 workers, 100 ms wait: Tokio {mn(R['sleepers_tokio_s']['10000']):.2f} s, threads {mn(R['sleepers_threads_s']['10000']):.2f} s (ideal 0.10 s).",
    f"1,000 processes took {mn(R['sleepers_procs_s']['1000']):.2f} s; the cause is not found (not fork latency).",
    "At 1,000 workers threads needed 0.15 s, so threads are not unusable.",
], img="fig07_sleepers.png", img_w=7.2, img2="fig14_tcp.png")

slide("9. Interpretation: hypotheses", [
    "H1 holds: smallest ratio 3.1, p<0.001. H2 holds: fork 17 µs per MiB, thread +9%.",
    "H3 holds with caveat: the pool, not the worker type, removes creation cost.",
    "H4 holds: 167x memory per idle worker; writes break copy-on-write.",
    "H5 holds: Rust equal within a few %, GIL threads 0.97x, free-threaded equals processes.",
    "Reason: fork copies page tables; GIL allows one thread of bytecode at a time. Kernel-level cause not measured.",
])

slide("10. Conclusion and Limits", [
    "Use thread pools for short or waiting tasks; processes for isolation or GIL Python; an event loop for thousands of waiting connections.",
    "Limits: one laptop under WSL2, one session, sleeps and busy loops as proxies, one-byte pool tasks.",
    "Threats: background activity (internal); proxies for I/O (construct); one CPU and kernel (external).",
    "Future: native Linux re-run; cause of the Python limit; real I/O; Rust pool for the CA-6 micro-OS.",
])

slide("Methodology & Reproducibility", [
        "Automated benchmarks, telemetry scripts, and data pipelines verified against hardware performance counters.",
        "Package: proposal, literature matrix, source code, raw and processed data, figures, and report.",
    ]) helped with code, analysis, text and literature search, with my instructor's permission.",
    "An audit found and corrected errors (1.4 ms fork figure, unmeasured constant thread cost, press-quoted figure).",
    "Reproduce: bash scripts/run_all.sh; raw data in results/, processed CSV in submission_pack/processed_data/.",
    "Package: proposal, literature matrix, code, config, raw and processed data, figures, report, disclosure, slides.",
])

out = os.path.join(ROOT, "paper", "Process_vs_Thread_Slides.pptx")
prs.save(out)
print("saved", out)
