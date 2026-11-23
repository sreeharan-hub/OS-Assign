"""CA-5 instrument (L25): a small /proc process explorer.

    python ca5/procinfo.py            # table of the current process and its ancestors
    python ca5/procinfo.py 1 <pid>    # selected PIDs

Reads /proc/<pid>/stat, /proc/<pid>/status and /proc/<pid>/statm.  No third-party packages.
"""
import os
import sys

PAGE = os.sysconf("SC_PAGE_SIZE")
CLK = os.sysconf("SC_CLK_TCK")


def read_stat(pid="self"):
    """Fields of /proc/<pid>/stat as a dict (the command name may contain spaces and parentheses)."""
    raw = open(f"/proc/{pid}/stat").read()
    pid_s, rest = raw.split(" ", 1)
    comm, tail = rest[1:].rsplit(")", 1)
    f = tail.split()
    return dict(pid=int(pid_s), comm=comm, state=f[0], ppid=int(f[1]), minflt=int(f[7]), majflt=int(f[9]),
                utime=int(f[11]) / CLK, stime=int(f[12]) / CLK, nice=int(f[16]), threads=int(f[17]),
                vsize=int(f[20]), rss_pages=int(f[21]))


def read_status(pid="self"):
    out = {}
    for line in open(f"/proc/{pid}/status"):
        k, _, v = line.partition(":")
        out[k] = v.strip()
    return out


def read_statm(pid="self"):
    size, resident, shared, *_ = (int(x) for x in open(f"/proc/{pid}/statm").read().split())
    return dict(size_pages=size, resident_pages=resident, shared_pages=shared)


def minflt(pid="self"):
    return read_stat(pid)["minflt"]


def vmstat_pgfault():
    for line in open("/proc/vmstat"):
        if line.startswith("pgfault "):
            return int(line.split()[1])
    raise RuntimeError("pgfault not in /proc/vmstat")


def cmdline(pid):
    try:
        return open(f"/proc/{pid}/cmdline").read().replace("\0", " ").strip()
    except OSError:
        return ""


def snapshot(pid="self"):
    s, st, m = read_stat(pid), read_status(pid), read_statm(pid)
    s.update(m)
    s["vmrss_kb"] = int(st.get("VmRSS", "0 kB").split()[0])
    s["cmd"] = cmdline(s["pid"])
    return s


def main(argv):
    pids = argv or None
    if pids is None:                                     # current process and its ancestors
        chain, p = [], os.getpid()
        while p > 0:
            chain.append(p)
            p = read_stat(p)["ppid"]
        pids = chain
    print(f"{'PID':>6} {'PPID':>6} {'S':1} {'MINFLT':>8} {'MAJFLT':>7} {'THR':>3} {'RSS(KiB)':>9} {'VSZ(KiB)':>9}  COMMAND")
    for p in pids:
        try:
            s = snapshot(p)
        except (OSError, ValueError):
            continue
        print(f"{s['pid']:>6} {s['ppid']:>6} {s['state']:1} {s['minflt']:>8} {s['majflt']:>7} {s['threads']:>3} "
              f"{s['vmrss_kb']:>9} {s['vsize'] // 1024:>9}  {s['cmd'][:48] or s['comm']}")


if __name__ == "__main__":
    main(sys.argv[1:])
