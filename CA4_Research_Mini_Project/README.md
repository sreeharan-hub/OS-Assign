# Process vs Thread: when are threads more efficient?

Measurement study for course 25PCCS201 (Operating Systems), CA-4 topic R6. It compares threads and processes on Linux with Rust and CPython 3.14 (default and free-threaded builds), measured on WSL2.

## Where things are

| Path | Content |
|---|---|
| `paper/Process_vs_Thread_Research_Paper_CA4_final.docx` / `.pdf` | the paper (17 pages) |
| `paper/os_assig.docx` | the same content laid out on the course template (`Template_Research-Writeup-1.docx`); built by `python/make_os_assig.py` |
| `paper/Process_vs_Thread_Slides.pptx` | 13-slide presentation |
| `paper/references.ris`, `references.bib` | import into Zotero |
| `paper/os_process_vs_thread_submission_bundle.zip` | offline archive of the whole package |
| `submission_pack/` | CA-4 package: proposal, literature matrix and search log, experiment configuration, processed data (CSV), viva notes, coverage checklist, `ca6_extension/` |
| `papers/` | open-access PDFs of the cited papers |
| `rust/` | Rust benchmark (`ptbench`: rayon, tokio, libc calls via `extern "C"`) |
| `python/bench2.py`, `bench_counters.py` | Python benchmarks (`bench2.py` on both builds; counters for page faults and context switches) |
| `python/analysis.py`, `figs2.py`, `fig_box.py`, `build_slides.py` | statistics, figures, slides |
| `python/build_paper3.py`, `docx_helpers.py` | first generator of the paper; the submitted .docx was edited after generation, so it is the source of truth |
| `python/fix_docx_ns.py` | repair tool for .docx files that Word reports as corrupted after python-docx edits |
| `results/` | raw samples as JSON |
| `figures/` | 15 figures (`fig01` to `fig15`) |
| `scripts/` | build and run scripts |
| `content_audit_report.md`, `research_verification_checklist.md` | fact-check notes |

## Reproduce

Run inside Linux (native is best; WSL2 Ubuntu works). Keep the machine idle and plugged in, and use the high-performance power plan.

    bash scripts/run_all.sh        # about 1 hour: builds Rust, installs free-threaded Python with uv, runs everything

Then on any machine with Python 3.14, numpy, scipy, matplotlib and python-pptx:

    python python/figs2.py
    python python/fig_box.py
    python python/build_slides.py

## Known issues

- All data comes from WSL2 (a virtual machine). A native-Linux repeat is not done.
- The CPython speed-up plateau (about 8x on 24 logical CPUs) and the slow start of 1,000 processes are unexplained.
- A first Rust run left the main thread pinned to CPU 0 after the ping-pong test. The code now restores the CPU mask and the affected sections were re-run.
- `python/build_paper3.py` needs a `style_base.docx` that is not in the project; it cannot regenerate the paper.
