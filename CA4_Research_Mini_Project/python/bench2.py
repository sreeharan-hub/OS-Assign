"""Process vs thread benchmarks in CPython (version 2). Linux only.

Runs under both the default (GIL) and the free-threaded (3.14t) interpreter.
Every experiment stores all raw samples. Usage:
    python bench2.py --tag gil --out results/py_gil.json [--sections create,cpu,...]
Internal: python bench2.py --serve MODEL CPU_US   (echo server used by the tcp section)
"""
import argparse, asyncio, json, os, signal, socket, subprocess, sys, threading, time, queue
import multiprocessing as mp
import concurrent.futures as cf

SECTIONS = ["create", "cpu", "io", "tcp", "mem", "pingpong", "pool"]


def reps(n, f):
    return [f() for _ in range(n)]


def noop():
    pass


def spin_us(us):
    if us <= 0:
        return
    end = time.perf_counter() + us / 1e6
    while time.perf_counter() < end:
        pass


# ------------------------------------------------------------------ create
def create_thread(n):
    t = time.perf_counter()
    for _ in range(n):
        th = threading.Thread(target=noop)
        th.start()
        th.join()
    return (time.perf_counter() - t) / n * 1e6


def create_proc(method, n):
    ctx = mp.get_context(method)
    t = time.perf_counter()
    for _ in range(n):
        p = ctx.Process(target=noop)
        p.start()
        p.join()
    return (time.perf_counter() - t) / n * 1e6


def create_os_fork(n):
    t = time.perf_counter()
    for _ in range(n):
        pid = os.fork()
        if pid == 0:
            os._exit(0)
        os.waitpid(pid, 0)
    return (time.perf_counter() - t) / n * 1e6


def sec_create():
    return {
        "thread": reps(15, lambda: create_thread(1000)),
        "os.fork": reps(15, lambda: create_os_fork(300)),
        "mp_fork": reps(15, lambda: create_proc("fork", 150)),
        "mp_forkserver": reps(8, lambda: create_proc("forkserver", 80)),
        "mp_spawn": reps(5, lambda: create_proc("spawn", 20)),
    }


# ------------------------------------------------------------------ cpu
TOTAL = 30_000_000


def spin(n):
    s = 0
    for i in range(n):
        s += i * i
    return s


def cpu_threads(w):
    t = time.perf_counter()
    hs = [threading.Thread(target=spin, args=(TOTAL // w,)) for _ in range(w)]
    for h in hs:
        h.start()
    for h in hs:
        h.join()
    return time.perf_counter() - t


def cpu_procs(w):
    ctx = mp.get_context("fork")
    t = time.perf_counter()
    ps = [ctx.Process(target=spin, args=(TOTAL // w,)) for _ in range(w)]
    for p in ps:
        p.start()
    for p in ps:
        p.join()
    return time.perf_counter() - t


def sec_cpu():
    ws = [1, 2, 4, 8, 12, 16, 24]
    return {
        "threads": {w: reps(7, lambda: cpu_threads(w)) for w in ws},
        "procs": {w: reps(7, lambda: cpu_procs(w)) for w in ws},
    }


# ------------------------------------------------------------------ io (blocking waits)
TASKS, WAIT = 240, 0.02


def io_work(k):
    for _ in range(k):
        time.sleep(WAIT)


def io_threads(w):
    t = time.perf_counter()
    hs = [threading.Thread(target=io_work, args=(TASKS // w,)) for _ in range(w)]
    for h in hs:
        h.start()
    for h in hs:
        h.join()
    return time.perf_counter() - t


def io_procs(w):
    ctx = mp.get_context("fork")
    t = time.perf_counter()
    ps = [ctx.Process(target=io_work, args=(TASKS // w,)) for _ in range(w)]
    for p in ps:
        p.start()
    for p in ps:
        p.join()
    return time.perf_counter() - t


def io_asyncio(w):
    async def worker(k):
        for _ in range(k):
            await asyncio.sleep(WAIT)

    async def main():
        await asyncio.gather(*[worker(TASKS // w) for _ in range(w)])

    t = time.perf_counter()
    asyncio.run(main())
    return time.perf_counter() - t


def sec_io():
    ws = [1, 2, 4, 8, 16, 32, 64]
    return {
        "threads": {w: reps(5, lambda: io_threads(w)) for w in ws},
        "procs": {w: reps(5, lambda: io_procs(w)) for w in ws},
        "asyncio": {w: reps(5, lambda: io_asyncio(w)) for w in ws},
    }


# ------------------------------------------------------------------ tcp echo server models
BACKEND_S = 0.002  # simulated database wait inside every request


def handle(conn, cpu_us):
    try:
        data = conn.recv(1024)
        time.sleep(BACKEND_S)
        spin_us(cpu_us)
        conn.sendall(data)
    finally:
        conn.close()


def serve(model, cpu_us):
    if model == "asyncio":
        async def h(r, w):
            data = await r.read(1024)
            await asyncio.sleep(BACKEND_S)
            spin_us(cpu_us)
            w.write(data)
            await w.drain()
            w.close()

        async def main():
            srv = await asyncio.start_server(h, "127.0.0.1", 0, backlog=512)
            print(srv.sockets[0].getsockname()[1], flush=True)
            async with srv:
                await srv.serve_forever()

        asyncio.run(main())
        return
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 0))
    s.listen(512)
    print(s.getsockname()[1], flush=True)
    if model == "fork":
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    pool = cf.ThreadPoolExecutor(32) if model == "threadpool" else None
    while True:
        c, _ = s.accept()
        if model == "thread":
            threading.Thread(target=handle, args=(c, cpu_us), daemon=True).start()
        elif model == "threadpool":
            pool.submit(handle, c, cpu_us)
        elif model == "fork":
            if os.fork() == 0:
                s.close()
                handle(c, cpu_us)
                os._exit(0)
            c.close()


async def client_run(port, conc, per):
    lat = []

    async def one():
        t = time.perf_counter()
        r, w = await asyncio.open_connection("127.0.0.1", port)
        w.write(b"x" * 1024)
        await w.drain()
        await r.read(1024)
        w.close()
        lat.append(time.perf_counter() - t)

    async def worker():
        for _ in range(per):
            await one()

    t0 = time.perf_counter()
    await asyncio.gather(*[worker() for _ in range(conc)])
    el = time.perf_counter() - t0
    lat.sort()
    return conc * per / el, lat[len(lat) // 2] * 1e3, lat[int(len(lat) * 0.99) - 1] * 1e3


def tcp_once(model, cpu_us, conc=32, per=40):
    p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--serve", model, str(cpu_us)],
                         stdout=subprocess.PIPE, text=True)
    try:
        port = int(p.stdout.readline())
        asyncio.run(client_run(port, 4, 5))  # warm-up
        return asyncio.run(client_run(port, conc, per))
    finally:
        p.terminate()
        p.wait()


def sec_tcp():
    out = {}
    for cpu_us in (0, 500):
        for model in ("thread", "threadpool", "fork", "asyncio"):
            rs = reps(5, lambda: tcp_once(model, cpu_us))
            out[f"{model}_cpu{cpu_us}"] = {
                "req_per_s": [r[0] for r in rs],
                "p50_ms": [r[1] for r in rs],
                "p99_ms": [r[2] for r in rs],
            }
    return out


# ------------------------------------------------------------------ memory
def status_kb(pid, fname, key):
    try:
        for l in open(f"/proc/{pid}/{fname}"):
            if l.startswith(key):
                return float(l.split()[1])
    except OSError:
        pass
    return 0.0


def pss(pid): return status_kb(pid, "smaps_rollup", "Pss:")
def pte(pid): return status_kb(pid, "status", "VmPTE:")


def mem_threads(n):
    b0, p0 = pss("self"), pte("self")
    ev = threading.Event()
    hs = [threading.Thread(target=ev.wait) for _ in range(n)]
    for h in hs:
        h.start()
    time.sleep(0.2)
    b1, p1 = pss("self"), pte("self")
    ev.set()
    for h in hs:
        h.join()
    return (b1 - b0) / n, (p1 - p0) / n


def mem_procs(method, n):
    ctx = mp.get_context(method)
    b0, p0 = pss("self"), pte("self")
    ev = ctx.Event()
    ps = [ctx.Process(target=ev.wait) for _ in range(n)]
    for p in ps:
        p.start()
    time.sleep(0.3 if method == "fork" else 1.0 + 0.05 * n)
    b1 = pss("self") + sum(pss(p.pid) for p in ps)
    p1 = pte("self") + sum(pte(p.pid) for p in ps)
    ev.set()
    for p in ps:
        p.join()
    return (b1 - b0) / n, (p1 - p0) / n


def sec_mem():
    out = {}
    cfg = [("thread", lambda n: mem_threads(n), [1, 10, 50, 100], 5),
           ("fork", lambda n: mem_procs("fork", n), [1, 10, 50, 100], 5),
           ("spawn", lambda n: mem_procs("spawn", n), [1, 10, 50], 3)]
    for name, f, ns, r in cfg:
        out[name + "_pss_kib_each"] = {n: [x[0] for x in reps(r, lambda: f(n))] for n in ns}
    # page-table figure from the same runs is cheap; repeat once for fork and thread
    out["thread_pte_kib_each"] = {n: [x[1] for x in reps(3, lambda: mem_threads(n))] for n in [10, 100]}
    out["fork_pte_kib_each"] = {n: [x[1] for x in reps(3, lambda: mem_procs("fork", n))] for n in [10, 100]}
    return out


# ------------------------------------------------------------------ ping-pong
def pin(cpu):
    if cpu is not None:
        os.sched_setaffinity(0, {cpu})


def pp_threads(n, a=None, b=None):
    qa, qb = queue.Queue(), queue.Queue()

    def echo():
        pin(b)
        for _ in range(n):
            qb.put(qa.get())

    th = threading.Thread(target=echo)
    th.start()
    prev = os.sched_getaffinity(0)
    pin(a)
    t = time.perf_counter()
    for _ in range(n):
        qa.put(1)
        qb.get()
    e = time.perf_counter() - t
    th.join()
    os.sched_setaffinity(0, prev)
    return e / n * 1e6


def _echo(c, n, cpu):
    pin(cpu)
    for _ in range(n):
        c.send(c.recv())


def pp_procs(n, a=None, b=None):
    ctx = mp.get_context("fork")
    p, c = ctx.Pipe()
    pr = ctx.Process(target=_echo, args=(c, n, b))
    pr.start()
    prev = os.sched_getaffinity(0)
    pin(a)
    t = time.perf_counter()
    for _ in range(n):
        p.send(1)
        p.recv()
    e = time.perf_counter() - t
    pr.join()
    os.sched_setaffinity(0, prev)
    return e / n * 1e6


def sec_pingpong():
    n = 15000
    return {
        "thread_unpinned": reps(10, lambda: pp_threads(n)),
        "proc_unpinned": reps(10, lambda: pp_procs(n)),
        "thread_same_core": reps(10, lambda: pp_threads(n, 0, 0)),
        "proc_same_core": reps(10, lambda: pp_procs(n, 0, 0)),
        "thread_diff_core": reps(10, lambda: pp_threads(n, 0, 2)),
        "proc_diff_core": reps(10, lambda: pp_procs(n, 0, 2)),
    }


# ------------------------------------------------------------------ per-task creation vs pools
W = 24


def task_per_thread(n, d):
    t = time.perf_counter()
    left = n
    while left > 0:
        b = min(W, left)
        hs = [threading.Thread(target=spin_us, args=(d,)) for _ in range(b)]
        for h in hs:
            h.start()
        for h in hs:
            h.join()
        left -= b
    return time.perf_counter() - t


def task_per_fork(n, d):
    t = time.perf_counter()
    left = n
    while left > 0:
        b = min(W, left)
        pids = []
        for _ in range(b):
            pid = os.fork()
            if pid == 0:
                spin_us(d)
                os._exit(0)
            pids.append(pid)
        for p in pids:
            os.waitpid(p, 0)
        left -= b
    return time.perf_counter() - t


def task_pool_threads(n, d):
    t = time.perf_counter()
    with cf.ThreadPoolExecutor(W) as ex:
        list(ex.map(spin_us, [d] * n))
    return time.perf_counter() - t


def task_pool_procs(n, d):
    t = time.perf_counter()
    with cf.ProcessPoolExecutor(W, mp_context=mp.get_context("fork")) as ex:
        list(ex.map(spin_us, [d] * n))
    return time.perf_counter() - t


def sec_pool():
    ds = [(0, 2400), (100, 2400), (1000, 2400), (10000, 480)]
    out = {"task_counts": {d: n for d, n in ds}}
    for name, f in (("per_thread", task_per_thread), ("per_fork", task_per_fork),
                    ("pool_threads", task_pool_threads), ("pool_procs", task_pool_procs)):
        out[name + "_s"] = {d: reps(5, lambda: f(n, d)) for d, n in ds}
    return out


# ------------------------------------------------------------------ main
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", nargs=2)
    ap.add_argument("--tag", default="gil")
    ap.add_argument("--out")
    ap.add_argument("--sections", default=",".join(SECTIONS))
    a = ap.parse_args()
    if a.serve:
        serve(a.serve[0], int(a.serve[1]))
        sys.exit(0)
    res = {"python": sys.version.split()[0], "tag": a.tag,
           "gil_enabled": getattr(sys, "_is_gil_enabled", lambda: True)(), "ncpu": os.cpu_count()}
    if os.path.exists(a.out):
        res = json.load(open(a.out))  # resume: keep sections already done
    for s in a.sections.split(","):
        t = time.time()
        res[s] = globals()["sec_" + s]()
        json.dump(res, open(a.out, "w"))
        print(f"[{a.tag}] {s} done in {time.time() - t:.0f}s", flush=True)
