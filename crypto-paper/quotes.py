"""Public crypto quotes. Binance REST first, CoinGecko fallback. No API keys."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BINANCE = "https://data-api.binance.vision"
COINGECKO = "https://api.coingecko.com/api/v3"
USER_AGENT = (
    "Mozilla/5.0 (compatible; dopamine-trading-crypto-paper/1.0; "
    "+https://github.com/vdimarco/dopamine-trading)"
)

DEFAULT_UNIVERSE = ("BTC", "ETH", "SOL", "DOGE", "SUI")
BINANCE_SYMBOL = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "DOGE": "DOGEUSDT",
    "SUI": "SUIUSDT",
}
COINGECKO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "DOGE": "dogecoin",
    "SUI": "sui",
}


def _ctx() -> ssl.SSLContext:
    return ssl.create_default_context()


def _get(url: str, timeout: float = 12.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as resp:
        return resp.read()


def _json(url: str, timeout: float = 12.0) -> Any:
    return json.loads(_get(url, timeout=timeout).decode("utf-8"))


def _closes_from_klines(rows: list[Any]) -> tuple[list[float], list[float]]:
    closes: list[float] = []
    highs: list[float] = []
    for row in rows:
        try:
            high = float(row[2])
            close = float(row[4])
        except (TypeError, ValueError, IndexError):
            continue
        if close > 0:
            closes.append(close)
            highs.append(high if high > 0 else close)
    return closes, highs


def _mom_bo(closes: list[float], highs: list[float]) -> tuple[float, float]:
    if not closes:
        return 0.0, 0.0
    last = closes[-1]
    lookback = 24 if len(closes) > 24 else max(1, len(closes) - 1)
    base = closes[-1 - lookback] if len(closes) > lookback else closes[0]
    mom = ((last / base) - 1.0) * 100.0 if base else 0.0
    window = highs[-24:] if highs else [last]
    peak = max(window) if window else last
    bo = ((last / peak) - 1.0) * 100.0 if peak else 0.0
    return mom, bo


def _row(symbol: str, last: float, day_pct: float, mom: float, bo: float, source: str) -> dict[str, Any]:
    return {
        "symbol": symbol.upper(),
        "last": last,
        "change_pct": day_pct / 100.0,
        "day_pct": day_pct,
        "momentum": mom,
        "breakout": bo,
        "source": source,
    }


def fetch_binance_quote(symbol: str) -> dict[str, Any]:
    pair = BINANCE_SYMBOL.get(symbol.upper())
    if not pair:
        raise RuntimeError(f"no binance pair for {symbol}")
    ticker = _json(f"{BINANCE}/api/v3/ticker/24hr?symbol={pair}")
    last = float(ticker.get("lastPrice") or 0.0)
    day = float(ticker.get("priceChangePercent") or 0.0)
    klines = _json(f"{BINANCE}/api/v3/klines?symbol={pair}&interval=1h&limit=48")
    mom, bo = _mom_bo(*_closes_from_klines(klines if isinstance(klines, list) else []))
    if last <= 0:
        raise RuntimeError(f"binance empty last for {symbol}")
    return _row(symbol, last, day, mom, bo, "binance_public")


def fetch_coingecko_quotes(symbols: list[str]) -> dict[str, dict[str, Any]]:
    ids = [COINGECKO_ID[s] for s in symbols if s in COINGECKO_ID]
    if not ids:
        return {}
    qs = urllib.parse.urlencode(
        {
            "ids": ",".join(ids),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        }
    )
    payload = _json(f"{COINGECKO}/simple/price?{qs}")
    inverse = {v: k for k, v in COINGECKO_ID.items()}
    out: dict[str, dict[str, Any]] = {}
    for cid, row in payload.items():
        symbol = inverse.get(cid)
        if not symbol:
            continue
        last = float((row or {}).get("usd") or 0.0)
        day = float((row or {}).get("usd_24h_change") or 0.0)
        mom, bo = day, 0.0
        try:
            chart = _json(f"{COINGECKO}/coins/{cid}/market_chart?vs_currency=usd&days=2")
            prices = [float(p[1]) for p in (chart.get("prices") or []) if p and p[1]]
            highs = prices[:]
            mom, bo = _mom_bo(prices, highs)
        except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError, KeyError, ValueError, TypeError):
            mom = day
            bo = 0.0
        if last > 0:
            out[symbol] = _row(symbol, last, day, mom, bo, "coingecko")
    return out


def fetch_quotes(symbols: list[str] | tuple[str, ...] | None = None) -> dict[str, dict[str, Any]]:
    """Live public quotes. Binance first; CoinGecko fills misses. No keys."""
    names = [s.strip().upper() for s in (symbols or DEFAULT_UNIVERSE) if s and s.strip()]
    out: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for name in names:
        try:
            out[name] = fetch_binance_quote(name)
        except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError, KeyError, ValueError) as exc:
            errors[name] = f"binance:{exc}"
    missing = [name for name in names if name not in out]
    if missing:
        try:
            gecko = fetch_coingecko_quotes(missing)
            out.update(gecko)
            for name in list(errors):
                if name in gecko:
                    errors.pop(name, None)
        except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError, KeyError, ValueError) as exc:
            for name in missing:
                errors.setdefault(name, f"coingecko:{exc}")
    sources = {row.get("source") for row in out.values() if isinstance(row, dict)}
    if sources == {"coingecko"}:
        out["_source"] = "coingecko"  # type: ignore[assignment]
    elif "binance_public" in sources and "coingecko" in sources:
        out["_source"] = "binance_public+coingecko"  # type: ignore[assignment]
    else:
        out["_source"] = "binance_public"  # type: ignore[assignment]
    if errors:
        out["_errors"] = {"kind": "quote_errors", "items": errors}  # type: ignore[assignment]
    return out


if __name__ == "__main__":
    quotes = fetch_quotes()
    source = quotes.pop("_source", "")
    errors = quotes.pop("_errors", {})
    print(f"source={source}")
    for sym in DEFAULT_UNIVERSE:
        row = quotes.get(sym)
        if not row:
            print(f"{sym:4} miss")
            continue
        print(
            f"{row['symbol']:4} {row['last']:12.4f}  day {row['day_pct']:+.2f}%  "
            f"mom {row['momentum']:+.2f}%  bo {row['breakout']:+.2f}%"
        )
    if errors:
        print(errors)
