#!/usr/bin/env python3
"""Run the whole CA-2 pipeline end to end:

    python run_all.py            # tests -> experiments -> analysis -> report
    python run_all.py --quick    # skip the heavy sweeps (for a smoke test)

Every step writes raw CSVs to results/ so nothing is lost.  Timing numbers are
machine-specific, so run this on YOUR machine and with nothing else heavy
running; the fault counts are deterministic and will match across machines.
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

STEPS = [
    ("unit tests", [PY, "-m", "unittest", "discover", "-s", "tests"]),
    ("environment", [PY, "-I", "experiments/make_env.py"]),
    ("main experiment", [PY, "-I", "experiments/run_main.py"]),
    ("reuse distance + cross-check", [PY, "-I", "experiments/run_reuse.py"]),
    ("Belady's anomaly", [PY, "-I", "experiments/run_belady.py"]),
    ("sensitivity sweeps", [PY, "-I", "experiments/run_sweeps.py"]),
    ("matmul knee", [PY, "-I", "experiments/run_knee.py"]),
    ("timing (leave the machine idle)", [PY, "-I", "experiments/run_timing.py"]),
    ("analysis, tables, figures", [PY, "-I", "experiments/analyze.py"]),
    ("report", [PY, "-I", "experiments/build_report.py"]),
]
QUICK_SKIP = {"sensitivity sweeps", "matmul knee"}


def main():
    quick = "--quick" in sys.argv
    t_all = time.time()
    for name, cmd in STEPS:
        if quick and name in QUICK_SKIP:
            print(f"[skip] {name}")
            continue
        print(f"\n=== {name} ===", flush=True)
        t0 = time.time()
        r = subprocess.run(cmd, cwd=ROOT)
        if r.returncode != 0:
            print(f"FAILED: {name}")
            sys.exit(r.returncode)
        print(f"({time.time() - t0:.1f}s)")
    print(f"\nAll done in {time.time() - t_all:.0f}s.  Open docs/CA2_Report.md "
          f"(and docs/CA2_Report.docx if pandoc is installed).")


if __name__ == "__main__":
    main()
