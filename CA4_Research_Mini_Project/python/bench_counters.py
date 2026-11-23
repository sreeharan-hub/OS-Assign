"""Page-fault and context-switch counts for threads and forked processes (CA-4 'preferred evidence').

Run inside Linux:  python3 python/bench_counters.py > results/followup_counters.json
A: create+join N empty workers; count minor faults and context switches per worker.
B: parent touches a 64 MiB buffer, one worker writes every page; count the minor faults the worker causes.
"""
import json, mmap, os, resource, sys, threading

N = 200
REPS = 10
BUF = 64 * 1024 * 1024
PAGE = 4096


def snap(who):
    r = resource.getrusage(who)
    return r.ru_minflt, r.ru_nvcsw + r.ru_nivcsw


def run_a_threads():
    f0, c0 = snap(resource.RUSAGE_SELF)
    for _ in range(N):
        t = threading.Thread(target=lambda: None)
        t.start(); t.join()
    f1, c1 = snap(resource.RUSAGE_SELF)
    return (f1 - f0) / N, (c1 - c0) / N


def run_a_fork():
    s0 = snap(resource.RUSAGE_SELF); k0 = snap(resource.RUSAGE_CHILDREN)
    for _ in range(N):
        pid = os.fork()
        if pid == 0:
            os._exit(0)
        os.waitpid(pid, 0)
    s1 = snap(resource.RUSAGE_SELF); k1 = snap(resource.RUSAGE_CHILDREN)
    faults = (s1[0] - s0[0]) + (k1[0] - k0[0])
    cs = (s1[1] - s0[1]) + (k1[1] - k0[1])
    return faults / N, cs / N


def touch(buf):
    for off in range(0, BUF, PAGE):
        buf[off] = 1


def run_b_thread(buf):
    f0, _ = snap(resource.RUSAGE_SELF)
    t = threading.Thread(target=touch, args=(buf,)); t.start(); t.join()
    return snap(resource.RUSAGE_SELF)[0] - f0


def run_b_fork(buf):
    k0 = snap(resource.RUSAGE_CHILDREN)[0]
    pid = os.fork()
    if pid == 0:
        touch(buf); os._exit(0)
    os.waitpid(pid, 0)
    return snap(resource.RUSAGE_CHILDREN)[0] - k0


out = {"python": sys.version.split()[0], "ncpu": os.cpu_count(), "n_per_rep": N, "reps": REPS,
       "a_thread_minflt_per_worker": [], "a_thread_ctxsw_per_worker": [],
       "a_fork_minflt_per_worker": [], "a_fork_ctxsw_per_worker": [],
       "b_thread_minflt_write64mib": [], "b_fork_minflt_write64mib": []}
buf = mmap.mmap(-1, BUF)
for off in range(0, BUF, PAGE):  # parent touches every page first
    buf[off] = 1
for _ in range(REPS):
    f, c = run_a_threads(); out["a_thread_minflt_per_worker"].append(f); out["a_thread_ctxsw_per_worker"].append(c)
    f, c = run_a_fork(); out["a_fork_minflt_per_worker"].append(f); out["a_fork_ctxsw_per_worker"].append(c)
    out["b_thread_minflt_write64mib"].append(run_b_thread(buf))
    out["b_fork_minflt_write64mib"].append(run_b_fork(buf))
print(json.dumps(out))
