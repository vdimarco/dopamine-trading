"""Paper broker engine. Simulated fills only. PAPER ONLY. Equities desk."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data.json"
STARTING_CASH = 100_000.0
TARGET_PCT = 0.05
MAX_FEED = 200
MAX_FILLS = 200
MAX_SNAPS = 360


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class PaperBroker:
    """In-memory paper book with JSON persistence. Never routes live orders."""

    def __init__(self, cash: float = STARTING_CASH, path: Path | None = None) -> None:
        self.path = Path(path) if path else DATA_PATH
        self.mode = "PAPER"
        self.desk = "equities"
        self.version = "live1"
        self.starting_cash = float(cash)
        self.cash = float(cash)
        self.positions: dict[str, dict[str, Any]] = {}
        self.fills: list[dict[str, Any]] = []
        self.feed: list[dict[str, Any]] = []
        self.created_at = utc_now()
        self.updated_at = self.created_at
        self.last_quotes: dict[str, dict[str, Any]] = {}
        self.snaps: list[dict[str, Any]] = []
        self.high = float(cash)
        self.low = float(cash)

    def note(self, kind: str, text: str, **extra: Any) -> None:
        event = {"ts": utc_now(), "kind": kind, "text": text, **extra}
        self.feed.insert(0, event)
        del self.feed[MAX_FEED:]
        self.updated_at = event["ts"]

    def mark(self, quotes: dict[str, dict[str, Any]]) -> None:
        clean = {k: v for k, v in quotes.items() if not k.startswith("_") and isinstance(v, dict)}
        self.last_quotes = clean
        for symbol, pos in self.positions.items():
            last = float((clean.get(symbol) or {}).get("last") or pos.get("last") or pos.get("avg") or 0.0)
            pos["last"] = last
            qty = float(pos.get("qty") or 0.0)
            avg = float(pos.get("avg") or 0.0)
            pos["mkt"] = qty * last
            pos["pnl"] = qty * (last - avg)
            pos["pnl_pct"] = ((last / avg) - 1.0) if avg else 0.0
        self.updated_at = utc_now()

    def equity(self) -> float:
        mkt = sum(float(p.get("mkt") or 0.0) for p in self.positions.values())
        return self.cash + mkt

    def market_order(self, symbol: str, qty: float, last: float, reason: str = "") -> dict[str, Any] | None:
        symbol = symbol.upper()
        qty = float(qty)
        last = float(last)
        if qty == 0 or last <= 0:
            return None
        notional = abs(qty) * last
        side = "BUY" if qty > 0 else "SELL"
        if qty > 0 and notional > self.cash + 1e-9:
            self.note("reject", f"REJECT {symbol} {side} cash {self.cash:.2f} need {notional:.2f}")
            return None
        pos = self.positions.get(symbol) or {"symbol": symbol, "qty": 0.0, "avg": 0.0, "last": last}
        cur_qty = float(pos["qty"])
        cur_avg = float(pos["avg"])
        realized = 0.0
        if qty > 0:
            new_qty = cur_qty + qty
            pos["avg"] = ((cur_avg * cur_qty) + (last * qty)) / new_qty if new_qty else 0.0
            pos["qty"] = new_qty
            self.cash -= notional
        else:
            sell_qty = min(abs(qty), cur_qty) if cur_qty > 0 else 0.0
            if sell_qty <= 0:
                self.note("reject", f"REJECT {symbol} SELL flat")
                return None
            realized = sell_qty * (last - cur_avg)
            pos["qty"] = cur_qty - sell_qty
            self.cash += sell_qty * last
            qty = -sell_qty
            notional = sell_qty * last
            if pos["qty"] <= 1e-9:
                self.positions.pop(symbol, None)
                pos = {"symbol": symbol, "qty": 0.0, "avg": 0.0, "last": last, "closed": True}
        if not pos.get("closed"):
            pos["last"] = last
            pos["mkt"] = float(pos["qty"]) * last
            pos["pnl"] = float(pos["qty"]) * (last - float(pos["avg"]))
            self.positions[symbol] = pos
        fill = {
            "ts": utc_now(),
            "symbol": symbol,
            "side": side,
            "qty": abs(qty),
            "price": last,
            "notional": notional,
            "realized": realized,
            "reason": reason,
            "mode": "PAPER",
        }
        self.fills.insert(0, fill)
        del self.fills[MAX_FILLS:]
        self.note(
            "fill",
            f"{side} {symbol} {abs(qty):.4f} @ {last:.2f}",
            symbol=symbol,
            side=side,
            qty=abs(qty),
            price=last,
            reason=reason,
        )
        self.updated_at = fill["ts"]
        return fill

    def _spy_pct(self) -> float:
        spy = self.last_quotes.get("SPY") or {}
        change = spy.get("change_pct")
        if change is None:
            return 0.0
        return float(change) * 100.0

    def _session_end_et(self) -> str:
        try:
            from zoneinfo import ZoneInfo

            now = datetime.now(ZoneInfo("America/New_York"))
            end = now.replace(hour=16, minute=0, second=0, microsecond=0)
            return end.isoformat()
        except Exception:
            return utc_now()

    def _push_snap(self, spy_pct: float) -> None:
        eq = self.equity()
        start = self.starting_cash
        pct = ((eq - start) / start * 100.0) if start else 0.0
        spy_eq = start * (1.0 + (spy_pct / 100.0))
        row = {
            "t": self.updated_at or utc_now(),
            "eq": round(eq, 4),
            "pct": round(pct, 4),
            "spy_eq": round(spy_eq, 4),
        }
        if not self.snaps:
            self.snaps.append(
                {
                    "t": self.created_at,
                    "eq": round(start, 4),
                    "pct": 0.0,
                    "spy_eq": round(start, 4),
                }
            )
        last = self.snaps[-1]
        same = last.get("t") == row["t"] and abs(float(last.get("eq") or 0.0) - eq) < 1e-6
        if same and len(self.snaps) > 1:
            self.snaps[-1] = row
        else:
            self.snaps.append(row)
        del self.snaps[:-MAX_SNAPS]

    def snapshot(self) -> dict[str, Any]:
        eq = self.equity()
        start = self.starting_cash
        target = start * (1.0 + TARGET_PCT)
        pnl = eq - start
        pnl_pct = (pnl / start * 100.0) if start else 0.0
        spy_pct = self._spy_pct()
        alpha_pct = pnl_pct - spy_pct
        self.high = max(float(self.high or start), eq)
        self.low = min(float(self.low or start), eq)
        realized = 0.0
        for fill in self.fills:
            realized += float(fill.get("realized") or fill.get("realized_pnl") or 0.0)
        quotes = []
        for symbol, row in sorted(self.last_quotes.items()):
            quotes.append(
                {
                    "symbol": symbol,
                    "last": row.get("last"),
                    "change_pct": row.get("change_pct"),
                    "momentum_20d": row.get("momentum_20d"),
                }
            )
        positions = []
        for sym, pos in sorted(self.positions.items()):
            last = float(pos.get("last") or 0.0)
            u_pnl = float(pos.get("pnl") or 0.0)
            u_pct = float(pos.get("pnl_pct") or 0.0) * 100.0
            positions.append(
                {
                    **pos,
                    "symbol": sym,
                    "last": last,
                    "mark": last,
                    "u_pnl": u_pnl,
                    "u_pct": u_pct,
                }
            )
        fills = []
        for fill in self.fills:
            row = dict(fill)
            row["ts_et"] = row.get("ts_et") or row.get("ts") or ""
            row["realized_pnl"] = row.get("realized_pnl", row.get("realized") or 0.0)
            fills.append(row)
        return {
            "mode": "PAPER",
            "desk": "equities",
            "version": "matrix1",
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.created_at,
            "start": start,
            "starting_cash": start,
            "target_equity": target,
            "target_hit": eq >= target,
            "to_target": target - eq,
            "cash": self.cash,
            "equity": eq,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "spy_pct": spy_pct,
            "alpha_pct": alpha_pct,
            "beating_spy": alpha_pct > 0,
            "profitable": pnl > 0,
            "winning": pnl > 0,
            "realized": realized,
            "unrealized": sum(float(p.get("u_pnl") or 0.0) for p in positions),
            "high": self.high,
            "low": self.low,
            "ends_at": self._session_end_et(),
            "snaps": list(self.snaps),
            "positions": positions,
            "fills": fills,
            "feed": list(self.feed),
            "quotes": quotes,
            "pulse": {"ok": True, "label": "matrix1", "age_s": 0},
        }

    def save(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.high = max(float(self.high or self.starting_cash), self.equity())
        self.low = min(float(self.low or self.starting_cash), self.equity())
        self._push_snap(self._spy_pct())
        payload = self.snapshot()
        payload["_book"] = {
            "cash": self.cash,
            "starting_cash": self.starting_cash,
            "positions": self.positions,
            "fills": self.fills,
            "feed": self.feed,
            "created_at": self.created_at,
            "snaps": self.snaps,
            "high": self.high,
            "low": self.low,
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.path

    @classmethod
    def load(cls, path: Path | None = None, cash: float = STARTING_CASH) -> "PaperBroker":
        dest = Path(path) if path else DATA_PATH
        broker = cls(cash=cash, path=dest)
        if not dest.exists():
            broker.note("boot", "PAPER book opened")
            return broker
        try:
            payload = json.loads(dest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            broker.note("boot", "PAPER book reset (unreadable data.json)")
            return broker
        book = payload.get("_book") or payload
        broker.starting_cash = float(book.get("starting_cash") or payload.get("starting_cash") or cash)
        broker.cash = float(book.get("cash") or payload.get("cash") or cash)
        broker.positions = {str(k).upper(): dict(v) for k, v in (book.get("positions") or {}).items()}
        if isinstance(payload.get("positions"), list) and not broker.positions:
            for row in payload["positions"]:
                if row.get("symbol"):
                    broker.positions[str(row["symbol"]).upper()] = dict(row)
        broker.fills = list(book.get("fills") or payload.get("fills") or [])
        broker.feed = list(book.get("feed") or payload.get("feed") or [])
        broker.created_at = str(book.get("created_at") or payload.get("created_at") or broker.created_at)
        broker.updated_at = str(payload.get("updated_at") or utc_now())
        broker.snaps = list(book.get("snaps") or payload.get("snaps") or [])
        broker.high = float(book.get("high") or payload.get("high") or broker.starting_cash)
        broker.low = float(book.get("low") or payload.get("low") or broker.starting_cash)
        broker.note("boot", "PAPER book restored")
        return broker
