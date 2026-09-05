"""One paper-trade session tick. PAPER ONLY. Equities desk."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engine import DATA_PATH, STARTING_CASH, PaperBroker
from quotes import DEFAULT_UNIVERSE, fetch_quotes
from strategy import signals

ROOT = Path(__file__).resolve().parent


def parse_universe(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_UNIVERSE)
    return [part.strip().upper() for part in raw.split(",") if part.strip()]


def run_tick(cash: float = STARTING_CASH, universe: list[str] | None = None, data_path: Path | None = None) -> dict:
    book = PaperBroker.load(path=data_path or DATA_PATH, cash=cash)
    names = universe or list(DEFAULT_UNIVERSE)
    quotes = fetch_quotes(names)
    errors = quotes.pop("_errors", None)
    book.mark(quotes)
    if errors:
        book.note("quote", f"quote misses: {', '.join(sorted((errors.get('items') or {}).keys()))}")
    else:
        book.note("quote", f"quote sweep {len(quotes)} names")
    for order in signals(quotes, book.positions, book.equity()):
        book.market_order(order["symbol"], order["qty"], order["last"], order.get("reason") or "")
    book.mark(quotes)
    path = book.save()
    snap = book.snapshot()
    snap["data_path"] = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    return snap


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one PAPER equities session tick.")
    parser.add_argument("--cash", type=float, default=STARTING_CASH)
    parser.add_argument("--universe", default=",".join(DEFAULT_UNIVERSE))
    parser.add_argument("--data", default=str(DATA_PATH))
    args = parser.parse_args(argv)
    snap = run_tick(cash=args.cash, universe=parse_universe(args.universe), data_path=Path(args.data))
    print(
        json.dumps(
            {
                "mode": snap["mode"],
                "version": snap["version"],
                "equity": round(snap["equity"], 2),
                "cash": round(snap["cash"], 2),
                "pnl": round(snap["pnl"], 2),
                "positions": len(snap["positions"]),
                "updated_at": snap["updated_at"],
                "data_path": snap["data_path"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
