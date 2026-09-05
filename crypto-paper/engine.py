"""CRYPTO PAPER broker. Simulated fills only. No live orders. No secrets."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data.json"
STARTING_CASH = 1000.0
TARGET_EQUITY = 100_000.0
HORIZON_DAYS = 30
FEE_RATE = 0.001  # 10 bps, matches live book
MAX_FEED = 200
MAX_FILLS = 200
MAX_SNAPS = 2000
ET = ZoneInfo("America/New_York")
UNIVERSE = ("BTC", "ETH", "SOL", "DOGE", "SUI")


def now_et() -> datetime:
    return datetime.now(ET)


def iso_et(dt: datetime | None = None) -> str:
    stamp = dt or now_et()
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=ET)
    return stamp.isoformat()


class PaperBroker:
    """Paper book: cash, long-only fractionals, small fee. Never shorts. Never live."""

    def __init__(self, cash: float = STARTING_CASH, path: Path | None = None) -> None:
        self.path = Path(path) if path else DATA_PATH
        self.mode = "CRYPTO_PAPER"
        self.asset_class = "crypto"
        self.starting_cash = float(cash)
        self.cash = float(cash)
        self.positions: dict[str, dict[str, Any]] = {}
        self.fills: list[dict[str, Any]] = []
        self.feed: list[dict[str, Any]] = []
        started = now_et()
        self.created_at = iso_et(started)
        self.updated_at = self.created_at
        self.started_at = self.created_at
        self.ends_at = iso_et(started.replace(microsecond=0) + timedelta(days=HORIZON_DAYS))
        self.last_quotes: dict[str, dict[str, Any]] = {}
        self.snaps: list[dict[str, Any]] = []
        self.high = float(cash)
        self.low = float(cash)
        self.btc_open = 0.0
        self.quote_source = ""
        self.universe = list(UNIVERSE)
        self.status = "running"

    def note(self, kind: str, text: str, **extra: Any) -> None:
        event = {"ts": iso_et(), "kind": kind, "text": text, **extra}
        self.feed.insert(0, event)
        del self.feed[MAX_FEED:]
        self.updated_at = event["ts"]

    def mark(self, quotes: dict[str, dict[str, Any]]) -> None:
        clean = {k: v for k, v in quotes.items() if not k.startswith("_") and isinstance(v, dict)}
        self.last_quotes = clean
        src = quotes.get("_source")
        if isinstance(src, str) and src:
            self.quote_source = src
        btc = clean.get("BTC") or {}
        btc_px = float(btc.get("last") or 0.0)
        if btc_px > 0 and self.btc_open <= 0:
            self.btc_open = btc_px
        for symbol, pos in self.positions.items():
            last = float((clean.get(symbol) or {}).get("last") or pos.get("mark") or pos.get("avg") or 0.0)
            qty = float(pos.get("qty") or 0.0)
            avg = float(pos.get("avg") or 0.0)
            pos["mark"] = last
            pos["mkt"] = qty * last
            pos["u_pnl"] = qty * (last - avg)
            pos["u_pct"] = ((last / avg) - 1.0) * 100.0 if avg else 0.0
        self.updated_at = iso_et()

    def equity(self) -> float:
        mkt = sum(float(p.get("mkt") or 0.0) for p in self.positions.values())
        return self.cash + mkt

    def market_order(
        self,
        symbol: str,
        qty: float,
        last: float,
        reason: str = "",
        note: str = "",
    ) -> dict[str, Any] | None:
        symbol = symbol.upper()
        qty = float(qty)
        last = float(last)
        if qty == 0 or last <= 0:
            return None
        side = "BUY" if qty > 0 else "SELL"
        if qty < 0:
            held = float((self.positions.get(symbol) or {}).get("qty") or 0.0)
            if held <= 0:
                self.note("reject", f"REJECT {symbol} SELL flat")
                return None
            qty = -min(abs(qty), held)
        notional = abs(qty) * last
        fee = notional * FEE_RATE
        if qty > 0 and (notional + fee) > self.cash + 1e-12:
            self.note("reject", f"REJECT {symbol} BUY cash {self.cash:.4f} need {notional + fee:.4f}")
            return None
        pos = self.positions.get(symbol) or {"symbol": symbol, "qty": 0.0, "avg": 0.0, "mark": last}
        cur_qty = float(pos["qty"])
        cur_avg = float(pos["avg"])
        realized = 0.0
        if qty > 0:
            cost = notional + fee
            new_qty = cur_qty + qty
            pos["avg"] = ((cur_avg * cur_qty) + cost) / new_qty if new_qty else 0.0
            pos["qty"] = new_qty
            self.cash -= cost
        else:
            sell_qty = abs(qty)
            proceeds = notional - fee
            realized = proceeds - (cur_avg * sell_qty)
            pos["qty"] = cur_qty - sell_qty
            self.cash += proceeds
            if pos["qty"] <= 1e-12:
                self.positions.pop(symbol, None)
                pos = {"symbol": symbol, "qty": 0.0, "avg": 0.0, "mark": last, "closed": True}
        if not pos.get("closed"):
            pos["mark"] = last
            pos["mkt"] = float(pos["qty"]) * last
            pos["u_pnl"] = float(pos["qty"]) * (last - float(pos["avg"]))
            pos["u_pct"] = ((last / float(pos["avg"])) - 1.0) * 100.0 if pos.get("avg") else 0.0
            self.positions[symbol] = pos
        eq = self.equity()
        fill = {
            "ts_et": iso_et(),
            "symbol": symbol,
            "side": side,
            "qty": f"{abs(qty):.8f}".rstrip("0").rstrip("."),
            "price": f"{last:.8f}".rstrip("0").rstrip("."),
            "notional": f"{notional:.4f}",
            "fees": f"{fee:.4f}",
            "realized_pnl": f"{realized:.4f}",
            "cash_after": f"{self.cash:.4f}",
            "equity_after": f"{eq:.4f}",
            "note": note or reason,
        }
        self.fills.append(fill)
        del self.fills[:-MAX_FILLS]
        self.note(
            "fill",
            f"{side} {symbol} {abs(qty):.8f} @ {last}",
            symbol=symbol,
            side=side,
            qty=abs(qty),
            price=last,
            reason=reason,
        )
        self.updated_at = fill["ts_et"]
        return fill

    def _btc_pct(self) -> tuple[float, float, float]:
        btc = self.last_quotes.get("BTC") or {}
        btc_now = float(btc.get("last") or 0.0)
        opened = float(self.btc_open or 0.0)
        if opened <= 0 and btc_now > 0:
            opened = btc_now
            self.btc_open = btc_now
        pct = ((btc_now / opened) - 1.0) * 100.0 if opened and btc_now else 0.0
        return opened, btc_now, pct

    def _horizon(self) -> tuple[float, float]:
        try:
            end = datetime.fromisoformat(self.ends_at)
            if end.tzinfo is None:
                end = end.replace(tzinfo=ET)
            remaining = (end - now_et()).total_seconds() / 86400.0
        except (TypeError, ValueError):
            remaining = float(HORIZON_DAYS)
        return float(HORIZON_DAYS), max(0.0, remaining)

    def _push_snap(self, btc_pct: float) -> None:
        eq = self.equity()
        start = self.starting_cash
        pct = ((eq - start) / start * 100.0) if start else 0.0
        btc_eq = start * (1.0 + (btc_pct / 100.0))
        row = {
            "t": self.updated_at or iso_et(),
            "eq": round(eq, 4),
            "pct": round(pct, 4),
            "btc_eq": round(btc_eq, 4),
            "spy_eq": round(btc_eq, 4),
        }
        if not self.snaps:
            self.snaps.append(
                {
                    "t": self.started_at,
                    "eq": round(start, 4),
                    "pct": 0.0,
                    "btc_eq": round(start, 4),
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
        target = TARGET_EQUITY
        pnl = eq - start
        pnl_pct = (pnl / start * 100.0) if start else 0.0
        btc_open, btc_now, btc_pct = self._btc_pct()
        alpha_pct = pnl_pct - btc_pct
        self.high = max(float(self.high or start), eq)
        self.low = min(float(self.low or start), eq)
        realized = 0.0
        for fill in self.fills:
            realized += float(fill.get("realized_pnl") or fill.get("realized") or 0.0)
        positions = []
        for sym, pos in self.positions.items():
            mark = float(pos.get("mark") or pos.get("last") or 0.0)
            qty = float(pos.get("qty") or 0.0)
            avg = float(pos.get("avg") or 0.0)
            u_pnl = float(pos.get("u_pnl") if pos.get("u_pnl") is not None else qty * (mark - avg))
            u_pct = float(pos.get("u_pct") if pos.get("u_pct") is not None else (((mark / avg) - 1.0) * 100.0 if avg else 0.0))
            positions.append(
                {
                    "symbol": sym,
                    "qty": qty,
                    "avg": avg,
                    "mark": mark,
                    "u_pnl": round(u_pnl, 4),
                    "u_pct": round(u_pct, 4),
                }
            )
        horizon_days, days_remaining = self._horizon()
        climb = max(target - start, 1e-9)
        progress_pct = max(0.0, (eq - start) / climb * 100.0)
        return {
            "mode": "CRYPTO_PAPER",
            "asset_class": "crypto",
            "horizon_days": horizon_days,
            "days_remaining": round(days_remaining, 4),
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "ends_at": self.ends_at,
            "equity": round(eq, 4),
            "cash": round(self.cash, 4),
            "start": start,
            "pnl": round(pnl, 4),
            "pnl_pct": round(pnl_pct, 4),
            "realized": round(realized, 4),
            "unrealized": round(sum(float(p.get("u_pnl") or 0.0) for p in positions), 4),
            "high": round(self.high, 4),
            "low": round(self.low, 4),
            "btc_open": round(btc_open, 8),
            "btc_now": round(btc_now, 8),
            "btc_pct": round(btc_pct, 4),
            "spy_pct": round(btc_pct, 4),
            "alpha_pct": round(alpha_pct, 4),
            "profitable": pnl > 0,
            "beating_btc": alpha_pct > 0,
            "target_equity": target,
            "to_target": round(target - eq, 4),
            "target_hit": eq >= target,
            "progress_pct": round(progress_pct, 4),
            "status": self.status,
            "quote_source": self.quote_source or "binance_public",
            "universe": list(self.universe),
            "positions": positions,
            "fills": list(self.fills),
            "snaps": list(self.snaps),
            "feed": list(self.feed),
        }

    def save(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _open, _now, btc_pct = self._btc_pct()
        self.high = max(float(self.high or self.starting_cash), self.equity())
        self.low = min(float(self.low or self.starting_cash), self.equity())
        self._push_snap(btc_pct)
        payload = self.snapshot()
        payload["_book"] = {
            "cash": self.cash,
            "starting_cash": self.starting_cash,
            "positions": self.positions,
            "fills": self.fills,
            "feed": self.feed,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "ends_at": self.ends_at,
            "snaps": self.snaps,
            "high": self.high,
            "low": self.low,
            "btc_open": self.btc_open,
            "quote_source": self.quote_source,
            "universe": self.universe,
            "status": self.status,
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.path

    @classmethod
    def load(cls, path: Path | None = None, cash: float = STARTING_CASH) -> "PaperBroker":
        dest = Path(path) if path else DATA_PATH
        broker = cls(cash=cash, path=dest)
        if not dest.exists():
            broker.note("boot", "CRYPTO PAPER book opened")
            return broker
        try:
            payload = json.loads(dest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            broker.note("boot", "CRYPTO PAPER book reset (unreadable data.json)")
            return broker
        book = payload.get("_book") or payload
        broker.starting_cash = float(book.get("starting_cash") or payload.get("start") or cash)
        broker.cash = float(book.get("cash") or payload.get("cash") or cash)
        raw_pos = book.get("positions") or {}
        if isinstance(raw_pos, dict):
            broker.positions = {str(k).upper(): dict(v) for k, v in raw_pos.items()}
        elif isinstance(raw_pos, list):
            broker.positions = {}
            for row in raw_pos:
                if row.get("symbol"):
                    broker.positions[str(row["symbol"]).upper()] = dict(row)
        if isinstance(payload.get("positions"), list) and not broker.positions:
            for row in payload["positions"]:
                if row.get("symbol"):
                    broker.positions[str(row["symbol"]).upper()] = dict(row)
        broker.fills = list(book.get("fills") or payload.get("fills") or [])
        broker.feed = list(book.get("feed") or payload.get("feed") or [])
        broker.created_at = str(book.get("created_at") or payload.get("started_at") or broker.created_at)
        broker.started_at = str(book.get("started_at") or payload.get("started_at") or broker.created_at)
        broker.ends_at = str(book.get("ends_at") or payload.get("ends_at") or broker.ends_at)
        broker.updated_at = str(payload.get("updated_at") or iso_et())
        broker.snaps = list(book.get("snaps") or payload.get("snaps") or [])
        broker.high = float(book.get("high") or payload.get("high") or broker.starting_cash)
        broker.low = float(book.get("low") or payload.get("low") or broker.starting_cash)
        broker.btc_open = float(book.get("btc_open") or payload.get("btc_open") or 0.0)
        broker.quote_source = str(book.get("quote_source") or payload.get("quote_source") or "")
        broker.universe = list(book.get("universe") or payload.get("universe") or UNIVERSE)
        broker.status = str(book.get("status") or payload.get("status") or "running")
        broker.note("boot", "CRYPTO PAPER book restored")
        return broker
