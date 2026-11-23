# Operating Systems (25PCCS201) — Continuous Assessments Portfolio

**Student Name:** Sreeharan (25BTRCL257)  
**Course:** 25PCCS201 — Operating Systems  
**Course In-Charge:** Dr. Sujeet S. Jagtap  
**Institution:** Faculty of Engineering and Technology, JAIN (Deemed-to-be University)  
**Research Topic:** R19 — Memory Management & Page Replacement for AI/ML Workloads  

---

## Continuous Assessments Overview

Each folder contains a self-contained, reproducible assignment submission with implementation source code, verification test suites, empirical data, and technical reports.

| Module | Title | Key Deliverables & Focus | Verification |
| :--- | :--- | :--- | :---: |
| [`CA1_Systems_Thinking`](CA1_Systems_Thinking/) | **Systems Thinking Challenge** | Working-set simulation, F1 page fault investigation, stdlib simulator, 9 unit tests, 11-page report | `pytest` / Python |
| [`CA2_Performance_Investigation`](CA2_Performance_Investigation/) | **Performance Investigation** | Paging algorithms (FIFO, LRU, OPT, SLRU), Belady's anomaly, sensitivity sweeps, 25-page report | Python simulator |
| [`CA3_Design_and_Debugging`](CA3_Design_and_Debugging/) | **Design & Debugging** | Stack-distance locality profiler, synthetic bug injection & fix validation, 15-page report | Python test suite |
| [`CA4_Research_Mini_Project`](CA4_Research_Mini_Project/) | **Research Mini-Project** | Empirical research paper: *Page Replacement for AI/ML-Like Access Patterns* (9-page peer review format) | Research PDF |
| [`CA5_Linux_Systems_Engineering`](CA5_Linux_Systems_Engineering/) | **Linux Systems Engineering** | Real kernel page fault benchmarking, `/proc` RSS telemetry, synthetic demand pager worker, 16-page report | Linux / WSL2 |
| [`CA6_Rust_Micro_OS`](CA6_Rust_Micro_OS/) | **Aeon Microkernel Task Queue** | Memory-safe lock-free task queue and scheduler crate written in Rust, Cargo test harness, 6-page report | `cargo check` |

---

## Master Verification Suite

To verify all 6 continuous assessments in a single command:

```bash
python verify_all.py
```

This verifies the unit test suites, algorithmic simulation models, kernel telemetry outputs, and report deliverables across the entire repository.

---

## Environment & Requirements

- **Python 3.10+**: `pip install -r requirements.txt` (or stdlib modules `math`, `time`, `os`, `sys`, `subprocess`)
- **Rust toolchain (CA-6)**: `cargo check` / `cargo test`
- **Linux / WSL2 (CA-5)**: Recommended for live `/proc` sampling and Linux memory pressure experiments
