# Experiment configuration

Environment: Intel Core i7-14650HX (16 cores, 24 logical), 11.7 GB RAM for the VM, Windows 11 Home (Balanced power plan, on AC), Ubuntu 26.04.1 on WSL2, Linux 6.18.33.2-microsoft-standard-WSL2, 4 KiB pages. Full details: `results/system_info.txt`.
Software: Rust 1.99.0 (release; rayon 1, tokio 1), CPython 3.14.8 default and free-threaded (uv), numpy, scipy, matplotlib, python-docx, python-pptx.
Random seed: none. The workloads are deterministic.

| Experiment | Parameters | Repetitions | Output file |
|---|---|---|---|
| Creation (Rust, Python) | empty worker, create+join, 300 to 2,000 per run | 15 to 20 samples (5 for spawn) | `rust_final.json`, `py_gil.json`, `py_ft.json` |
| Creation vs parent memory | 0, 64, 256, 1,024 MiB touched | 10 runs | `rust_final.json`, `followup_heap_thread.json` |
| fork with live children | 0, 100, 500, 1,000 sleeping children | see file | `followup_fork_live.json` |
| Per-task creation vs pools | 24 workers, tasks 0 to 10,000 us | see file | `rust_final.json`, `followup_pool_ipc.json` |
| CPU-bound scaling | 1 to 32 workers; Rust 4 to 24 workers interleaved | 10 to 30 | `rust_final.json`, `followup_cpu2.json`, `py_*.json` |
| Waiting workers | Rust 100 to 10,000 workers x 100 ms; Python 240 x 20 ms over 1 to 64 workers | see file | `rust_final.json`, `py_*.json` |
| Memory | idle PSS and VmPTE (100 workers, 50 for spawn); 8 workers on 64 MiB shared buffer | see file | `rust_final.json`, `py_*.json` |
| Context switch, futex hand-off | same core, 1-byte messages | see file | `followup_park.json`, `followup_topo.json` |
| Page faults and context switches | 200 workers per rep; 64 MiB buffer written by one worker (system CPython 3.14.4, GIL) | 10 | `followup_counters.json` (`python/bench_counters.py`) |

Rebuild: `bash scripts/run_all.sh` (about 1 hour, inside Linux, machine idle). Then `python python/figs2.py` and the paper build scripts.
Processed data: `processed_data/*_summary.csv` (mean, sd, 95% CI, min, max per measurement, produced from the raw JSON in `results/`).
