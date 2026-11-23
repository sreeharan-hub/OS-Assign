| Sweep | Pattern | Value | LRU−FIFO @50% | LRU−FIFO @90% | OPT @50% (or LRU @5% for tile) |
|---|---|---|---|---|---|
| footprint | Sequential loop | 256 | 0.000 | 0.000 | 0.525 |
| footprint | Sequential loop | 512 | 0.000 | 0.000 | 0.525 |
| footprint | Sequential loop | 1024 | 0.000 | 0.000 | 0.525 |
| footprint | Uniform random | 256 | 0.000 | -0.000 | 0.223 |
| footprint | Uniform random | 512 | 0.000 | -0.002 | 0.218 |
| footprint | Uniform random | 1024 | -0.000 | -0.000 | 0.216 |
| footprint | Shuffled epochs | 256 | 0.037 | 0.151 | 0.525 |
| footprint | Shuffled epochs | 512 | 0.039 | 0.150 | 0.525 |
| footprint | Shuffled epochs | 1024 | 0.038 | 0.149 | 0.525 |
| hot_set | Bursty reuse | 24 | -0.022 | -0.011 | 0.144 |
| hot_set | Bursty reuse | 48 | -0.044 | -0.021 | 0.148 |
| hot_set | Bursty reuse | 96 | -0.084 | -0.041 | 0.160 |
| tile | Matmul (tiled), LRU @5% | 8 | – | – | 0.011 |
| tile | Matmul (tiled), LRU @5% | 16 | – | – | 0.006 |
| tile | Matmul (tiled), LRU @5% | 32 | – | – | 0.033 |
