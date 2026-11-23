| Pattern | Footprint | Refs | Cold % | Median dist ÷ footprint | P90 dist ÷ footprint |
|---|---|---|---|---|---|
| Sequential loop | 512 | 10240 | 5.000 | 1.000 | 1.000 |
| Uniform random | 512 | 10224 | 5.008 | 0.479 | 0.887 |
| Shuffled epochs | 512 | 10240 | 5.000 | 0.811 | 0.980 |
| Bursty reuse | 560 | 20803 | 2.692 | 0.061 | 1.000 |
| Matmul (naive) | 768 | 528384 | 0.145 | 0.090 | 0.090 |
| Matmul (tiled) | 768 | 540672 | 0.142 | 0.023 | 0.023 |
| Forward-backward | 256 | 10201 | 2.510 | 0.504 | 0.902 |

Cross-check: LRU faults from distances = simulator LRU at **77/77** (pattern, memory) points.
