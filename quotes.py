"""Yahoo Finance quotes via urllib. Equities paper desk only."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
USER_AGENT = (
    "Mozilla/5.0 (compatible; dopamine-trading-paper/1.0; +https://github.com/vdimarco/dopamine-trading)"
)

# Liquid US equities / ETFs only. No crypto tickers.
DEFAULT_UNIVERSE = (
    "SPY",
    "QQQ",
    "IWM",
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "GOOGL",
    "META",
    "TSLA",
    "JPM",
    "XOM",
    "UNH",
    "AVGO",
    "COST",
)


def _ctx() -> ssl.SSLContext:
    return ssl.create_default_context()


def _get(url: str, timeout: float = 12.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as resp:
        return resp.read()


def fetch_chart(symbol: str, range_: str = "3mo", interval: str = "1d") -> dict[str, Any]:
    """Return Yahoo chart payload for one equity symbol."""
    qs = urllib.parse.urlencode({"range": range_, "interval": interval, "includePrePost": "false"})
    url = f"{YAHOO_CHART.format(symbol=urllib.parse.quote(symbol))}?{qs}"
    raw = _get(url)
    payload = json.loads(raw.decode("utf-8"))
    results = (payload.get("chart") or {}).get("result") or []
    if not results:
        error = (payload.get("chart") or {}).get("error") or {"message": "empty chart"}
        raise RuntimeError(f"yahoo chart failed for {symbol}: {error}")
    return results[0]


def _closes(chart: dict[str, Any]) -> list[float]:
    quote = ((chart.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    out: list[float] = []
    for value in closes:
        if value is None:
            continue
        try:
            price = float(value)
        except (TypeError, ValueError):
            continue
        if price > 0:
            out.append(price)
    return out


def quote_from_chart(symbol: str, chart: dict[str, Any]) -> dict[str, Any]:
    meta = chart.get("meta") or {}
    closes = _closes(chart)
    last = float(meta.get("regularMarketPrice") or (closes[-1] if closes else 0.0) or 0.0)
    prev = float(meta.get("chartPreviousClose") or (closes[-2] if len(closes) > 1 else last) or last)
    change = last - prev if prev else 0.0
    change_pct = (change / prev) if prev else 0.0
    lookback = 20
    mom = 0.0
    if len(closes) > lookback and closes[-1 - lookback] > 0:
        mom = (closes[-1] / closes[-1 - lookback]) - 1.0
    return {
        "symbol": symbol.upper(),
        "last": last,
        "prev": prev,
        "change": change,
        "change_pct": change_pct,
        "momentum_20d": mom,
        "closes": closes[-60:],
        "currency": meta.get("currency") or "USD",
        "exchange": meta.get("exchangeName") or "",
        "instrument": meta.get("instrumentType") or "EQUITY",
    }


def fetch_quote(symbol: str) -> dict[str, Any]:
    return quote_from_chart(symbol.upper(), fetch_chart(symbol.upper()))


def fetch_quotes(symbols: list[str] | tuple[str, ...] | None = None) -> dict[str, dict[str, Any]]:
    """Fetch Yahoo quotes. Skips failed names so one miss does not abort the desk."""
    names = [s.strip().upper() for s in (symbols or DEFAULT_UNIVERSE) if s and s.strip()]
    out: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for name in names:
        try:
            out[name] = fetch_quote(name)
        except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError, KeyError, ValueError) as exc:
            errors[name] = str(exc)
    if errors:
        out["_errors"] = {"kind": "quote_errors", "items": errors}  # type: ignore[assignment]
    return out


if __name__ == "__main__":
    quotes = fetch_quotes(DEFAULT_UNIVERSE[:4])
    for sym, row in quotes.items():
        if sym.startswith("_"):
            continue
        print(f"{row['symbol']:6} {row['last']:10.2f}  mom20 {row['momentum_20d']:+.2%}")
