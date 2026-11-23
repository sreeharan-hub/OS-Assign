# Literature search log

Date: 2026-10-21. Tool: web search (US-only general engine), run by the AI assistant on the author's behalf, first without and then with domain filters for the four databases.

| # | Query | What it returned | Used |
|---|---|---|---|
| 1 | thread vs process creation cost Linux fork parent memory size comparison study | Bendersky blog 2018 (launch time vs heap, C); 2000 PostgreSQL list test (fork cost grows by about 73 us per MB, thread flat); 2004 LKML fork-vs-thread thread (disputed method); AnandTech cross-OS test | Bendersky added as [21]; others not cited (informal) |
| 2 | Sysel "A comparison of processes and threads creation" full text | Only the publisher page and Tomas Bata University repository records; no open full text found by this search (the open postprint was found later, see query 5). Abstract: Linux tasks, same data structures, heavy-weight vs light-weight naming, source fragments attached | Superseded by query 5 |
| 3 | free-threaded Python 3.13 threads vs multiprocessing benchmark worker pool creation overhead | Informal Discourse and blog benchmarks, a 3.14t repo on one MacBook; no study of creation cost | Not cited; supports the Python part of the gap |
| 4 | threads versus processes performance evaluation Linux task length worker pool break-even | Lecture notes, Oracle threads documentation (pools avoid per-task creation), a course assignment; no break-even study | Not cited; supports the break-even part of the gap |
| 5 | Springer Link: process versus thread creation overhead Linux performance comparison | Sysel 2020 chapter; Occlum (SGX) paper on process creation; SPARC T3-4 characterization | Sysel read in full (open postprint at the Tomas Bata University repository, `papers/sysel-2020-processes-threads-creation.pdf`) |
| 6 | ScienceDirect: process thread creation cost fork memory multicore performance comparison | General overview pages on thread creation; Marcel thread library (3.3 us thread create, older hardware); no fork-vs-thread benchmark | Not cited |
| 7 | IEEE Xplore: thread vs process performance comparison creation overhead multicore Linux | Virtualization-overhead paper for multi-threaded computation; RcppThread benchmark (about 10 to 30 us per thread); no Linux process-vs-thread study | Not cited |
| 8 | ACM DL: fork process creation cost page table memory threads comparison | On-demand-fork (EuroSys 2021, Zhao, Gong, Fonseca); Spork (HotOS 2025, Vogele, Thomas, Honig); page-size study | Both added as [22] and [23], abstracts only (PDF download blocked) |

Note: the site-restricted searches were made through a general search engine with a domain filter, not through the sites' own search forms. Metadata of [22], [23] and [6] was checked in Crossref.

Conclusions: earlier measurements show creation cost against address-space size for C ([4], [6], [21], [22]); Sysel measured it directly (fork about 20 ms at 4 GB, thread 170 to 290 us). I found no source that combines creation cost with task length and pools, memory with copy-on-write, and Rust against CPython with and without the GIL. The paper words this as "I did not find".

Limit: eight queries through one search engine. Not an exhaustive search.
