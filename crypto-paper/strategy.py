"""Aggressive crypto momentum/breakout. Concentrated size. PAPER ONLY."""

from __future__ import annotations

from typing import Any

# Hunt the strongest 24h + hourly momentum names. Size up into 1-2 slots.
CASH_RESERVE = 2.0
PRIMARY_FRAC = 0.92
SECONDARY_FRAC = 0.08
MAX_NAMES = 2
ENTRY_SCORE = -0.15
EXIT_SCORE = -1.25
MIN_NOTIONAL = 5.0


def _num(row: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if row.get(key) is not None:
            try:
                return float(row[key])
            except (TypeError, ValueError):
                continue
    return default


def _metrics(row: dict[str, Any]) -> tuple[float, float, float, float]:
    last = _num(row, "last")
    day = _num(row, "day_pct")
    if day == 0.0 and row.get("change_pct") is not None:
        raw = _num(row, "change_pct")
        day = raw * 100.0 if abs(raw) <= 2 else raw
    mom = _num(row, "momentum", "momentum_20d")
    if abs(mom) <= 2 and "momentum_20d" in row and "momentum" not in row:
        mom = mom * 100.0
    bo = _num(row, "breakout")
    return last, day, mom, bo


def score_row(row: dict[str, Any]) -> dict[str, Any]:
    last, day, mom, bo = _metrics(row)
    score = (day * 0.55) + (mom * 0.35) + (bo * 0.10)
    return {
        "symbol": str(row.get("symbol") or "").upper(),
        "last": last,
        "day": day,
        "mom": mom,
        "bo": bo,
        "score": score,
        "note": f"breakout/mom day={day:.2f}% mom={mom:.2f}% bo={bo:.2f}%",
    }


def rank(quotes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol, row in quotes.items():
        if symbol.startswith("_") or not isinstance(row, dict):
            continue
        item = score_row({**row, "symbol": row.get("symbol") or symbol})
        if item["last"] <= 0 or not item["symbol"]:
            continue
        rows.append(item)
    rows.sort(key=lambda item: item["score"], reverse=True)
    return rows


def signals(
    quotes: dict[str, dict[str, Any]],
    positions: dict[str, dict[str, Any]] | None = None,
    equity: float = 0.0,
    cash: float = 0.0,
) -> list[dict[str, Any]]:
    """BUY strongest breakout/momentum; flatten faded names. No shorts."""
    held = {str(k).upper(): dict(v) for k, v in (positions or {}).items()}
    ranked = rank(quotes)
    if not ranked or equity <= 0:
        return []
    longs = [row for row in ranked if row["score"] >= ENTRY_SCORE][:MAX_NAMES]
    long_set = {row["symbol"] for row in longs}
    by_sym = {row["symbol"]: row for row in ranked}
    orders: list[dict[str, Any]] = []

    for symbol, pos in held.items():
        qty = float(pos.get("qty") or 0.0)
        last = float((quotes.get(symbol) or {}).get("last") or pos.get("mark") or pos.get("last") or 0.0)
        row = by_sym.get(symbol) or {}
        score = float(row.get("score") or EXIT_SCORE)
        if qty > 0 and last > 0 and (symbol not in long_set or score < EXIT_SCORE):
            note = row.get("note") or f"breakout/mom exit score={score:.2f}"
            orders.append(
                {
                    "symbol": symbol,
                    "qty": -qty,
                    "last": last,
                    "reason": f"momentum_exit score={score:+.3f}",
                    "note": note,
                }
            )

    deployable = max(0.0, (cash if cash > 0 else equity) - CASH_RESERVE)
    if deployable < MIN_NOTIONAL or not longs:
        return orders

    weights = [PRIMARY_FRAC, SECONDARY_FRAC][: len(longs)]
    weight_sum = sum(weights) or 1.0
    weights = [w / weight_sum for w in weights]

    for row, weight in zip(longs, weights):
        symbol = row["symbol"]
        last = row["last"]
        cur_qty = float((held.get(symbol) or {}).get("qty") or 0.0)
        cur_mkt = cur_qty * last
        target = equity * weight
        if cur_mkt >= target * 0.90:
            continue
        need = min(target - cur_mkt, deployable)
        if need < MIN_NOTIONAL:
            continue
        qty = need / last
        if qty <= 0:
            continue
        orders.append(
            {
                "symbol": symbol,
                "qty": qty,
                "last": last,
                "reason": f"breakout_entry score={row['score']:+.3f}",
                "note": row["note"],
            }
        )
        deployable -= need
    return orders
