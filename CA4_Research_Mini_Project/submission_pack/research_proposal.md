# Research proposal (CA-4 template order)

**Title.** Thread or Process? When Is Thread-Based Execution More Efficient on Linux?
**Author:** Sreeharan, USN 25BTRCL257, course 25PCCS201 Operating Systems, topic R6. Date: (fill in)

## 1. Background
Linux creates threads and processes with `clone`; the difference is what is shared. A forked process copies the page tables, a thread shares the address space. CPython has a GIL, and a free-threaded build is supported since PEP 703/779.

## 2. Problem Statement
How do worker creation cost and memory decide whether threads or processes are the more efficient choice for tasks of different length, and how much does a worker pool remove?

## 3. Motivation
The same program may start one worker for an hour of work or ten thousand for a millisecond each. Programmers usually choose without numbers for their own runtime.

## 4. Literature Review
See `literature_matrix.md`: Baumann (fork cost grows with memory), Drepper and Molnar (NPTL), Sysel (creation comparison, including fork vs address-space size), Zhao et al. and Voegele et al. (fork cost), Ousterhout, von Behren, Pai, Welsh (threads vs events), Hoefler/Belli, Kalibera/Jones, Heiser (benchmarking method).

## 5. Research Gap
Existing comparisons measure creation of an empty worker in C, including its growth with the parent's address space (Sysel, Bendersky, Zhao et al.). I did not find one that adds task length, pools, worker memory and Python runtimes to the creation measurements on one machine.

## 6. Research Question
Primary: under what workloads is thread-based execution more efficient than process-based execution on Linux?
Secondary: (a) how does fork cost change with parent memory, and when does it stop mattering; (b) does the answer change between Rust, CPython with the GIL and free-threaded CPython?

## 7. Hypothesis
H1 thread creation at least 2x cheaper in every runtime. H2 fork cost grows with parent memory, thread creation does not. H3 worker-per-task is acceptable only for long tasks; pools make threads and processes alike. H4 idle thread needs far less memory, also when workers write shared data. H5 Rust threads = processes for CPU work; GIL threads do not scale; free-threaded threads do.

## 8. Objectives
1. Measure creation cost of thread, fork and fork+exec in Rust and Python, and how fork cost changes with parent memory (0 to 1,024 MiB).
2. Find the task length above which creating a worker per task costs under 10% of run time, and compare with a pool.
3. Compare CPU scaling (1 to 32 workers), memory per idle worker and cost of many waiting workers across Rust, CPython with GIL and free-threaded CPython.

## 9. Methodology
Independent: worker type, runtime, parent memory, task length, worker count. Dependent: time, speed-up, memory. Control: hardware, kernel, power plan, idle machine, fixed total work. Environmental: thermal state, background activity. Baseline: one worker / a thread / 0 MiB. 5 to 30 interleaved repetitions; 95% CI (t); Mann-Whitney U. Details in `experiment_config.md`.

## 10. Tools and Language
Rust 1.99 (rayon, tokio, libc), CPython 3.14.8 with and without GIL, Python (numpy, scipy, matplotlib) for analysis, Bash, Ubuntu 26.04.1 on WSL2 (language policy for R6: Python + Linux, Rust recommended).

## 11. Metrics
Create+join time (us), wall time per task (us), speed-up against one worker, PSS and page-table size per worker (KiB), time for C concurrent waiting workers (s), requests per second.

## 12. Expected Contribution
A measured decision guide: threads win when workers are started often or held in large numbers; a pool removes creation cost; processes are needed for isolation and for CPU scaling in GIL Python.
