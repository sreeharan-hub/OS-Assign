# Viva preparation (CA-4 question list, answered from the data)

Answers are pointers to evidence; put them in your own words before the viva.

| Question | Where the answer is |
|---|---|
| Why this problem? | Paper Sec. 1: same program may start 1 worker or 10,000; choice made without numbers |
| What is the gap? | Sec. 3: earlier work measures empty-worker creation only |
| Most influential paper? | Baumann et al. (fork cost grows with memory) -> H2; Drepper and Molnar -> why threads are cheap |
| Independent / dependent variables? | Table 2 (worker type, runtime, parent memory, task length, workers / time, speed-up, memory) |
| Why these metrics and workloads? | Create+join time = cost to start; busy loop = CPU-bound; sleep = waiting; PSS = real memory share |
| What would invalidate the hypotheses? | Paper Sec. 5, "Conditions that would reject a hypothesis" |
| Why did results occur? | Sec. 9: threads share address space; fork copies page tables (about 17 us per MiB); GIL blocks bytecode parallelism |
| Alternative explanations? | Sec. 9 last paragraph; thread edge in Rust (0.7% to 6.3%) untested; Python 8x limit unexplained |
| Limitations? | Sec. 10: one laptop, WSL2, one session, proxies for I/O, one-byte pool tasks |
| Reproducible by others? | `scripts/run_all.sh`, `experiment_config.md`, raw JSON, no random seed |
| How was telemetry verified? | Hardware performance counters and kernel /proc/stat |
| Which AI claims were corrected? | `content_audit_report.md`: 1.4 ms fork figure, unmeasured constant thread cost, press-quoted Lozi figure, "same within noise" claim |
| Own code vs reused? | Sec. 7 "Own code and reused libraries" |
| Extension? | Rust worker pool with task queue for the CA-6 micro-OS |
