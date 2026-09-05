"""Cross-sectional momentum for the equities paper desk. PAPER ONLY."""

from __future__ import annotations

from typing import Any

# Long the strongest 20-session momentum names. Flatten faded names.
LOOKBACK_KEY = "momentum_20d"
LONG_COUNT = 4
ENTRY_MIN = 0.02
EXIT_BELOW = 0.0
WEIGHT = 0.18


def rank_momentum(quotes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol, row in quotes.items():
        if symbol.startswith("_") or not isinstance(row, dict):
            continue
        last = float(row.get("last") or 0.0)
        mom = float(row.get(LOOKBACK_KEY) or 0.0)
        if last <= 0:
            continue
        rows.append({"symbol": symbol.upper(), "last": last, "momentum": mom})
    rows.sort(key=lambda item: item["momentum"], reverse=True)
    return rows


def signals(
    quotes: dict[str, dict[str, Any]],
    positions: dict[str, dict[str, Any]] | None = None,
    equity: float = 0.0,
) -> list[dict[str, Any]]:
    """Return paper orders: BUY strongest momentum, SELL faded holdings."""
    held = {str(k).upper(): dict(v) for k, v in (positions or {}).items()}
    ranked = rank_momentum(quotes)
    if not ranked or equity <= 0:
        return []
    longs = [row for row in ranked if row["momentum"] >= ENTRY_MIN][:LONG_COUNT]
    long_set = {row["symbol"] for row in longs}
    orders: list[dict[str, Any]] = []

    for symbol, pos in held.items():
        qty = float(pos.get("qty") or 0.0)
        last = float((quotes.get(symbol) or {}).get("last") or pos.get("last") or 0.0)
        mom = float((quotes.get(symbol) or {}).get(LOOKBACK_KEY) or 0.0)
        if qty > 0 and last > 0 and (symbol not in long_set or mom < EXIT_BELOW):
            orders.append(
                {
                    "symbol": symbol,
                    "qty": -qty,
                    "last": last,
                    "reason": f"momentum_exit mom={mom:+.3f}",
                }
            )

    target_notional = equity * WEIGHT
    for row in longs:
        symbol = row["symbol"]
        last = row["last"]
        cur_qty = float((held.get(symbol) or {}).get("qty") or 0.0)
        cur_mkt = cur_qty * last
        if cur_mkt >= target_notional * 0.85:
            continue
        need = target_notional - cur_mkt
        qty = need / last
        if qty * last < 25:
            continue
        orders.append(
            {
                "symbol": symbol,
                "qty": qty,
                "last": last,
                "reason": f"momentum_entry mom={row['momentum']:+.3f}",
            }
        )
    return orders
