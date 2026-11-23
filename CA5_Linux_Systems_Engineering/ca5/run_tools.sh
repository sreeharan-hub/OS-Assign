#!/usr/bin/env bash
# CA-5 Linux toolchain evidence (Bash orchestration).  Output: ca5/results/tools_output.txt
# Everything runs on processes created here; nothing system-wide is changed.
set -u
cd "$(dirname "$0")/.."
OUT=ca5/results/tools_output.txt
{
echo "### lscpu (CPU topology)";            lscpu | grep -E "^(Architecture|CPU\(s\)|Model name|Thread|Core|Socket|L2|L3)"
echo; echo "### free -m (before)";           free -m
echo; echo "### page size / THP";            getconf PAGESIZE; cat /sys/kernel/mm/transparent_hugepage/enabled
echo; echo "### taskset: affinity of this shell"; taskset -p $$
echo; echo "### vmstat 1 11 while ca5/hold_memory.py touches, holds and releases ~195 MiB"
python3 ca5/hold_memory.py > /dev/null &
HP=$!
vmstat 1 11
wait $HP
echo; echo "### ps -o for a controlled child (sleep 5) : state, PPID, faults, RSS"
sleep 5 & CP=$!
ps -o pid,ppid,stat,min_flt,maj_flt,nlwp,rss,vsz,comm -p $CP
echo; echo "### process explorer (ca5/procinfo.py): this shell and its ancestors"
python3 ca5/procinfo.py $$ $PPID 1
echo; echo "### /proc/vmstat pgfault / pgmajfault (system-wide counters)"
grep -E "^(pgfault|pgmajfault) " /proc/vmstat
wait $CP
} > "$OUT" 2>&1
echo "wrote $OUT"
