"""Continuous CRYPTO PAPER loop. Writes session.pid (gitignored). PAPER ONLY."""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path

from engine import DATA_PATH, STARTING_CASH, PaperBroker
from quotes import DEFAULT_UNIVERSE, fetch_quotes
from strategy import signals
from sync_dashboard import sync

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


def parse_universe(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_UNIVERSE)
    return [part.strip().upper() for part in raw.split(",") if part.strip()]


def run_tick(cash: float = STARTING_CASH, universe: list[str] | None = None, data_path: Path | None = None) -> dict:
    book = PaperBroker.load(path=data_path or DATA_PATH, cash=cash)
    names = universe or list(DEFAULT_UNIVERSE)
    book.universe = list(names)
    quotes = fetch_quotes(names)
    source = quotes.pop("_source", None)
    errors = quotes.pop("_errors", None)
    if isinstance(source, str):
        book.quote_source = source
    book.mark(quotes)
    if errors:
        book.note("quote", f"quote misses: {', '.join(sorted((errors.get('items') or {}).keys()))}")
    else:
        book.note("quote", f"quote sweep {len(quotes)} names src={book.quote_source}")
    for order in signals(quotes, book.positions, book.equity(), book.cash):
        book.market_order(
            order["symbol"],
            order["qty"],
            order["last"],
            order.get("reason") or "",
            note=order.get("note") or "",
        )
    book.mark(quotes)
    path = book.save()
    snap = book.snapshot()
    snap["data_path"] = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    return snap


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Loop CRYPTO PAPER session ticks (24/7).")
    parser.add_argument("--interval", type=float, default=60.0, help="Seconds between ticks.")
    parser.add_argument("--cash", type=float, default=STARTING_CASH)
    parser.add_argument("--universe", default=",".join(DEFAULT_UNIVERSE))
    parser.add_argument("--data", default=str(DATA_PATH))
    parser.add_argument("--pid", default=str(PID_PATH))
    parser.add_argument("--once", action="store_true", help="Run a single tick then exit.")
    parser.add_argument("--sync", action="store_true", default=True, help="Write dashboard/data.json after each tick.")
    parser.add_argument("--no-sync", dest="sync", action="store_false")
    parser.add_argument("--republish", action="store_true", help="Optional here.now republish after sync.")
    args = parser.parse_args(argv)

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)
    pid_path = Path(args.pid)
    write_pid(pid_path)
    universe = parse_universe(args.universe)
    print(f"CRYPTO PAPER loop start pid={os.getpid()} interval={args.interval}s", flush=True)
    try:
        while not _stop:
            snap = run_tick(cash=args.cash, universe=universe, data_path=Path(args.data))
            if args.sync:
                dest = sync(Path(args.data), republish=args.republish)
                snap["dashboard"] = str(dest)
            print(
                json.dumps(
                    {
                        "updated_at": snap["updated_at"],
                        "equity": round(float(snap["equity"]), 4),
                        "pnl": round(float(snap["pnl"]), 4),
                        "positions": len(snap["positions"]),
                        "quote_source": snap.get("quote_source"),
                    }
                ),
                flush=True,
            )
            if args.once:
                break
            deadline = time.time() + max(1.0, args.interval)
            while not _stop and time.time() < deadline:
                time.sleep(0.25)
    finally:
        clear_pid(pid_path)
        print("CRYPTO PAPER loop stop", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
