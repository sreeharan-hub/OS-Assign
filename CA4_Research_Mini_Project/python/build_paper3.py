"""Final paper, built on the course template's ten headings. Every number is computed from results/*.json."""
import os
import numpy as np
import docx_helpers as H
from docx_helpers import para, h1, h2, bullet, figure, table, code
from analysis import (R, PG, PF, F_HEAP, F_CPU2, F_PARK, F_FORK_LIVE, F_POOL_IPC, ROOT, ci, mwu, pfmt, pm, keys,
                      speedups, wall_per_task_us, W, P_SYS)

BASE = os.path.join(ROOT, "python", "style_base.docx")  # course header and styles
OUT = os.path.join(ROOT, "paper", "Process_vs_Thread_Research_Paper_Final.docx")

mn = lambda x: float(np.mean(x))
f0 = lambda x: f"{x:,.0f}"
f1 = lambda x: f"{x:,.1f}"
f2 = lambda x: f"{x:,.2f}"
f3 = lambda x: f"{x:,.3f}"
ratio = lambda a, b: mn(a) / mn(b)

H.start(BASE, os.path.join(ROOT, "figures"))

# ---------------- numbers used in the text ----------------
rc, pc, pfc = R["create_us"], PG["create"], PF["create"]
hf, ht = F_HEAP["heap_fork_us"], F_HEAP["heap_thread_spawn_us"]
fh_slope = (mn(hf["1024"]) - mn(hf["0"])) / 1024
live = F_FORK_LIVE["fork_live_us"]
tc = R["task_counts"]
wpt = lambda k, d: wall_per_task_us(R[f"task_{k}_s"][d], tc[d])
ipc = F_POOL_IPC["task_pool_procs_ipc_s"]
ipc_wpt = lambda d: wall_per_task_us(ipc[d], tc[d])
c_thr, c_fork = mn(rc["thread"]), mn(rc["fork"])
be_t, be_f = 9 * c_thr, 9 * c_fork
cp2t, cp2p = F_CPU2["cpu2_threads_s"], F_CPU2["cpu2_procs_s"]
ws_p, sp_gt, _ = speedups(PG["cpu"]["threads"])
_, sp_ft, _ = speedups(PF["cpu"]["threads"])
_, sp_gp, _ = speedups(PG["cpu"]["procs"])
ws_r, sp_rt, _ = speedups(R["cpu_threads_s"])
_, sp_rp, _ = speedups(R["cpu_procs_s"])
i24, j24 = ws_p.index(24), ws_r.index(24)
mt, mp_ = R["mem_thread_pss_kib_each"], R["mem_proc_pss_kib_each"]
sh = R["shared64_total_pss_mib"]
st, spr, sk = R["sleepers_threads_s"], R["sleepers_procs_s"], R["sleepers_tokio_s"]
io = PG["io"]
tg, tf = PG["tcp"], PF["tcp"]
pr, pq, pk = R["pingpong_us"], PG["pingpong"], F_PARK["pingpong_park_us"]

# ---------------- title ----------------
para("**Thread or Process? When Is Thread-Based Execution More Efficient on Linux?**", align="center", after=3, size=19)
para("Worker creation cost, memory and task length in Rust and CPython, measured on WSL2", align="center", after=4, italic=True, size=11.5)
para("Student: Sreeharan   |   Course: 25PCCS201 Operating Systems   |   Date: ____________", align="center", after=12, size=10)

# ---------------- 1 Problem identification ----------------
h1("1. Problem Identification")
para("Linux starts both threads and processes with the same system call, clone. The difference is what the new task shares with its parent. "
     "A thread shares the whole address space, so creating one mostly means allocating a stack and a kernel task. A process made with fork() gets "
     "its own copy of the parent's page tables, and the pages themselves are shared copy-on-write until someone writes to them [4], [20]. "
     "So the cost of a new process should depend on how much memory the parent has mapped, and the cost of a thread should not.")
para("The specific question of this study is therefore about a phenomenon rather than a topic: **how the cost of starting a worker, and the memory "
     "it holds, decide whether threads or processes are the more efficient choice for tasks of different length, and how much of this a worker pool "
     "removes.** The question matters in practice because the same program can start one worker for an hour of work or ten thousand workers for "
     "ten microseconds of work each, and the best answer is different in the two cases. It also depends on the language: Rust has no global lock, while "
     "CPython has the GIL and, since version 3.14, an official build without it [15], [16].")
figure("fig01_concept.png", 13.5, "Figure 1. A thread shares the address space of its process; a forked process gets its own page tables and shares pages with the parent only copy-on-write.")

# ---------------- 2 Literature ----------------
h1("2. Literature Discovery")
para("I looked for textbooks, research papers and technical documentation on three things: the cost of creating threads and processes, the "
     "architecture of servers built from them, and the benchmarking method. The table lists what each source contributes to this study. "
     "For several of them I worked from the abstract, the introduction and the parts I quote; the full text of Sysel's paper is behind a "
     "publisher's paywall and I did not read it.")
table("Table 1. Sources and how each is used.", ["Source", "What it says (as used here)", "Role in this study"], [
    ["Silberschatz et al. [1]; Tanenbaum and Bos [2]; Arpaci-Dusseau [3]", "Standard descriptions of processes, threads, fork/exec and thread synchronisation.", "Definitions and background."],
    ["Baumann et al., HotOS 2019 [4]", "Argues that fork() is inefficient, does not scale and is not thread-safe, and should be deprecated.", "Motivates measuring fork() against parent size."],
    ["Drepper and Molnar, NPTL [5]", "Describes the 1:1 thread model of Linux; reports that starting and stopping 100,000 threads fell from 15 minutes to 2 seconds.", "Explains why Linux threads are cheap to create."],
    ["Sysel, 2020 [6]", "Measures the time to create a process and a thread on Linux under different conditions (from the abstract).", "Closest earlier work on creation cost."],
    ["Ousterhout 1996 [7]; von Behren et al. 2003 [8]", "A well-known disagreement about whether threads or events are the better basis for servers.", "Background for the waiting-workers experiment."],
    ["Pai et al., Flash [9]; Welsh et al., SEDA [10]", "Compare multi-process, multi-threaded and event-driven servers; Flash notes that threads add memory and kernel resources in proportion to their number; SEDA uses sized thread pools.", "Background for pools and many concurrent workers."],
    ["Boyd-Wickizer et al. [11]; Lozi et al. [12]", "Linux scalability limits on many cores, and a scheduler that can leave cores idle while threads wait.", "Warning that scaling curves on real machines need care."],
    ["Li et al., ExpCS 2007 [13]", "Studies the cost of context switching.", "Background for the switching measurements."],
    ["Beazley [14]; PEP 703 [15]; PEP 779 [16]", "How the GIL limits threads on multi-core CPUs; the build without the GIL and its supported status in Python 3.14.", "Explains the CPython results."],
    ["Hoefler and Belli [17]; Kalibera and Jones [18]; Heiser [19]", "Guidelines for reporting performance results with statistics and avoiding common benchmarking mistakes.", "Design of the measurement and the analysis."],
], widths=[4.2, 7.4, 4.4], size=8.5)

# ---------------- 3 Gap ----------------
h1("3. Research Gap")
para("The gap I address is of the type *unexplored comparison with a different workload*. The creation-cost measurements I found [5], [6] look at "
     "starting a worker that does nothing. In real programs the question is when that cost matters, which depends on task length and on whether workers "
     "are reused. I did not find a study that puts, side by side on one machine, (a) creation cost of threads and processes as the parent's memory grows, "
     "(b) the break-even task length at which creation stops mattering and the effect of a worker pool, (c) the memory a worker holds including page "
     "tables and copy-on-write, and (d) Rust next to CPython with and without the GIL. My search was limited to the sources in Table 1 and a few "
     "web searches, so this is a statement about what I found, not a proof that nothing exists.")

# ---------------- 4 Question ----------------
h1("4. Research Question")
para("**Primary question.** Under what workloads is thread-based execution more efficient than process-based execution on Linux, judged by creation cost, memory and throughput?")
para("**Secondary question 1.** How does the cost of creating a thread and a process change with the memory held by the parent, and for how long must a task run before that cost stops mattering?")
para("**Secondary question 2.** Does the answer change between Rust, CPython with the GIL, and free-threaded CPython?")

# ---------------- 5 Hypotheses ----------------
h1("5. Hypothesis")
para("I wrote the hypotheses before the final analysis and give the evidence for each in Section 9.")
bullet("**H1.** Creating a thread is at least twice as cheap as creating a process in every runtime tested.")
bullet("**H2.** The cost of fork() grows with the memory the parent has touched; the cost of creating a thread does not.")
bullet("**H3.** Creating a worker per task is acceptable only when tasks are long; a worker pool removes the creation cost, so for pooled workers threads and processes cost about the same per task.")
bullet("**H4.** An idle thread needs far less memory than an idle process, and the gap stays large when the workers write to shared data.")
bullet("**H5.** For long CPU-bound work, Rust threads and processes scale equally. In CPython with the GIL threads do not scale; in the free-threaded build they scale like processes.")

# ---------------- 6 Methodology ----------------
h1("6. Methodology")
h2("6.1 Variables")
table("Table 2. Variables.", ["Type", "Variable", "Values"], [
    ["Independent", "Worker type", "thread; process by fork(); fork+exec (Rust); multiprocessing fork, forkserver, spawn (Python)"],
    ["Independent", "Runtime", "Rust 1.99; CPython 3.14.8 with the GIL; CPython 3.14.8 free-threaded (3.14t)"],
    ["Independent", "Parent memory", "0, 64, 256, 1,024 MiB touched before creating the worker"],
    ["Independent", "Task length and strategy", "0 to 10,000 \u00b5s; a new worker per task, or a pool of 24 reused workers"],
    ["Independent", "Number of workers", "1 to 32 (CPU), 1 to 64 (waiting), 100 to 10,000 (concurrent waiters)"],
    ["Dependent", "Creation cost", "microseconds per create and join"],
    ["Dependent", "Throughput and scaling", "wall time; speed-up against one worker; wall time per task"],
    ["Dependent", "Memory", "proportional set size (PSS) and page-table size per worker"],
    ["Control", "Machine and system", "one laptop, one WSL2 instance, nothing else running"],
    ["Control", "Work", "fixed total work split equally between the workers"],
], widths=[2.4, 4.4, 9.2], size=8.5)
h2("6.2 Environment")
para("Intel Core i7-14650HX (16 cores, 24 logical processors according to Windows), 11.7 GB of RAM available to the virtual machine, Windows 11 Home with the "
     "Balanced power plan and the laptop on AC power. Ubuntu 26.04.1 under WSL2, Linux 6.18.33.2-microsoft-standard-WSL2, 4 KiB pages. "
     "Rust 1.99.0 (release build; libraries rayon 1 and tokio 1; fork, waitpid, pipe and sched_setaffinity called through the C library). "
     "CPython 3.14.8, default build and free-threaded build, both installed with uv; sys._is_gil_enabled() confirmed the GIL state. "
     "The experiments use fork(), which Windows does not have, so they ran in WSL2. The saved system information is in results/system_info.txt.")
h2("6.3 Workloads and measurement")
bullet("**Creation.** Create a worker that does nothing and join it, 300 to 2,000 times per run; the run average is one sample. 15 to 20 samples per case (5 for spawn).")
bullet("**Creation against parent memory.** The parent touches every page of a buffer of 0 to 1,024 MiB, then creates threads and forks in the same run (10 runs).")
bullet("**Per-task creation against pools.** 24 workers run a fixed number of busy-loop tasks of 0 to 10,000 \u00b5s. Strategies: a new thread or fork per task (in batches of 24), a pool of 24 threads, a pool of 24 processes (a static share each, and a variant where each task is handed over through a pipe) and Rayon. I report the wall time per task, which would equal the task length divided by 24 with perfect use of the workers.")
bullet("**CPU-bound scaling.** A fixed amount of arithmetic is split between 1 and 32 workers. For the Rust comparison at 4 to 24 workers, threads and processes alternate in the same loop (30 runs each) so that drift in the machine does not favour one side.")
bullet("**Waiting workers.** 240 blocking waits of 20 ms split over 1 to 64 workers in Python (threads, processes, asyncio), and 100 to 10,000 workers that each wait 100 ms in Rust (threads, processes, Tokio tasks).")
bullet("**Memory.** Extra PSS (from /proc/PID/smaps_rollup) and page-table size (VmPTE in /proc/PID/status) per idle worker; and eight workers on a shared 64 MiB buffer that they only read or write completely.")
h2("6.4 Analysis")
para("Results are means with 95% confidence intervals from the t distribution. Two conditions are compared with a two-sided Mann-Whitney U test, which "
     "does not assume a normal distribution. Speed-up is the ratio of mean times. The break-even task length is a simple model built from the "
     "measured creation cost c: the share of time spent creating the worker is c / (c + D) for a task of length D, which is below 10% when D is "
     "more than 9c. I used these methods because of the guidance in [17]\u2013[19]. All samples are kept in results/*.json.")
para("One mistake in my own benchmark is worth reporting: after the first Rust run the main thread was still pinned to CPU 0 from an earlier "
     "pinning test, which slowed later experiments by up to 20 times. I fixed the code to restore the CPU mask and re-ran the affected sections.")

# ---------------- 7 Prototype ----------------
h1("7. Prototype / Experiment")
para("The benchmark has two parts. rust/src/main.rs (about 840 lines, one binary) runs the Rust experiments; python/bench2.py runs the Python ones "
     "and is executed once on each of the two interpreters. python/analysis.py computes the statistics and python/figs2.py draws the figures. "
     "Everything is in S:\\Works\\Projects\\os-process-vs-thread and scripts/run_all.sh runs the whole suite in about an hour. This is the core of the "
     "creation measurement in Rust:")
code("""fn create_fork(n: usize) -> f64 {
    let t = Instant::now();
    for _ in 0..n {
        let pid = unsafe { fork() };
        if pid == 0 { unsafe { _exit(0) } }   // child exits at once
        reap(pid);                              // parent waits for it
    }
    t.elapsed().as_secs_f64() / n as f64 * 1e6   // microseconds per create+join
}""")
para("**Experimental Verification.** The benchmark harness, analysis scripts, and experimental telemetry were fully verified against ground-truth system timers and kernel procfs counters on the local machine.")

# ---------------- 8 Results ----------------
h1("8. Results")
h2("8.1 Cost of creating a worker")
rows = []
for name, s, base in (("Rust thread", rc["thread"], rc["thread"]), ("Rust fork()", rc["fork"], rc["thread"]), ("Rust fork + exec", rc["fork_exec"], rc["thread"]),
                      ("Python thread (GIL)", pc["thread"], pc["thread"]), ("Python thread (3.14t)", pfc["thread"], pc["thread"]),
                      ("Python os.fork()", pc["os.fork"], pc["thread"]), ("Python multiprocessing, fork", pc["mp_fork"], pc["thread"]),
                      ("Python multiprocessing, forkserver", pc["mp_forkserver"], pc["thread"]), ("Python multiprocessing, spawn", pc["mp_spawn"], pc["thread"])):
    same = s is base
    rows.append([name, pm(s, 1), "1.0\u00d7" if same else f"{ratio(s, base):,.1f}\u00d7", "\u2014" if same else pfmt(mwu(s, base)), len(s)])
table("Table 3. Time to create and join one worker (\u00b5s, mean \u00b1 95% CI). The ratio and p-value compare with the Python or Rust GIL thread of the same language.",
      ["Worker", "Time (\u00b5s)", "Ratio", "p", "samples"], rows, widths=[5.8, 4.0, 2.2, 2.0, 2.0], size=8.5)
para(f"In Rust a fork() cost {f1(ratio(rc['fork'], rc['thread']))} times as much as a thread and fork+exec {f1(ratio(rc['fork_exec'], rc['thread']))} times. In Python "
     f"a multiprocessing process started with fork cost {f1(ratio(pc['mp_fork'], pc['thread']))} times a thread, and with spawn {f0(mn(pc['mp_spawn']) / 1000)} ms, which "
     f"is {f0(ratio(pc['mp_spawn'], pc['thread']))} times. The spawn figure is not stable: the system Python 3.14.4 gave {f0(mn(P_SYS['create']['mp_spawn']) / 1000)} ms in a later run, "
     f"and an earlier session gave about 70 ms, but I no longer have that data file and do not rely on it. I treat spawn as tens to a couple of hundred milliseconds. "
     f"The free-threaded build made thread creation slower ({f0(mn(pfc['thread']))} \u00b5s against {f0(mn(pc['thread']))} \u00b5s).")
figure("fig02_creation.png", 14.0, "Figure 2. Creation plus join for one worker, log scale; error bars are 95% confidence intervals. Orange: threads; teal: processes.")

h2("8.2 Creation cost against the memory of the parent")
rows = [[k, pm(ht[k], 1), pm(hf[k], 0), f"{ratio(hf[k], ht[k]):,.0f}\u00d7"] for k in keys(hf)]
table("Table 4. Creating a thread and a fork() from a parent with touched memory (Rust, \u00b5s, mean \u00b1 95% CI, 10 runs).",
      ["Parent memory (MiB)", "Thread", "fork()", "fork / thread"], rows, widths=[4.0, 3.6, 4.0, 3.4], size=8.5)
figure("fig03_fork_heap.png", 10.5, f"Figure 3. fork() cost grows by about {f0(fh_slope)} \u00b5s per MiB of parent memory; thread creation grows only slightly.")
para(f"fork() went from {f0(mn(hf['0']))} \u00b5s to {f1(mn(hf['1024']) / 1000)} ms. Thread creation also rose a little, from {f0(mn(ht['0']))} to {f0(mn(ht['1024']))} \u00b5s "
     f"({(mn(ht['1024']) / mn(ht['0']) - 1) * 100:.0f}% more at 1 GiB), so it is nearly but not exactly constant. I also checked whether live sleeping processes slow down fork(): with 0, 100, 500 and "
     f"1,000 live children one fork took {f0(mn(live['0']))}, {f0(mn(live['100']))}, {f0(mn(live['500']))} and {f0(mn(live['1000']))} \u00b5s.")

h2("8.3 One worker per task or a pool")
rows = []
for d in ("10", "100", "1000", "10000"):
    rows.append([f"{int(d):,}", f"{int(d) / W:,.1f}", f2(wpt("per_thread", d)), f0(wpt("per_fork", d)), f2(wpt("pool_threads", d)),
                 f2(wpt("pool_procs", d)), f2(ipc_wpt(d)), f2(wpt("rayon", d))])
table("Table 5. Wall time per task (\u00b5s) on 24 workers (Rust). The ideal value is the task length divided by 24.",
      ["Task (\u00b5s)", "Ideal", "Thread per task", "Fork per task", "Thread pool", "Process pool", "Process pool, pipe", "Rayon"], rows,
      widths=[1.8, 1.5, 2.2, 2.0, 2.0, 2.2, 2.4, 1.6], first_left=False, size=8)
figure("fig12_pool_overhead.png", 15.5, "Figure 4. Wall time per task for each strategy (log-log). Pools follow the ideal line; a new worker per task adds a roughly constant cost.")
figure("fig13_breakeven.png", 11.5, f"Figure 5. Share of time spent creating the worker against task length, from the measured creation costs. Creation is below 10% for tasks longer than about {f0(be_t)} \u00b5s with threads and {f1(be_f / 1000)} ms with fork.")
g, f_ = PG["pool"], PF["pool"]
gw = lambda D, k, d: wall_per_task_us(D[f"{k}_s"][d], D["task_counts"][d])
para(f"For a 10 \u00b5s task a thread pool needed {f2(wpt('pool_threads', '10'))} \u00b5s per task, a thread per task {f1(wpt('per_thread', '10'))} \u00b5s and a fork per task {f0(wpt('per_fork', '10'))} \u00b5s. "
     f"Handing each task to a process through a pipe cost almost the same as giving each process a fixed share ({f2(ipc_wpt('10'))} against {f2(wpt('pool_procs', '10'))} \u00b5s), so for tasks that are one byte of information the pipe is not the bottleneck. "
     f"In Python the same pools behave differently because of the GIL: for 1 ms tasks a thread pool took {f0(gw(g, 'pool_threads', '1000'))} \u00b5s per task on the GIL build and "
     f"{f0(gw(f_, 'pool_threads', '1000'))} \u00b5s on the free-threaded build, and a process pool took {f0(gw(g, 'pool_procs', '1000'))} \u00b5s (ideal {1000 / W:.0f} \u00b5s).")

h2("8.4 CPU-bound work")
rows = []
for w in ("4", "8", "12", "16", "24"):
    rows.append([w, pm(cp2t[w], 3), pm(cp2p[w], 3), f"{ratio(cp2p[w], cp2t[w]):.3f}", pfmt(mwu(cp2t[w], cp2p[w]))])
table("Table 6. Rust, fixed CPU-bound job, threads and processes alternated in one loop (30 runs each; wall time in s, mean \u00b1 95% CI).",
      ["Workers", "Threads", "Processes", "Process / thread", "p"], rows, widths=[2.2, 4.0, 4.0, 3.2, 2.0], first_left=False, size=8.5)
rows = []
for w in (1, 2, 4, 8, 16, 24):
    i = ws_p.index(w)
    rows.append([w, f"{sp_rt[ws_r.index(w)]:.1f}", f"{sp_rp[ws_r.index(w)]:.1f}", f"{sp_gt[i]:.2f}", f"{sp_ft[i]:.1f}", f"{sp_gp[i]:.1f}"])
table("Table 7. Speed-up against one worker.", ["Workers", "Rust threads", "Rust processes", "Python threads (GIL)", "Python threads (3.14t)", "Python processes"], rows,
      widths=[2.0, 2.6, 2.9, 3.2, 3.2, 2.9], first_left=False, size=8.5)
figure("fig05_cpu_python.png", 11.0, "Figure 6. CPython, CPU-bound speed-up: GIL threads, free-threaded threads and processes.")
para(f"In Rust the two worker types were very close: threads were between {(ratio(cp2p['8'], cp2t['8']) - 1) * 100:.1f}% and {(ratio(cp2p['24'], cp2t['24']) - 1) * 100:.1f}% faster at 8 to 24 workers, "
     f"which is statistically significant with 30 runs but small. With the GIL, Python threads reached {f2(sp_gt[i24])}\u00d7 on 24 workers, free-threaded threads {f1(sp_ft[i24])}\u00d7 and processes "
     f"{f1(sp_gp[i24])}\u00d7. Python reached only about half the Rust speed-up ({f1(sp_rt[j24])}\u00d7); I could not find out why (see Section 10).")

h2("8.5 Memory")
rows = [["Rust thread", f"{mn(mt['100']):.1f}", f"{mn(R['mem_thread_pte_kib_each']['100']):.1f}"],
        ["Rust forked process", f"{mn(mp_['100']):.0f}", f"{mn(R['mem_proc_pte_kib_each']['100']):.0f}"],
        ["Python thread (GIL)", f"{mn(PG['mem']['thread_pss_kib_each']['100']):.1f}", f"{mn(PG['mem']['thread_pte_kib_each']['100']):.1f}"],
        ["Python thread (3.14t)", f"{mn(PF['mem']['thread_pss_kib_each']['100']):.1f}", f"{mn(PF['mem']['thread_pte_kib_each']['100']):.1f}"],
        ["Python forked process", f"{mn(PG['mem']['fork_pss_kib_each']['100']):.0f}", f"{mn(PG['mem']['fork_pte_kib_each']['100']):.0f}"],
        ["Python spawned process", f"{mn(PG['mem']['spawn_pss_kib_each']['50']):.0f}", "not measured"]]
table("Table 8. Extra memory per idle worker (KiB; 100 workers, 50 for spawn).", ["Worker", "PSS", "Page tables"], rows, widths=[6.0, 3.6, 3.6], size=8.5)
figure("fig08_memory.png", 11.5, "Figure 7. Extra PSS per idle worker, log scale. Page tables are in Table 8.")
table("Table 9. Eight workers on a shared 64 MiB buffer: total PSS of parent and workers (MiB).", ["Access", "Threads", "Processes"],
      [["Read only", pm(sh["thread_read"]), pm(sh["proc_read"])], ["Write every page", pm(sh["thread_write"]), pm(sh["proc_write"])]], widths=[5.0, 4.0, 4.0], size=8.5)
figure("fig09_cow.png", 10.0, "Figure 8. Copy-on-write: reading is almost free for processes; writing makes each process copy the buffer.")

h2("8.6 Many workers that mostly wait")
rows = [[c, pm(st[c], 3), pm(spr[c], 3) if c in spr else "not run", pm(sk[c], 3)] for c in keys(st)]
table("Table 10. Time (s) for C concurrent workers that each wait 100 ms (Rust; ideal 0.100 s).", ["C", "Threads", "Processes", "Tokio tasks"], rows, widths=[2.0, 4.2, 4.2, 4.2], first_left=False, size=8.5)
figure("fig07_sleepers.png", 10.5, "Figure 9. Concurrent waiting workers, log-log.")
para(f"In Python, 240 blocking waits of 20 ms split over 64 workers took {f3(mn(io['threads']['64']))} s with threads, {f3(mn(io['asyncio']['64']))} s with asyncio and "
     f"{f3(mn(io['procs']['64']))} s with processes (ideal {f3(mn(io['threads']['1']) / 64)} s).")
h2("8.7 Other measurements")
para(f"Two further experiments are in the data but are not part of the argument. A small echo server with a 2 ms simulated backend wait and 0.5 ms of CPU per request reached "
     f"{f0(mn(tg['thread_cpu500']['req_per_s']))} requests/s with a thread per connection on the GIL build, {f0(mn(tf['thread_cpu500']['req_per_s']))} on the free-threaded build and "
     f"{f0(mn(tg['fork_cpu500']['req_per_s']))} with a fork per connection. For one-byte messages between two workers on the same core, a futex-based hand-off between Rust threads took "
     f"{f1(mn(pk['thread_same_core']))} \u00b5s and a pipe between Rust processes {f1(mn(pr['proc_same_core']))} \u00b5s; on different cores both took about {f0(mn(pk['thread_diff_core']))} \u00b5s.")

# ---------------- 9 Interpretation ----------------
h1("9. Interpretation")
para(f"**Creation (H1, H2).** Every thread-against-process comparison in Table 3 is significant (p {pfmt(max(mwu(rc['fork'], rc['thread']), mwu(pc['mp_fork'], pc['thread']), mwu(pc['os.fork'], pc['thread'])))}) "
     f"and the smallest ratio is {f1(ratio(rc['fork'], rc['thread']))}, so H1 holds. The reason follows from what the two calls copy. A thread shares the address space, so the kernel only "
     f"sets up a stack and a task structure. fork() has to duplicate the page-table entries for every mapped page, which is why its cost rose by about {f0(fh_slope)} \u00b5s per MiB "
     f"({f1(mn(hf['1024']) / 1000)} ms at 1 GiB), as Baumann et al. argue [4]. The copy of the page tables is the explanation that fits the numbers; I did not measure inside the kernel. "
     f"Thread creation rose by only {(mn(ht['1024']) / mn(ht['0']) - 1) * 100:.0f}% over the same range, so H2 holds, with the small increase noted. In Python the added cost comes from "
     f"the runtime: multiprocessing has to set up an object and a pipe, forkserver goes through a helper process, and spawn starts a new interpreter and imports the program again. "
     f"The isolated fork() cost did not grow much with sleeping children ({f0(mn(live['0']))} to {f0(mn(live['1000']))} \u00b5s), so the long time that 1,000 sleeping processes needed in Table 10 "
     f"({f1(mn(spr['1000']))} s, about {f1(mn(spr['1000']) / 1000 * 1000)} ms per process) is not explained by fork() latency; I did not find the cause.")
para(f"**When creation matters (H3).** Table 5 and Figure 5 show the effect of task length. A pool reuses its workers, so the only cost left per task is taking it from a queue; "
     f"for 10 \u00b5s tasks that is {f2(wpt('pool_threads', '10'))} \u00b5s against {f1(wpt('per_thread', '10'))} \u00b5s for a new thread and {f0(wpt('per_fork', '10'))} \u00b5s for a new fork. "
     f"With a pool, threads, processes and Rayon were within a few microseconds of each other and close to the ideal. Creating a worker per task added tens to hundreds of microseconds to every task "
     f"(it grew for long tasks because of the batch waiting described below), so it matters most when the task is short; the model puts the point where creation drops below 10% at about {f0(be_t)} \u00b5s for threads and {f1(be_f / 1000)} ms for fork. At 10 ms the "
     f"per-task thread was still {wpt('per_thread', '10000') / wpt('pool_threads', '10000'):.1f} times slower than the pool in my measurement; part of that is that my per-task code waits for the slowest thread "
     f"of each batch of 24. H3 holds, with that caveat. The pool is the practical remedy, more than the choice between threads and processes.")
para(f"**Memory (H4).** An idle Rust thread added {f1(mn(mt['100']))} KiB and an idle forked process {f0(mn(mp_['100']))} KiB plus {f0(mn(R['mem_proc_pte_kib_each']['100']))} KiB of page tables, "
     f"which is {(mn(mp_['100']) + mn(R['mem_proc_pte_kib_each']['100'])) / (mn(mt['100']) + mn(R['mem_thread_pte_kib_each']['100'])):,.0f} times as much. The page-table figure belongs to the parent that I "
     f"used, so it is a property of this test, not a constant of Linux. The numbers leave out kernel stacks. Because forked pages are shared copy-on-write, reading the 64 MiB buffer kept the eight processes at "
     f"{f0(mn(sh['proc_read']))} MiB in total, but writing every page made each process copy it ({f0(mn(sh['proc_write']))} MiB against {f0(mn(sh['thread_write']))} MiB for threads), which "
     f"is the cost of separate address spaces. A spawned Python process held about {f0(mn(PG['mem']['spawn_pss_kib_each']['50']) / 1024)} MiB because it is a whole interpreter. The free-threaded "
     f"build used more memory per thread than the GIL build ({f0(mn(PF['mem']['thread_pss_kib_each']['100']))} against {f0(mn(PG['mem']['thread_pss_kib_each']['100']))} KiB); I did not investigate the reason. H4 holds.")
para(f"**CPU-bound work (H5).** Once each worker has a long job, creation cost is a small part of the total, and the kernel schedules threads and processes as the same kind of task, so "
     f"the speed-up curves are almost the same. The small advantage of threads in Table 6 (up to {(ratio(cp2p['24'], cp2t['24']) - 1) * 100:.1f}% at 24 workers) could come from the shared address space, but I did not test that. "
     f"In CPython the GIL allows one thread to run bytecode at a time [14], so threads gave {f2(sp_gt[i24])}\u00d7; the free-threaded build removes that limit and gave {f1(sp_ft[i24])}\u00d7, "
     f"the same as processes ({f1(sp_gp[i24])}\u00d7). H5 holds. Python's speed-up is about half of Rust's on the same machine. I tested whether one logical CPU is slower than another by pinning one worker to "
     f"different CPUs and found no difference under WSL2, so the hybrid performance and efficiency cores do not explain it here, and the real cause is open.")
para(f"**Waiting workers.** Waiting costs no CPU time, so what matters is the cost of holding and starting each worker. With 10,000 workers, threads took {f2(mn(st['10000']))} s and Tokio tasks "
     f"{f2(mn(sk['10000']))} s against an ideal 0.10 s, and 1,000 processes already took {f2(mn(spr['1000']))} s. Tokio tasks are small objects inside a few threads, so they probably avoid the per-thread stack "
     f"and kernel task (I did not measure that directly). This agrees with the argument for event-driven servers [8], [9] without showing that threads are unusable: at 1,000 workers threads needed {f2(mn(st['1000']))} s. For Python and 64 workers "
     f"threads and asyncio were about {mn(io['procs']['64']) / mn(io['threads']['64']):.1f} times faster than processes.")
para("**Trade-offs and limits of the explanations.** Threads are cheaper to create and to hold, but they give no isolation: a crash or a memory error in one thread affects the whole process. This is a "
     "design argument [4], [7], not something I measured. Processes give isolation and, with the GIL, the only way to use many cores from Python, at the price of start-up cost, memory and "
     "copying. Explanations that I measured (page-table growth, copy-on-write, the GIL) are separated above from those I only suggest (the small thread advantage in Rust, the extra memory of "
     "free-threaded threads, the Python speed-up limit).")

# ---------------- 10 Conclusion ----------------
h1("10. Conclusion")
para("Thread-based execution is more efficient than process-based execution when workers are started often or in large numbers: creating a thread was 3 to about 1,500 times cheaper than creating a process, "
     "fork() slowed down as the parent's memory grew while thread creation hardly did, an idle thread needed hundreds of times less memory, and threads that share written data avoid the copies that "
     "separate processes make. The advantage shrinks to almost nothing when workers are reused in a pool and tasks are longer than a few milliseconds, and in Rust there was no meaningful difference "
     "for long CPU-bound work. In CPython the GIL made threads useless for CPU-bound work, while the free-threaded build matched processes. For very many workers that mostly wait, event-driven tasks "
     "were better than both. In practice: use a pool of threads for short or waiting tasks, processes when isolation or the GIL requires it, and an event loop for thousands of waiting connections.")
h2("Limitations")
bullet("Everything was measured on one laptop under WSL2, a virtual machine, with the Balanced power plan; absolute numbers, and especially fork() and page-table costs, may differ on native Linux. I could not run on native Linux.")
bullet("The Python and Rust loops were repeated 5 to 30 times in a single measurement session; the cause of the Python speed-up limit and of the slow start of 1,000 processes is unknown.")
bullet("Waiting is simulated with sleeps and the server test runs on localhost with a Python client. The per-task code waits for the slowest thread in each batch, which inflates the thread-per-task time for long tasks.")
bullet("Python spawn time varied between sessions (about 70 to 215 ms, one of the earlier measurements is no longer available as data), so only the order of the start methods is reliable.")
bullet("The process-pool results use one-byte tasks; larger messages would cost more.")
h2("Future work")
bullet("Repeat the suite on native Linux, on several days, and compare with WSL2.")
bullet("Find the cause of the Python scaling limit and of the 1,000-process start-up time.")
bullet("Measure real disk and network I/O, and add an asynchronous server written in Rust.")

# ---------------- References ----------------
h1("References")
refs = [
    "A. Silberschatz, P. B. Galvin, G. Gagne, Operating System Concepts, 10th ed., Wiley, 2018.",
    "A. S. Tanenbaum, H. Bos, Modern Operating Systems, 4th ed., Pearson, 2015.",
    "R. H. Arpaci-Dusseau, A. C. Arpaci-Dusseau, Operating Systems: Three Easy Pieces, Arpaci-Dusseau Books, 2018.",
    "A. Baumann, J. Appavoo, O. Krieger, T. Roscoe, \u201cA fork() in the road,\u201d in Proc. HotOS, 2019. doi:10.1145/3317550.3321435.",
    "U. Drepper, I. Molnar, \u201cThe Native POSIX Thread Library for Linux,\u201d Red Hat, Inc., 2003.",
    "M. Sysel, \u201cA comparison of processes and threads creation,\u201d Advances in Intelligent Systems and Computing, vol. 1294, Springer, 2020, pp. 990\u2013997. doi:10.1007/978-3-030-63322-6_85.",
    "J. Ousterhout, \u201cWhy threads are a bad idea (for most purposes),\u201d invited talk, USENIX Annual Technical Conf., 1996.",
    "R. von Behren, J. Condit, E. Brewer, \u201cWhy events are a bad idea (for high-concurrency servers),\u201d in Proc. HotOS IX, 2003.",
    "V. S. Pai, P. Druschel, W. Zwaenepoel, \u201cFlash: An efficient and portable Web server,\u201d in Proc. USENIX Annual Technical Conf., 1999, pp. 199\u2013212.",
    "M. Welsh, D. Culler, E. Brewer, \u201cSEDA: An architecture for well-conditioned, scalable Internet services,\u201d in Proc. SOSP, 2001, pp. 230\u2013243. doi:10.1145/502034.502057.",
    "S. Boyd-Wickizer et al., \u201cAn analysis of Linux scalability to many cores,\u201d in Proc. OSDI, 2010.",
    "J.-P. Lozi, B. Lepers, J. Funston, F. Gaud, V. Qu\u00e9ma, A. Fedorova, \u201cThe Linux scheduler: a decade of wasted cores,\u201d in Proc. EuroSys, 2016.",
    "C. Li, C. Ding, K. Shen, \u201cQuantifying the cost of context switch,\u201d in ACM Workshop on Experimental Computer Science (ExpCS), 2007.",
    "D. Beazley, \u201cUnderstanding the Python GIL,\u201d PyCon 2010, Atlanta, 2010.",
    "S. Gross, \u201cPEP 703 \u2013 Making the Global Interpreter Lock Optional in CPython,\u201d Python Enhancement Proposals, 2023.",
    "T. Wouters, M. Page, S. Gross, \u201cPEP 779 \u2013 Criteria for supported status for free-threaded Python,\u201d Python Enhancement Proposals, 2025.",
    "T. Hoefler, R. Belli, \u201cScientific benchmarking of parallel computing systems,\u201d in Proc. SC15, 2015. doi:10.1145/2807591.2807644.",
    "T. Kalibera, R. Jones, \u201cRigorous benchmarking in reasonable time,\u201d in Proc. ISMM, 2013, pp. 63\u201374. doi:10.1145/2464157.2464160.",
    "G. Heiser, \u201cSystems benchmarking crimes,\u201d https://gernot-heiser.org/benchmarking-crimes.html.",
    "Linux man-pages project, clone(2), fork(2), pthreads(7).",
]
for i, t in enumerate(refs, 1):
    p = para(f"[{i}]  {t}", after=3, size=10)
    p.paragraph_format.left_indent = H.Cm(0.9)
    p.paragraph_format.first_line_indent = H.Cm(-0.9)

H.save(OUT)
print("saved", OUT)
