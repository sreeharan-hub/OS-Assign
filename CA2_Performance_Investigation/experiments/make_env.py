"""Record the experimental environment (CA-2 reproducibility requirement)."""
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from common import RESULTS, ROOT  # noqa: E402


def cpu_model():
    try:
        for line in open("/proc/cpuinfo"):
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def ram_gb():
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemTotal"):
                return round(int(line.split()[1]) / 1024 / 1024, 1)
    except OSError:
        pass
    return None


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "not a git checkout"


def main():
    import matplotlib
    import numpy
    import pandas
    import scipy
    env = {
        "date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "cpu": cpu_model(),
        "logical_cores": os.cpu_count(),
        "ram_gb": ram_gb(),
        "numpy": numpy.__version__, "scipy": scipy.__version__,
        "matplotlib": matplotlib.__version__, "pandas": pandas.__version__,
        "git_commit": git_commit(),
    }
    (RESULTS / "environment.json").write_text(json.dumps(env, indent=2) + "\n")
    print(json.dumps(env, indent=2))


if __name__ == "__main__":
    main()
