"""Repeat paper-trade ticks. PAPER ONLY. Writes session.pid (gitignored)."""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from pathlib import Path

from engine import DATA_PATH, STARTING_CASH
from quotes import DEFAULT_UNIVERSE
from run_session import parse_universe, run_tick

ROOT = Path(__file__).resolve().parent
PID_PATH = ROOT / "session.pid"

_stop = False


def _handle_stop(signum: int, _frame: object) -> None:
    global _stop
    _stop = True
    print(f"stop signal {signum}", flush=True)


def write_pid(path: Path) -> None:
    path.write_text(str(os.getpid()), encoding="utf-8")


def clear_pid(path: Path) -> None:
    try:
        if path.exists() and path.read_text(encoding="utf-8").strip() == str(os.getpid()):
            path.unlink()
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Loop PAPER equities session ticks.")
    parser.add_argument("--interval", type=float, default=60.0, help="Seconds between ticks.")
    parser.add_argument("--cash", type=float, default=STARTING_CASH)
    parser.add_argument("--universe", default=",".join(DEFAULT_UNIVERSE))
    parser.add_argument("--data", default=str(DATA_PATH))
    parser.add_argument("--pid", default=str(PID_PATH))
    args = parser.parse_args(argv)

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)
    pid_path = Path(args.pid)
    write_pid(pid_path)
    universe = parse_universe(args.universe)
    print(f"PAPER loop start pid={os.getpid()} interval={args.interval}s", flush=True)
    try:
        while not _stop:
            snap = run_tick(cash=args.cash, universe=universe, data_path=Path(args.data))
            print(
                f"{snap['updated_at']} equity={snap['equity']:.2f} pnl={snap['pnl']:+.2f} "
                f"pos={len(snap['positions'])}",
                flush=True,
            )
            deadline = time.time() + max(1.0, args.interval)
            while not _stop and time.time() < deadline:
                time.sleep(0.25)
    finally:
        clear_pid(pid_path)
        print("PAPER loop stop", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
