"""Touch 50,000 pages (about 195 MiB), hold them for 3 s, release with MADV_DONTNEED, wait 3 s.  Used under `vmstat 1`."""
import mmap
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pager  # noqa: E402

N, P = 50_000, pager.PAGE
time.sleep(2)
m = pager.new_region(N)
for i in range(N):
    m[i * P] = 1
print("touched", N, "pages", flush=True)
time.sleep(3)
m.madvise(mmap.MADV_DONTNEED)
print("released", flush=True)
time.sleep(3)
