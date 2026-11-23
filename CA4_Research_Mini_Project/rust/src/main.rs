// Process vs thread benchmarks, version 2 (Linux).
// Every experiment stores all raw samples so the analysis step can compute
// means, confidence intervals and tests. Output: one JSON object on stdout.
#![allow(clashing_extern_declarations)]
use rayon::prelude::*;
use std::fs;
use std::hint::black_box;
use std::process::Command;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::mpsc;
use std::sync::{Arc, Barrier};
use std::thread;
use std::time::{Duration, Instant};

extern "C" {
    fn fork() -> i32;
    fn waitpid(pid: i32, status: *mut i32, opts: i32) -> i32;
    fn _exit(code: i32) -> !;
    fn pipe(fds: *mut i32) -> i32;
    fn read(fd: i32, buf: *mut u8, n: usize) -> isize;
    fn write(fd: i32, buf: *const u8, n: usize) -> isize;
    fn close(fd: i32) -> i32;
    fn sched_setaffinity(pid: i32, size: usize, mask: *const u64) -> i32;
    fn sched_getaffinity(pid: i32, size: usize, mask: *mut u64) -> i32;
}

fn get_aff() -> [u64; 16] {
    let mut m = [0u64; 16];
    unsafe { sched_getaffinity(0, 128, m.as_mut_ptr()) };
    m
}
fn set_aff(m: &[u64; 16]) {
    unsafe { sched_setaffinity(0, 128, m.as_ptr()) };
}

const W: usize = 24; // concurrency used for pool experiments

fn reap(pid: i32) {
    let mut st = 0;
    unsafe { waitpid(pid, &mut st, 0) };
}

fn pin(cpu: usize) {
    let mut mask = [0u64; 16];
    mask[cpu / 64] |= 1u64 << (cpu % 64);
    unsafe { sched_setaffinity(0, 128, mask.as_ptr()) };
}

fn reps<F: FnMut() -> f64>(n: usize, mut f: F) -> Vec<f64> {
    (0..n).map(|_| f()).collect()
}

fn arr(v: &[f64]) -> String {
    let s: Vec<String> = v.iter().map(|x| format!("{:.4}", x)).collect();
    format!("[{}]", s.join(","))
}

struct Out {
    first: bool,
}
impl Out {
    fn new() -> Out {
        println!("{{");
        Out { first: true }
    }
    fn key(&mut self, k: &str, raw: &str) {
        if !self.first {
            println!(",");
        }
        self.first = false;
        print!("\"{}\": {}", k, raw);
    }
    fn map(&mut self, k: &str, items: Vec<(String, Vec<f64>)>) {
        let s: Vec<String> = items.iter().map(|(n, v)| format!("\"{}\": {}", n, arr(v))).collect();
        self.key(k, &format!("{{{}}}", s.join(", ")));
    }
    fn end(&self) {
        println!("\n}}");
    }
}

// ---------- 1. creation ----------
fn create_thread(n: usize) -> f64 {
    let t = Instant::now();
    for _ in 0..n {
        thread::spawn(|| {}).join().unwrap();
    }
    t.elapsed().as_secs_f64() / n as f64 * 1e6
}
fn create_fork(n: usize) -> f64 {
    let t = Instant::now();
    for _ in 0..n {
        let pid = unsafe { fork() };
        if pid == 0 {
            unsafe { _exit(0) }
        }
        reap(pid);
    }
    t.elapsed().as_secs_f64() / n as f64 * 1e6
}
fn create_spawn(n: usize) -> f64 {
    let t = Instant::now();
    for _ in 0..n {
        Command::new("/bin/true").status().unwrap();
    }
    t.elapsed().as_secs_f64() / n as f64 * 1e6
}
fn fork_vs_heap(mb: usize, n: usize) -> f64 {
    let mut v = vec![0u8; mb << 20];
    for i in (0..v.len()).step_by(4096) {
        v[i] = 1;
    }
    let r = create_fork(n);
    black_box(&v);
    r
}

// ---------- 2. CPU-bound ----------
fn work(iters: u64) {
    let mut x: u64 = 88172645463325252;
    let mut s: u64 = 0;
    for _ in 0..iters {
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        s = s.wrapping_add(x);
    }
    black_box(s);
}
fn cpu_threads(total: u64, w: usize) -> f64 {
    let t = Instant::now();
    let hs: Vec<_> = (0..w).map(|_| thread::spawn(move || work(total / w as u64))).collect();
    for h in hs {
        h.join().unwrap();
    }
    t.elapsed().as_secs_f64()
}
fn cpu_procs(total: u64, w: usize) -> f64 {
    let t = Instant::now();
    let mut pids = vec![];
    for _ in 0..w {
        let pid = unsafe { fork() };
        if pid == 0 {
            work(total / w as u64);
            unsafe { _exit(0) }
        }
        pids.push(pid);
    }
    for p in pids {
        reap(p);
    }
    t.elapsed().as_secs_f64()
}

// ---------- 3. memory ----------
fn status_kb(pid: &str, file: &str, key: &str) -> f64 {
    let s = fs::read_to_string(format!("/proc/{}/{}", pid, file)).unwrap_or_default();
    for l in s.lines() {
        if l.starts_with(key) {
            return l.split_whitespace().nth(1).unwrap().parse::<f64>().unwrap();
        }
    }
    0.0
}
fn pss(pid: &str) -> f64 {
    status_kb(pid, "smaps_rollup", "Pss:")
}
fn pte(pid: &str) -> f64 {
    status_kb(pid, "status", "VmPTE:")
}
fn tree(children: &[i32], f: fn(&str) -> f64) -> f64 {
    let mut t = f("self");
    for c in children {
        t += f(&c.to_string());
    }
    t
}
// returns (PSS KiB per worker, page-table KiB per worker)
fn mem_threads(n: usize) -> (f64, f64) {
    let (b0, p0) = (tree(&[], pss), tree(&[], pte));
    let b = Arc::new(Barrier::new(n + 1));
    let hs: Vec<_> = (0..n)
        .map(|_| {
            let b = b.clone();
            thread::spawn(move || {
                b.wait();
                b.wait();
            })
        })
        .collect();
    b.wait();
    thread::sleep(Duration::from_millis(100));
    let (b1, p1) = (tree(&[], pss), tree(&[], pte));
    b.wait();
    for h in hs {
        h.join().unwrap();
    }
    ((b1 - b0) / n as f64, (p1 - p0) / n as f64)
}
fn mem_procs(n: usize) -> (f64, f64) {
    let (b0, p0) = (tree(&[], pss), tree(&[], pte));
    let mut fds = [0i32; 2];
    unsafe { pipe(fds.as_mut_ptr()) };
    let mut pids = vec![];
    for _ in 0..n {
        let pid = unsafe { fork() };
        if pid == 0 {
            unsafe {
                close(fds[1]);
                let mut c = 0u8;
                read(fds[0], &mut c, 1);
                _exit(0)
            }
        }
        pids.push(pid);
    }
    thread::sleep(Duration::from_millis(200));
    let (b1, p1) = (tree(&pids, pss), tree(&pids, pte));
    unsafe { close(fds[1]) };
    for p in pids {
        reap(p);
    }
    ((b1 - b0) / n as f64, (p1 - p0) / n as f64)
}

// 64 MiB buffer, 8 workers: total PSS (MiB), read-only vs write every page
fn shared_buf(n: usize, writes: bool, procs: bool) -> f64 {
    let mut buf = vec![1u8; 64 << 20];
    for i in (0..buf.len()).step_by(4096) {
        buf[i] = 2;
    }
    if procs {
        let mut fds = [0i32; 2];
        unsafe { pipe(fds.as_mut_ptr()) };
        let mut pids = vec![];
        for _ in 0..n {
            let pid = unsafe { fork() };
            if pid == 0 {
                unsafe { close(fds[1]) };
                let mut s = 0u64;
                for i in (0..buf.len()).step_by(4096) {
                    if writes {
                        buf[i] = 9;
                    } else {
                        s += buf[i] as u64;
                    }
                }
                black_box(s);
                let mut c = 0u8;
                unsafe {
                    read(fds[0], &mut c, 1);
                    _exit(0)
                }
            }
            pids.push(pid);
        }
        thread::sleep(Duration::from_millis(800));
        let t = tree(&pids, pss) / 1024.0;
        unsafe { close(fds[1]) };
        for p in pids {
            reap(p);
        }
        t
    } else {
        let ptr = buf.as_mut_ptr() as usize;
        let len = buf.len();
        let b = Arc::new(Barrier::new(n + 1));
        let hs: Vec<_> = (0..n)
            .map(|k| {
                let b = b.clone();
                thread::spawn(move || {
                    let sl = unsafe { std::slice::from_raw_parts_mut(ptr as *mut u8, len) };
                    let mut s = 0u64;
                    for i in ((k * 4096)..len).step_by(4096 * n) {
                        if writes {
                            sl[i] = 9;
                        } else {
                            s += sl[i] as u64;
                        }
                    }
                    black_box(s);
                    b.wait();
                    b.wait();
                })
            })
            .collect();
        b.wait();
        thread::sleep(Duration::from_millis(200));
        let t = tree(&[], pss) / 1024.0;
        b.wait();
        for h in hs {
            h.join().unwrap();
        }
        t
    }
}

// ---------- 4. ping-pong with optional pinning and working set ----------
fn touch(b: &[u8]) -> u64 {
    let mut s = 0u64;
    for i in (0..b.len()).step_by(64) {
        s += b[i] as u64;
    }
    s
}
// threads share ONE buffer of ws bytes
fn pp_threads(n: usize, a: Option<usize>, b: Option<usize>, ws: usize) -> f64 {
    let buf = Arc::new(vec![1u8; ws.max(64)]);
    let (a_tx, a_rx) = mpsc::channel::<u8>();
    let (b_tx, b_rx) = mpsc::channel::<u8>();
    let bf = buf.clone();
    let h = thread::spawn(move || {
        if let Some(c) = b {
            pin(c);
        }
        for _ in 0..n {
            let v = a_rx.recv().unwrap();
            if ws > 0 {
                black_box(touch(&bf));
            }
            b_tx.send(v).unwrap();
        }
    });
    let saved = get_aff();
    if let Some(c) = a {
        pin(c);
    }
    let t = Instant::now();
    for _ in 0..n {
        a_tx.send(1).unwrap();
        b_rx.recv().unwrap();
        if ws > 0 {
            black_box(touch(&buf));
        }
    }
    let e = t.elapsed().as_secs_f64();
    h.join().unwrap();
    set_aff(&saved); // later experiments must see all CPUs again
    e / n as f64 * 1e6
}
// processes each own a private ws-byte buffer (copy-on-write broken by writing every page)
fn pp_procs(n: usize, a: Option<usize>, b: Option<usize>, ws: usize) -> f64 {
    let mut p2c = [0i32; 2];
    let mut c2p = [0i32; 2];
    unsafe {
        pipe(p2c.as_mut_ptr());
        pipe(c2p.as_mut_ptr());
    }
    let mut buf = vec![1u8; ws.max(64)];
    for i in (0..buf.len()).step_by(4096) {
        buf[i] = 2;
    }
    let pid = unsafe { fork() };
    if pid == 0 {
        if let Some(c) = b {
            pin(c);
        }
        for i in (0..buf.len()).step_by(4096) {
            buf[i] = 3; // private copy
        }
        let mut c = 0u8;
        for _ in 0..n {
            unsafe {
                read(p2c[0], &mut c, 1);
            }
            if ws > 0 {
                black_box(touch(&buf));
            }
            unsafe {
                write(c2p[1], &c, 1);
            }
        }
        unsafe { _exit(0) }
    }
    let saved = get_aff();
    if let Some(c) = a {
        pin(c);
    }
    let t = Instant::now();
    let mut c = 1u8;
    for _ in 0..n {
        unsafe {
            write(p2c[1], &c, 1);
            read(c2p[0], &mut c, 1);
        }
        if ws > 0 {
            black_box(touch(&buf));
        }
    }
    let e = t.elapsed().as_secs_f64();
    reap(pid);
    set_aff(&saved);
    e / n as f64 * 1e6
}

// ---------- 5. per-task creation vs pools ----------
fn iters_per_us() -> f64 {
    let n = 200_000_000u64;
    let t = Instant::now();
    work(n);
    n as f64 / (t.elapsed().as_secs_f64() * 1e6)
}
fn task_per_thread(n: usize, it: u64) -> f64 {
    let t = Instant::now();
    let mut left = n;
    while left > 0 {
        let b = left.min(W);
        let hs: Vec<_> = (0..b).map(|_| thread::spawn(move || work(it))).collect();
        for h in hs {
            h.join().unwrap();
        }
        left -= b;
    }
    t.elapsed().as_secs_f64()
}
fn task_per_fork(n: usize, it: u64) -> f64 {
    let t = Instant::now();
    let mut left = n;
    while left > 0 {
        let b = left.min(W);
        let mut pids = vec![];
        for _ in 0..b {
            let pid = unsafe { fork() };
            if pid == 0 {
                work(it);
                unsafe { _exit(0) }
            }
            pids.push(pid);
        }
        for p in pids {
            reap(p);
        }
        left -= b;
    }
    t.elapsed().as_secs_f64()
}
fn task_pool_threads(n: usize, it: u64) -> f64 {
    let t = Instant::now();
    let next = Arc::new(AtomicUsize::new(0));
    let hs: Vec<_> = (0..W)
        .map(|_| {
            let next = next.clone();
            thread::spawn(move || {
                while next.fetch_add(1, Ordering::Relaxed) < n {
                    work(it);
                }
            })
        })
        .collect();
    for h in hs {
        h.join().unwrap();
    }
    t.elapsed().as_secs_f64()
}
fn task_pool_procs(n: usize, it: u64) -> f64 {
    let t = Instant::now();
    let mut pids = vec![];
    for _ in 0..W {
        let pid = unsafe { fork() };
        if pid == 0 {
            for _ in 0..(n / W) {
                work(it);
            }
            unsafe { _exit(0) }
        }
        pids.push(pid);
    }
    for p in pids {
        reap(p);
    }
    t.elapsed().as_secs_f64()
}
fn task_rayon(pool: &rayon::ThreadPool, n: usize, it: u64) -> f64 {
    let t = Instant::now();
    pool.install(|| (0..n).into_par_iter().for_each(|_| work(it)));
    t.elapsed().as_secs_f64()
}

// ---------- 6. many concurrent sleepers ----------
fn sleepers_threads(c: usize, ms: u64) -> f64 {
    let t = Instant::now();
    let hs: Vec<_> = (0..c).map(|_| thread::spawn(move || thread::sleep(Duration::from_millis(ms)))).collect();
    for h in hs {
        h.join().unwrap();
    }
    t.elapsed().as_secs_f64()
}
fn sleepers_procs(c: usize, ms: u64) -> f64 {
    let t = Instant::now();
    let mut pids = vec![];
    for _ in 0..c {
        let pid = unsafe { fork() };
        if pid == 0 {
            thread::sleep(Duration::from_millis(ms));
            unsafe { _exit(0) }
        }
        pids.push(pid);
    }
    for p in pids {
        reap(p);
    }
    t.elapsed().as_secs_f64()
}
fn sleepers_tokio(rt: &tokio::runtime::Runtime, c: usize, ms: u64) -> f64 {
    let t = Instant::now();
    rt.block_on(async {
        let hs: Vec<_> = (0..c).map(|_| tokio::spawn(tokio::time::sleep(Duration::from_millis(ms)))).collect();
        for h in hs {
            h.await.unwrap();
        }
    });
    t.elapsed().as_secs_f64()
}

// ---------- 7. follow-up experiments (added after the audit) ----------
// thread spawn and fork measured in the same run, with a parent that holds `mb` MiB of touched heap
fn heap_pair(mb: usize) -> (f64, f64) {
    let mut v = vec![0u8; mb << 20];
    for i in (0..v.len()).step_by(4096) {
        v[i] = 1;
    }
    let t = create_thread(500);
    let f = create_fork(50);
    black_box(&v);
    (t, f)
}

// fork latency while `live` children are already alive and asleep
fn fork_live(live: usize) -> f64 {
    let mut fds = [0i32; 2];
    unsafe { pipe(fds.as_mut_ptr()) };
    let mut pids = vec![];
    for _ in 0..live {
        let pid = unsafe { fork() };
        if pid == 0 {
            unsafe {
                close(fds[1]);
                let mut c = 0u8;
                read(fds[0], &mut c, 1);
                _exit(0)
            }
        }
        pids.push(pid);
    }
    thread::sleep(Duration::from_millis(100));
    let r = create_fork(100);
    unsafe { close(fds[1]) };
    for p in pids {
        reap(p);
    }
    r
}

// process pool where every task is handed over through a pipe (real inter-process communication)
fn task_pool_procs_ipc(n: usize, it: u64) -> f64 {
    let t = Instant::now();
    let mut fds = [0i32; 2];
    unsafe { pipe(fds.as_mut_ptr()) };
    let mut pids = vec![];
    for _ in 0..W {
        let pid = unsafe { fork() };
        if pid == 0 {
            unsafe { close(fds[1]) };
            let mut c = 0u8;
            loop {
                let k = unsafe { read(fds[0], &mut c, 1) };
                if k <= 0 {
                    break;
                }
                work(it);
            }
            unsafe { _exit(0) }
        }
        pids.push(pid);
    }
    unsafe { close(fds[0]) };
    let buf = vec![1u8; n];
    let mut sent = 0;
    while sent < n {
        let k = unsafe { write(fds[1], buf.as_ptr().add(sent), n - sent) };
        if k <= 0 {
            break;
        }
        sent += k as usize;
    }
    unsafe { close(fds[1]) };
    for p in pids {
        reap(p);
    }
    t.elapsed().as_secs_f64()
}

// thread hand-off with park/unpark (futex-based) instead of a channel
fn pp_threads_park(n: usize, a: Option<usize>, b: Option<usize>) -> f64 {
    use std::sync::atomic::AtomicU32;
    let turn = Arc::new(AtomicU32::new(0));
    let main_t = thread::current();
    let t2 = turn.clone();
    let h = thread::spawn(move || {
        if let Some(c) = b {
            pin(c);
        }
        for _ in 0..n {
            while t2.load(Ordering::Acquire) != 1 {
                thread::park();
            }
            t2.store(0, Ordering::Release);
            main_t.unpark();
        }
    });
    let saved = get_aff();
    if let Some(c) = a {
        pin(c);
    }
    let t = Instant::now();
    for _ in 0..n {
        turn.store(1, Ordering::Release);
        h.thread().unpark();
        while turn.load(Ordering::Acquire) != 0 {
            thread::park();
        }
    }
    let e = t.elapsed().as_secs_f64();
    h.join().unwrap();
    set_aff(&saved);
    e / n as f64 * 1e6
}

// speed of one worker pinned to a single logical CPU (finds slower cores)
fn pinned_speed(cpu: usize, iters: u64) -> f64 {
    let saved = get_aff();
    pin(cpu);
    let t = Instant::now();
    work(iters);
    let e = t.elapsed().as_secs_f64();
    set_aff(&saved);
    e
}

// threads and processes alternated in the same loop so order and drift do not favour one side
fn cpu_interleaved(total: u64, w: usize, n: usize) -> (Vec<f64>, Vec<f64>) {
    let (mut a, mut b) = (vec![], vec![]);
    for _ in 0..n {
        a.push(cpu_threads(total, w));
        b.push(cpu_procs(total, w));
    }
    (a, b)
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let want = |s: &str| args.is_empty() || args.iter().any(|a| a == s);
    let ncpu = thread::available_parallelism().unwrap().get();
    let mut o = Out::new();
    o.key("ncpu", &ncpu.to_string());
    o.key("rustc", "\"1.99.0\"");

    if want("create") {
    o.map(
        "create_us",
        vec![
            ("thread".into(), reps(20, || create_thread(2000))),
            ("fork".into(), reps(20, || create_fork(1000))),
            ("fork_exec".into(), reps(20, || create_spawn(300))),
        ],
    );
    let heaps = [0usize, 64, 256, 1024];
    o.map(
        "fork_vs_heap_mb_us",
        heaps.iter().map(|&m| (m.to_string(), reps(10, || fork_vs_heap(m, 50)))).collect(),
    );
    }

    // 2 CPU
    if want("cpu") {
    let total: u64 = 2_000_000_000;
    let ws = [1usize, 2, 4, 8, 12, 16, 24, 32];
    o.map("cpu_threads_s", ws.iter().map(|&w| (w.to_string(), reps(10, || cpu_threads(total, w)))).collect());
    o.map("cpu_procs_s", ws.iter().map(|&w| (w.to_string(), reps(10, || cpu_procs(total, w)))).collect());
    }

    // 3 memory
    if want("mem") {
    let ns = [1usize, 10, 50, 100, 500];
    let mt: Vec<(usize, Vec<(f64, f64)>)> = ns.iter().map(|&n| (n, reps_pair(7, || mem_threads(n)))).collect();
    let mp: Vec<(usize, Vec<(f64, f64)>)> = ns.iter().map(|&n| (n, reps_pair(7, || mem_procs(n)))).collect();
    o.map("mem_thread_pss_kib_each", mt.iter().map(|(n, v)| (n.to_string(), v.iter().map(|p| p.0).collect())).collect());
    o.map("mem_thread_pte_kib_each", mt.iter().map(|(n, v)| (n.to_string(), v.iter().map(|p| p.1).collect())).collect());
    o.map("mem_proc_pss_kib_each", mp.iter().map(|(n, v)| (n.to_string(), v.iter().map(|p| p.0).collect())).collect());
    o.map("mem_proc_pte_kib_each", mp.iter().map(|(n, v)| (n.to_string(), v.iter().map(|p| p.1).collect())).collect());
    o.map(
        "shared64_total_pss_mib",
        vec![
            ("thread_read".into(), reps(7, || shared_buf(8, false, false))),
            ("thread_write".into(), reps(7, || shared_buf(8, true, false))),
            ("proc_read".into(), reps(7, || shared_buf(8, false, true))),
            ("proc_write".into(), reps(7, || shared_buf(8, true, true))),
        ],
    );
    }

    // 4 ping-pong: pinning variants (no working set)
    if want("pingpong") {
    let n = 30000;
    o.map(
        "pingpong_us",
        vec![
            ("thread_unpinned".into(), reps(10, || pp_threads(n, None, None, 0))),
            ("proc_unpinned".into(), reps(10, || pp_procs(n, None, None, 0))),
            ("thread_same_core".into(), reps(10, || pp_threads(n, Some(0), Some(0), 0))),
            ("proc_same_core".into(), reps(10, || pp_procs(n, Some(0), Some(0), 0))),
            ("thread_diff_core".into(), reps(10, || pp_threads(n, Some(0), Some(2), 0))),
            ("proc_diff_core".into(), reps(10, || pp_procs(n, Some(0), Some(2), 0))),
        ],
    );
    }
    // 4b working-set switching cost, same core
    if want("switch") {
    let wss: [usize; 6] = [0, 32 << 10, 256 << 10, 2 << 20, 8 << 20, 16 << 20];
    let nn = |w: usize| if w <= (32 << 10) { 20000 } else if w <= (256 << 10) { 5000 } else { 800 };
    o.map(
        "switch_ws_thread_us",
        wss.iter().map(|&w| (w.to_string(), reps(7, || pp_threads(nn(w), Some(0), Some(0), w)))).collect(),
    );
    o.map(
        "switch_ws_proc_us",
        wss.iter().map(|&w| (w.to_string(), reps(7, || pp_procs(nn(w), Some(0), Some(0), w)))).collect(),
    );
    }

    // 5 per-task creation vs pools (the Rayon pool is built last so its threads do not exist while forking)
    if want("pool") {
    let ipu = iters_per_us();
    o.key("iters_per_us", &format!("{:.2}", ipu));
    let mut pool: Option<rayon::ThreadPool> = None;
    let ds: [(u64, usize); 5] = [(0, 24000), (10, 24000), (100, 24000), (1000, 4800), (10000, 960)];
    let mut modes: Vec<(String, Vec<(String, Vec<f64>)>)> = vec![];
    for name in ["per_thread", "per_fork", "pool_threads", "pool_procs", "rayon"] {
        let mut v = vec![];
        for &(d, n) in ds.iter() {
            let it = (d as f64 * ipu) as u64;
            let s = match name {
                "per_thread" => reps(7, || task_per_thread(n, it)),
                "per_fork" => reps(7, || task_per_fork(n, it)),
                "pool_threads" => reps(7, || task_pool_threads(n, it)),
                "pool_procs" => reps(7, || task_pool_procs(n, it)),
                _ => {
                    if pool.is_none() {
                        pool = Some(rayon::ThreadPoolBuilder::new().num_threads(W).build().unwrap());
                    }
                    let p = pool.as_ref().unwrap();
                    reps(7, || task_rayon(p, n, it))
                }
            };
            v.push((format!("{}", d), s));
        }
        modes.push((name.to_string(), v));
    }
    let tasks: Vec<String> = ds.iter().map(|(d, n)| format!("\"{}\": {}", d, n)).collect();
    o.key("task_counts", &format!("{{{}}}", tasks.join(", ")));
    for (name, v) in modes {
        o.map(&format!("task_{}_s", name), v);
    }
    }

    // 6 many concurrent sleepers (100 ms)
    if want("sleepers") {
    let rt = tokio::runtime::Builder::new_multi_thread().worker_threads(W).enable_time().build().unwrap();
    let cs = [100usize, 1000, 5000, 10000];
    o.map("sleepers_threads_s", cs.iter().map(|&c| (c.to_string(), reps(5, || sleepers_threads(c, 100)))).collect());
    o.map("sleepers_tokio_s", cs.iter().map(|&c| (c.to_string(), reps(5, || sleepers_tokio(&rt, c, 100)))).collect());
    o.map(
        "sleepers_procs_s",
        [100usize, 500, 1000].iter().map(|&c| (c.to_string(), reps(5, || sleepers_procs(c, 100)))).collect(),
    );
    }

    // 7 follow-up experiments from the audit
    if want("heap_thread") {
        let sizes = [0usize, 64, 256, 1024];
        let mut tt: Vec<(String, Vec<f64>)> = vec![];
        let mut ff: Vec<(String, Vec<f64>)> = vec![];
        for &m in sizes.iter() {
            let r: Vec<(f64, f64)> = (0..10).map(|_| heap_pair(m)).collect();
            tt.push((m.to_string(), r.iter().map(|p| p.0).collect()));
            ff.push((m.to_string(), r.iter().map(|p| p.1).collect()));
        }
        o.map("heap_thread_spawn_us", tt);
        o.map("heap_fork_us", ff);
    }
    if want("cpu2") {
        let total: u64 = 1_000_000_000;
        let ws = [4usize, 8, 12, 16, 24];
        let mut t: Vec<(String, Vec<f64>)> = vec![];
        let mut p: Vec<(String, Vec<f64>)> = vec![];
        for &w in ws.iter() {
            let (a, b) = cpu_interleaved(total, w, 30);
            t.push((w.to_string(), a));
            p.push((w.to_string(), b));
        }
        o.map("cpu2_threads_s", t);
        o.map("cpu2_procs_s", p);
    }
    if want("fork_live") {
        o.map(
            "fork_live_us",
            [0usize, 100, 500, 1000].iter().map(|&n| (n.to_string(), reps(5, || fork_live(n)))).collect(),
        );
    }
    if want("pool_ipc") {
        let ipu = iters_per_us();
        let ds: [(u64, usize); 4] = [(10, 24000), (100, 24000), (1000, 4800), (10000, 960)];
        o.map(
            "task_pool_procs_ipc_s",
            ds.iter().map(|&(d, n)| (d.to_string(), reps(7, || task_pool_procs_ipc(n, (d as f64 * ipu) as u64)))).collect(),
        );
    }
    if want("park") {
        let n = 30000;
        o.map(
            "pingpong_park_us",
            vec![
                ("thread_unpinned".into(), reps(10, || pp_threads_park(n, None, None))),
                ("thread_same_core".into(), reps(10, || pp_threads_park(n, Some(0), Some(0)))),
                ("thread_diff_core".into(), reps(10, || pp_threads_park(n, Some(0), Some(2)))),
            ],
        );
    }
    if want("topo") {
        let cpus = [0usize, 1, 2, 8, 15, 16, 20, 23];
        o.map("pinned_speed_s", cpus.iter().map(|&c| (c.to_string(), reps(5, || pinned_speed(c, 500_000_000)))).collect());
    }
    o.end();
}

fn reps_pair<F: FnMut() -> (f64, f64)>(n: usize, mut f: F) -> Vec<(f64, f64)> {
    (0..n).map(|_| f()).collect()
}
