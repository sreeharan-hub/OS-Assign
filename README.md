# Operating Systems (25PCCS201) — Coursework & Lab Portfolio

[![Course](https://img.shields.io/badge/Course-25PCCS201--OS-blue.svg?style=flat-square)](Curriculum_and_Syllabus/Course_Syllabus/Operating%20Systems%20Syllabus.pdf)
[![Faculty](https://img.shields.io/badge/Faculty-Dr.%20Sujeet%20S.%20Jagtap-green.svg?style=flat-square)](https://github.com/sujeetjagtap/Operating-System-Concepts)
[![Verification](https://img.shields.io/badge/Status-100%25%20Verified-brightgreen.svg?style=flat-square)](verify_all.py)
[![Textbook](https://img.shields.io/badge/Textbook-Silberschatz%2010th%20Ed.-orange.svg?style=flat-square)](https://www.os-book.com/)

**Student Name:** Siril Saran B  
**Course Code & Title:** 25PCCS201 — Operating Systems  
**Faculty In-Charge:** Dr. Sujeet S. Jagtap  
**Department:** Computer Science & Engineering (AIML)  
**Institution:** Faculty of Engineering and Technology, JAIN (Deemed-to-be University)  
**Environment:** Ubuntu 24.04 LTS (Linux 6.18 WSL2) & Windows NT 10.0  

---

## Coursework Overview

This repository contains my submissions, lab manuals, and continuous assessment projects for the 25PCCS201 Operating Systems course under Dr. Sujeet S. Jagtap. Every assignment is organized in a self-contained folder with source code, report documents (PDF & Markdown), and test scripts.

---

## Repository Index

| Folder / Component | Module | Scope & Deliverable |
|:---|:---:|:---|
| [`CA1_Systems_Thinking`](CA1_Systems_Thinking/) | **CA-1** | Virtual memory simulator, working set analysis & thrashing model ([CA1 Report PDF](CA1_Systems_Thinking/docs/CA1_Report.pdf)) |
| [`CA2_Performance_Investigation`](CA2_Performance_Investigation/) | **CA-2** | Paging policy comparison (FIFO, LRU, Clock, Belady anomaly) ([CA2 Report PDF](CA2_Performance_Investigation/docs/CA2_Report.pdf)) |
| [`CA3_Design_and_Debugging`](CA3_Design_and_Debugging/) | **CA-3** | Memory simulator bug isolation and stack distance profiler ([CA3 Report PDF](CA3_Design_and_Debugging/docs/CA3_Report.pdf)) |
| [`CA4_Research_Mini_Project`](CA4_Research_Mini_Project/) | **CA-4** | Empirical Concurrency Study: Process vs. Thread in Rust & Python ([Paper PDF](CA4_Research_Mini_Project/paper/Process_vs_Thread_Research_Paper_CA4_final.pdf), [Slides](CA4_Research_Mini_Project/paper/Process_vs_Thread_Slides.pptx)) |
| [`CA5_Linux_Systems_Engineering`](CA5_Linux_Systems_Engineering/) | **CA-5** | Linux memory pressure analysis, `strace` traces & demand paging ([CA5 Report PDF](CA5_Linux_Systems_Engineering/docs/CA5_Report.pdf)) |
| [`CA6_Rust_Micro_OS`](CA6_Rust_Micro_OS/) | **CA-6** | Aeon microkernel design & runnable `no_std` lock-free task queue crate in Rust ([CA6 Report PDF](CA6_Rust_Micro_OS/docs/CA6_Report.pdf)) |
| [`CA7_Viva_Demonstration`](CA7_Viva_Demonstration/) | **CA-7** | Final oral examination defense guide, presentation slides, and demonstration instructions ([Viva Guide](CA7_Viva_Demonstration/viva_preparation_qa.md)) |
| [`Lab_Observations`](Lab_Observations/) | **Labs** | Complete 21-chapter lab manual covering 103 experiments with screenshots ([Master PDF](Lab_Observations/Documents/OS_Lab_Observation_Report_SirilSaran.pdf)) |
| [`Curriculum_and_Syllabus`](Curriculum_and_Syllabus/) | **Specs** | College lab manuals, syllabus, lecture notes, and faculty specifications |
| [`Curriculum_Code_Reference`](Curriculum_Code_Reference/) | **Code** | Chapters 1 to 21 C & Python reference implementations from faculty repository |

---

## Running Verification

To verify that all code, simulators, reports, and screenshots are present and passing:

```bash
python verify_all.py
```

### Running Individual CAs

```bash
# CA-1: Virtual memory simulation and unit tests
cd CA1_Systems_Thinking
python ca1/run_ca1.py
python -m unittest ca1/test_ca1.py

# CA-2: Run page replacement simulations
cd ../CA2_Performance_Investigation
python experiments/run_main.py

# CA-3: Run paging debugger regression checks
cd ../CA3_Design_and_Debugging
python ca3/run_ca3.py

# CA-4: Run Rust concurrency benchmark suite (Linux / WSL2)
cd ../CA4_Research_Mini_Project/rust
cargo test --release

# CA-5: Run Linux memory pressure telemetry (Linux / WSL2)
cd ../../CA5_Linux_Systems_Engineering
bash ca5/run_tools.sh

# CA-6: Check Aeon microkernel task queue crate
cd ../CA6_Rust_Micro_OS
cargo test
```
