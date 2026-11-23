| Pattern | Seed | Footprint | Frame counts checked | FIFO anomalies | Worst extra faults |
|---|---|---|---|---|---|
| Sequential loop | 0 | 512 | 511 | 0 | 0 |
| Uniform random | 0 | 512 | 511 | 2 | 3 |
| Uniform random | 1 | 512 | 511 | 9 | 12 |
| Uniform random | 2 | 512 | 511 | 7 | 18 |
| Shuffled epochs | 0 | 512 | 511 | 2 | 5 |
| Shuffled epochs | 1 | 512 | 511 | 5 | 10 |
| Shuffled epochs | 2 | 512 | 511 | 4 | 12 |
| Bursty reuse | 0 | 560 | 559 | 1 | 1 |
| Bursty reuse | 1 | 560 | 559 | 1 | 3 |
| Bursty reuse | 2 | 560 | 559 | 2 | 1 |
| Matmul (naive) | 0 | 768 | 30 | 0 | 0 |
| Matmul (tiled) | 0 | 768 | 30 | 0 | 0 |
| Forward-backward | 0 | 256 | 255 | 0 | 0 |
