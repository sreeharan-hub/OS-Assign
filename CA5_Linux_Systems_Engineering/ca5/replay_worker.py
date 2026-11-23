"""One measured replay in a fresh process (so each run starts from the same interpreter state).

usage: python ca5/replay_worker.py PATTERN SEED POLICY MEM_PCT [--rss N]   ->  one JSON line on stdout
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src")]
import pager  # noqa: E402
import procinfo  # noqa: E402
import simulator as S  # noqa: E402
import traces  # noqa: E402
from common import frames_for  # noqa: E402


def main():
    pattern, seed, policy, mem = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
    rss_every = int(sys.argv[sys.argv.index("--rss") + 1]) if "--rss" in sys.argv else 0
    raw = S.dedup(traces.build(pattern, seed=seed))
    trace, fp = pager.relabel(raw)
    frames = frames_for(fp, mem)
    victims, predicted = pager.POLICY_FN[policy](trace, frames)
    assert predicted == S.simulate(policy, raw, frames), "pager policy disagrees with the simulator"
    r = pager.replay(trace, victims, fp, rss_every)
    r.update(pattern=pattern, seed=seed, policy=policy, mem=mem, frames=frames, footprint=fp, refs=len(trace),
             predicted=predicted, evictions=sum(1 for v in victims if v >= 0), majflt=procinfo.read_stat()["majflt"],
             total_minflt=procinfo.minflt())
    print(json.dumps(r))


if __name__ == "__main__":
    main()
