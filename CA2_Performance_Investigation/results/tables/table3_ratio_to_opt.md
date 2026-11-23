| Pattern | Mem % | FIFO/OPT | LRU/OPT |
|---|---|---|---|
| Sequential loop | 10 | 1.10 | 1.10 |
| Sequential loop | 50 | 1.90 | 1.90 |
| Sequential loop | 90 | 6.91 | 6.91 |
| Uniform random | 10 | 1.46 | 1.46 |
| Uniform random | 50 | 2.34 | 2.34 |
| Uniform random | 90 | 2.02 | 2.00 |
| Shuffled epochs | 10 | 1.10 | 1.10 |
| Shuffled epochs | 50 | 1.55 | 1.62 |
| Shuffled epochs | 90 | 1.46 | 2.50 |
| Bursty reuse | 10 | 1.38 | 1.38 |
| Bursty reuse | 50 | 1.97 | 1.68 |
| Bursty reuse | 90 | 5.26 | 4.86 |
| Matmul (naive) | 10 | 1.07 | 1.04 |
| Matmul (naive) | 50 | 2.00 | 1.00 |
| Matmul (naive) | 90 | 1.33 | 1.00 |
| Matmul (tiled) | 10 | 1.50 | 1.35 |
| Matmul (tiled) | 50 | 1.44 | 2.00 |
| Matmul (tiled) | 90 | 1.00 | 1.00 |
| Forward-backward | 10 | 1.00 | 1.00 |
| Forward-backward | 50 | 1.00 | 1.00 |
| Forward-backward | 90 | 4.05 | 1.00 |
