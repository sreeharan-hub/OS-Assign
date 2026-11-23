# CA-1 – OS Systems Thinking Challenge

**Scenario chosen:** Challenge F1 – High Page Fault Rate (policy comparison of F2 used as evidence), tied to research topic R19
(page replacement for AI/ML-like access patterns).
**Decision:** shard the data so the working set fits in the available frames (shard + hot set <= frames), keep LRU-style replacement.

Report follows the brief's template, sections A–K: `docs/CA1_Report.pdf` (also `.docx`, `.md`). The brief is `docs/CA1_Brief.md`.

## Files
| File | Purpose |
|---|---|
| `ca1/policies.py` | FIFO, LRU, MRU, OPT and the effective-access-time formula (standard library only) |
| `ca1/workloads.py` | four seeded ML-like workloads |
| `ca1/working_set.py` | working-set size and the thrashing (CPU utilisation) model |
| `ca1/run_ca1.py` | all experiments E1–E7 -> `ca1/results/`, `ca1/figures/` |
| `ca1/test_ca1.py` | 9 unit tests |
| `ca1/build_report_ca1.py` | rebuilds the report from the results |

## Run
```
cd ca1
python3 test_ca1.py       # 9 tests, standard library only
python3 run_ca1.py        # experiments (figures need matplotlib, otherwise skipped)
python3 build_report_ca1.py   # needs pandoc, python-docx, LibreOffice
```
The code itself uses only the Python standard library, like the rest of the course repository.
