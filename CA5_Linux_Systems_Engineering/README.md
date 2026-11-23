# CA-5 – Linux Systems Engineering Challenge (research topic R19)

Student: Siril Saran B (25BTRCL254) · Course: 25PCCS201 Operating Systems · Faculty: Dr. Sujeet S Jagtap

Replays the R19 page-reference traces on a **real Linux kernel**: the simulator's FIFO/LRU/OPT policies decide which page to evict with
`madvise(MADV_DONTNEED)`, and the kernel's own page-fault counter (`/proc/<pid>/stat`) is compared with the simulator's prediction.

| Path | What |
|---|---|
| `docs/CA5_Report.pdf` / `.docx` / `.md` | the report |
| `ca5/procinfo.py` | `/proc` process explorer (also a library) |
| `ca5/pager.py`, `ca5/replay_worker.py` | policy-driven real-memory replay, one measured run per process |
| `ca5/demand_worker.py`, `ca5/hold_memory.py` | demand-paging growth experiment, memory hold for `vmstat` |
| `ca5/run_ca5.py` | all experiments (strace, taskset, statistics, figures) |
| `ca5/run_tools.sh` | Bash: lscpu, free, vmstat, ps, taskset evidence |
| `ca5/results/` | raw measurements, strace outputs, tool output |
| `ca5/build_report_ca5.py` | builds the report from the results |

## Run (Linux only; needs `strace` and `taskset`)
```
pip install -r requirements.txt
python ca5/run_ca5.py            # about 3 minutes
bash ca5/run_tools.sh
python ca5/build_report_ca5.py   # needs pandoc, LibreOffice, poppler for the .docx/.pdf
python ca5/procinfo.py           # the process explorer on its own
```
Safety: only child processes started by the scripts are touched; mappings are at most 195 MiB; no system setting is changed.
Timings and the environment table describe the machine that ran the experiment: re-run on your own Linux machine to put your hardware in the report.
