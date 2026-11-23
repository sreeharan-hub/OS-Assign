# CA-4 coverage check

Source: full spec `Activities-and-Assignments/CA4_Research_Mini_Project.md` in github.com/sujeetjagtap/Operating-System-Concepts (read in full, 1,102 lines). Status 2026-10-21. [x] done, [ ] yours to do.

## Paper to use
`paper/Process_vs_Thread_Research_Paper_CA4_final.docx` (your earlier draft plus every addition below). The older drafts were deleted.

## Final report, 18 sections -> where each is
| Spec section | In paper |
|---|---|
| Title, Abstract | title block, Abstract (added) |
| Introduction, Problem statement | 1. Problem Identification |
| Literature review (+ five review questions) | 2. Literature Discovery; "What the literature shows" (added) |
| Research gap | 3 |
| Question / hypothesis, Objectives | 4, 5; Objectives and rejection conditions (added) |
| Methodology, Experimental setup | 6 (variable table now has Environmental, Repetition, Baseline rows; reproducibility and ethics added) |
| Implementation | 7 (own vs reused code added) |
| Results, Analysis and discussion | 8, 9 (box plot Figure 2b added) |
| Threats to validity / limitations | 10 Limitations + Threats to validity (added) |
| Conclusion, Future work | 10 (CA-6 item added) |
| References | References |
| Methodology & Reproducibility | Experimental controls and reproducibility statement |

## Submission package (10 items)
1. [x] Research proposal: `research_proposal.md` (template order, 12 sections)
2. [x] Literature matrix: `literature_matrix.md` (8 columns)
3. [x] Source code: `rust/`, `python/`, `scripts/`
4. [x] Experimental configuration: `experiment_config.md`
5. [x] Raw data: `results/*.json`
6. [x] Processed data: `processed_data/*.csv`
7. [x] Graphs/tables: `figures/` (15), paper
8. [x] Final report: see above
9. [x] Experimental reproducibility & verification statement
10. [x] Presentation: `paper/Process_vs_Thread_Slides.pptx` rebuilt, 13 slides, follows the 10 stages and the paper's wording
- [ ] Short live demonstration: run `bash scripts/run_all.sh quick` (smoke test)

## Other spec items
- [x] Research ladder level (Level 3)
- [x] Reproducibility list (OS, versions, hardware, libraries, source version, workload method, parameters, repetitions, measurement, seed)
- [x] Variable classes incl. baseline and repetitions
- [x] At least 2 limitations (5), threats to validity
- [x] Numerical evidence, graphs explained, box plot of variability
- [x] Academic-integrity points: own vs reused code, unexpected results reported, ethics line
- [x] Viva questions: `viva_prep.md` (all 15 spec questions)
- [x] Optional CA-6 challenge: `ca6_extension/` (no_std-style spinlock task queue, 2 tests pass in WSL)
- [x] Team model: individual project, one name

## Done in the last round
- [x] Title block: `USN: 25BTRCL257`, no date (as asked)
- [x] Literature search run and logged: `literature_search_log.md`; closest prior work (Bendersky 2018) added as [21] and to the gap paragraph
- [x] Page-fault and context-switch counts measured (`results/followup_counters.json`), added to Section 8.7 and the H4 discussion
- [x] Submission bundle zip rebuilt

## Not possible from here
- ACM papers [22] and [23]: only abstracts read (ACM blocks the PDF download). Sysel [6] was read in full (open postprint).
- Native Linux re-run: needs a native Linux machine; all data is WSL2 and the paper says so.
- Open technical questions (CPython 8x plateau, 1,000-process start-up time) are stated as unexplained in the paper.
- Faculty approval record: skipped at the author's request.
