| Pattern | Mem % | n | FIFO | LRU | LRU−FIFO | LRU better / worse (seeds) | p (paired t) |
|---|---|---|---|---|---|---|---|
| Sequential loop | 10 | 1 | 1.0000 | 1.0000 | +0.0000 | – | single run |
| Sequential loop | 50 | 1 | 1.0000 | 1.0000 | +0.0000 | – | single run |
| Sequential loop | 90 | 1 | 1.0000 | 1.0000 | +0.0000 | – | single run |
| Uniform random | 10 | 10 | 0.9014 | 0.9016 | +0.0002 | 4 / 5 | 0.472 |
| Uniform random | 50 | 10 | 0.5088 | 0.5088 | +0.0000 | 4 / 6 | 1.000 |
| Uniform random | 90 | 10 | 0.1344 | 0.1327 | -0.0018 | 7 / 2 | 0.127 |
| Shuffled epochs | 10 | 10 | 0.9946 | 0.9948 | +0.0002 | 0 / 9 | 0.004 |
| Shuffled epochs | 50 | 10 | 0.8145 | 0.8530 | +0.0385 | 0 / 10 | <0.001 |
| Shuffled epochs | 90 | 10 | 0.2114 | 0.3614 | +0.1500 | 0 / 10 | <0.001 |
| Bursty reuse | 10 | 10 | 0.3387 | 0.3387 | +0.0000 | 0 / 0 | identical in every seed |
| Bursty reuse | 50 | 10 | 0.2925 | 0.2486 | -0.0439 | 10 / 0 | <0.001 |
| Bursty reuse | 90 | 10 | 0.2694 | 0.2486 | -0.0208 | 10 / 0 | <0.001 |
| Matmul (naive) | 10 | 1 | 0.0329 | 0.0320 | -0.0010 | – | single run |
| Matmul (naive) | 50 | 1 | 0.0029 | 0.0015 | -0.0015 | – | single run |
| Matmul (naive) | 90 | 1 | 0.0019 | 0.0015 | -0.0005 | – | single run |
| Matmul (tiled) | 10 | 1 | 0.0047 | 0.0043 | -0.0005 | – | single run |
| Matmul (tiled) | 50 | 1 | 0.0020 | 0.0028 | +0.0008 | – | single run |
| Matmul (tiled) | 90 | 1 | 0.0014 | 0.0014 | +0.0000 | – | single run |
| Forward-backward | 10 | 1 | 0.9044 | 0.9044 | +0.0000 | – | single run |
| Forward-backward | 50 | 1 | 0.5145 | 0.5145 | +0.0000 | – | single run |
| Forward-backward | 90 | 1 | 0.5045 | 0.1245 | -0.3800 | – | single run |
