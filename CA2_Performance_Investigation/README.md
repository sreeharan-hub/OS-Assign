# OS CA-2 – Page-Replacement Performance Investigation

**Course:** 25PCCS201 Operating Systems · **Assessment:** CA-2 (OS Performance Investigation) ·
**Experiment base:** Experiment 9 (Page Replacement) + Investigation C (memory-pressure threshold)
**Topic:** R19 – page replacement for AI/ML-like access patterns

> **Question:** For ML-shaped page-reference patterns, how does the access pattern change the
> page-fault rate of FIFO, LRU and OPT as memory shrinks – and when does LRU beat FIFO?

A controlled, reproducible Python simulation. It implements FIFO, LRU, OPT (plus MRU, Random and CLOCK
as controls), replays seven synthetic ML-shaped workloads at 11 memory sizes, and produces raw CSVs,
statistics, figures and a report in the CA-2 18-section format.

## Quick start

```bash
# 1. Python 3.11+ (developed on 3.13)
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Run everything: tests -> experiments -> analysis -> report   (about 1.5 minutes)
python run_all.py
```

Outputs:

| Where | What |
|---|---|
| `docs/CA2_Report.docx` / `.pdf` / `.md` | the CA-2 report, formatted like the research paper (the `.docx` and `.pdf` need `pandoc`; the `.pdf` also needs LibreOffice; the `.md` is always produced) |
| `results/*.csv` | **raw measurements** (every run kept) + summaries |
| `results/tables/*.md` | the tables used in the report |
| `results/figures/*.png` | figures 1–8 |
| `results/environment.json` | CPU, RAM, OS, Python and library versions, date |

Run a single piece:

```bash
python -m unittest discover -s tests -v     # 14 validation tests (textbook answers, Belady's string...)
python experiments/run_main.py              # main experiment
python experiments/run_belady.py            # Belady's anomaly search
python experiments/run_reuse.py             # reuse-distance cross-check of LRU
python experiments/run_sweeps.py            # footprint / hot-set / tile sweeps
python experiments/run_knee.py              # matmul memory-pressure knee
python experiments/run_timing.py            # timing (leave the machine idle!)
python experiments/analyze.py               # statistics + figures + tables
python experiments/build_report.py          # assemble the report
```

## Report formatting

The report is laid out to match the research-activity paper: US Letter, 1-inch margins, the bold Arial
running header (course on the right) on every page, a thin page border, Calibri 11 body text, Calibri bold
headings, and bordered tables with a grey header row. This comes from `docs/reference.docx` (a Word template,
built by `experiments/make_reference_docx.py`) and `experiments/format_docx.py` (table/figure/marker formatting).
To change the header text (e.g. the second line) edit `HEADER_LEFT` / `HEADER_RIGHT` in `make_reference_docx.py`,
run it, then `python experiments/build_report.py`. Yellow-highlighted **[STUDENT: …]** markers in the report are
things only you can fill in. The report follows the 18-section structure of the CA-2 document and adds the
submission checklist (Appendix A) and rubric mapping (Appendix B).

## Repository layout

```
src/            simulator.py (policies)  traces.py (workloads)  stackdist.py  common.py
experiments/    run_*.py  analyze.py  build_report.py  format_docx.py  make_reference_docx.py  make_env.py
tests/          test_simulator.py
results/        raw CSVs, tables/, figures/, environment.json   (committed: raw data is evidence)
docs/           CA2_Report.md / .docx / .pdf   reference.docx (Word template)
run_all.py      one-command pipeline          Makefile   make all / make test
```

## What is reproducible and what is not

* **Fault counts are deterministic.** All randomness is seeded (`random.Random`), so every machine gives the
  *same* fault counts, tables and figures (other than the timing figure).
* **Timing is machine-specific.** `results/raw_timing.csv` and Fig 7 depend on your CPU – that is why you must
  re-run on your own machine and report *your* environment. It times a Python simulator, not an OS kernel.

## What YOU must do before submitting (important)

All results and figures are strictly derived from empirical simulation execution.

1. Run `python run_all.py` **on your own machine**. Confirm the tests pass.
2. Open `docs/CA2_Report.md` and complete every **[STUDENT: …]** marker – especially §6 (your hardware)
   and §17 (AI disclosure: what *you* re-ran and verified).
3. Read the code and be ready to explain it (the viva/questions). Try changing a parameter in
   `src/traces.py` and re-running; spot-check one fault count by hand on a small string.
4. Compare your `results/summary_main.csv` with the one in the repository – they should be identical.
5. Re-build the report (`python experiments/build_report.py`, also run by `run_all.py`) and proofread the `.docx`;
   you can edit it in Word and export your own PDF.

## Git / GitHub

```bash
git init -b main              # (already done in this archive)
git add -A && git commit -m "message"
# create an EMPTY repo on github.com (no README), then:
git remote add origin https://github.com/<your-username>/os-ca2-page-replacement.git
git push -u origin main
```

Keep the history honest: commit your own re-runs and edits so the log shows your work.

## Design notes

* Immediately repeated references to the same page are dropped (they can never fault); fault rates are per
  page-changing reference. A unit test checks this changes no fault count.
* Workloads were re-implemented from the research paper's description. The sequential, random, shuffled and
  forward-backward results agree with the paper; the *bursty* cold-scan layout is not fully specified in the
  paper, so this repository's definition (`src/traces.py`) is a documented choice and gives a larger LRU advantage.
* LRU stack distances (Mattson algorithm) give the whole LRU fault curve in one pass and are used to
  cross-check the simulator at every memory level.
* CLOCK sets the reference bit when a page is loaded and on every hit.


## Cover page and contents

The report opens with a cover page in the style of the department lab record (logo in `docs/logo.png`, student/USN and faculty tables) followed by a contents page whose page numbers are filled in automatically (two-pass build in `experiments/build_report.py`). Edit the name, USN and faculty in `build_docx()` if needed.
