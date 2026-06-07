"""
Daily seed runner for cron.

Reads the first domain from seed_list.txt, runs the outreach pipeline with
--skip-confirm, and removes the seed only after a successful run.
"""

import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SEED_LIST = ROOT / "seed_list.txt"
LOCK_FILE = ROOT / "data" / "run_daily.lock"
LOCK_MAX_AGE_SECONDS = 6 * 60 * 60


def _read_seeds() -> list[str]:
    if not SEED_LIST.exists():
        raise FileNotFoundError(f"Missing seed list: {SEED_LIST}")
    return [
        line.strip()
        for line in SEED_LIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _write_seeds(seeds: list[str]) -> None:
    SEED_LIST.write_text("\n".join(seeds) + ("\n" if seeds else ""), encoding="utf-8")


def _acquire_lock() -> bool:
    LOCK_FILE.parent.mkdir(exist_ok=True)
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        age = time.time() - LOCK_FILE.stat().st_mtime
        if age < LOCK_MAX_AGE_SECONDS:
            print("Another daily pipeline run appears to be active.")
            return False
        LOCK_FILE.unlink()
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)

    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(str(time.time()))
    return True


def _release_lock() -> None:
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


def main() -> int:
    if not _acquire_lock():
        return 1

    try:
        seeds = _read_seeds()
        if not seeds:
            print("No seed domains left in seed_list.txt.")
            return 0

        seed = seeds[0]
        cmd = [sys.executable, str(ROOT / "main.py"), seed, "--skip-confirm"]
        result = subprocess.run(cmd, cwd=ROOT, check=False)
        if result.returncode != 0:
            return result.returncode

        _write_seeds(seeds[1:])
        return 0
    finally:
        _release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
