| Pattern | Policy | Frames at knee (rate < ¼ of small-memory plateau) | Predicted |
|---|---|---|---|
| Matmul (naive) | FIFO | 69 | 69 |
| Matmul (naive) | LRU | 69 | 69 |
| Matmul (naive) | OPT | 60 | 69 |
| Matmul (tiled) | FIFO | 18 | 18 |
| Matmul (tiled) | LRU | 18 | 18 |
| Matmul (tiled) | OPT | 16 | 18 |
