"""CRYPTO PAPER snapshot fields + matrix2 dashboard viewport/cache gate."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from engine import FEE_RATE, STARTING_CASH, TARGET_EQUITY, PaperBroker
from republish_dashboard import collect_files
from strategy import signals

ROOT = Path(__file__).resolve().parent
DASH = ROOT / "dashboard"


class CryptoPaperTests(unittest.TestCase):
    def test_html_matrix2_viewport_contract(self) -> None:
        html = (DASH / "index.html").read_text(encoding="utf-8")
        self.assertIn("viewport-fit=cover", html)
        self.assertIn("safe-area-inset-top", html)
        self.assertNotIn("onclick=", html)
        self.assertNotIn("—", html)
        self.assertIn("dash.js?v=matrix2", html)
        self.assertNotIn("dash.js?v=matrix1", html)
        self.assertNotIn("dash.js?v=live1", html)
        self.assertIn("overflow-x:clip", html)
        self.assertIn("matrix2 responsive hard lock", html)
        self.assertIn("CRYPTO PAPER // JACKED IN", html)
        self.assertIn("vs BTC", html)
        self.assertIn('id="fsBtn"', html)
        self.assertIn('id="chartPanel"', html)
        self.assertIn('id="pnl"', html)
        self.assertIn('id="curve"', html)
        self.assertIn('type="button"', html)
        self.assertEqual(html.count('id="fsBtn"'), 1)

    def test_js_btc_overlay_and_fs(self) -> None:
        js = (DASH / "dash.js").read_text(encoding="utf-8")
        self.assertIn("label:'BTC'", js)
        self.assertIn("vs BTC", js)
        self.assertIn("visualViewport", js)
        self.assertIn("wireFullscreen", js)
        self.assertEqual(js.count("btn.addEventListener('click'"), 1)
        self.assertNotIn("dash.js?v=matrix1", js)
        self.assertIn("const START=1000, TARGET=100000", js)

    def test_snapshot_live_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            book = PaperBroker(cash=STARTING_CASH, path=path)
            book.mark(
                {
                    "BTC": {"last": 80000.0, "day_pct": 1.0, "momentum": 0.4, "breakout": -0.1},
                    "ETH": {"last": 2500.0, "day_pct": 2.0, "momentum": 0.8, "breakout": 0.0},
                }
            )
            fill = book.market_order("ETH", 0.2, 2500.0, "test", note="breakout/mom day=2.00% mom=0.80% bo=0.00%")
            self.assertIsNotNone(fill)
            book.mark(book.last_quotes)
            book.save()
            snap = book.snapshot()
        self.assertEqual(snap["mode"], "CRYPTO_PAPER")
        self.assertEqual(snap["asset_class"], "crypto")
        self.assertEqual(snap["start"], STARTING_CASH)
        self.assertEqual(snap["target_equity"], TARGET_EQUITY)
        self.assertEqual(snap["universe"], ["BTC", "ETH", "SOL", "DOGE", "SUI"])
        self.assertIn("btc_pct", snap)
        self.assertIn("spy_pct", snap)
        self.assertIn("alpha_pct", snap)
        self.assertIn("days_remaining", snap)
        self.assertIn("progress_pct", snap)
        self.assertIn("quote_source", snap)
        self.assertGreaterEqual(len(snap["snaps"]), 2)
        self.assertIn("btc_eq", snap["snaps"][-1])
        self.assertIn("spy_eq", snap["snaps"][-1])
        self.assertTrue(snap["positions"])
        pos = snap["positions"][0]
        self.assertIn("mark", pos)
        self.assertIn("u_pnl", pos)
        self.assertIn("u_pct", pos)
        self.assertAlmostEqual(float(pos["qty"]), 0.2)
        fee = 0.2 * 2500.0 * FEE_RATE
        self.assertAlmostEqual(snap["cash"], STARTING_CASH - 500.0 - fee, places=3)

    def test_no_short_fractional_fee(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            book = PaperBroker(cash=STARTING_CASH, path=Path(tmp) / "data.json")
            self.assertIsNone(book.market_order("SOL", -1.0, 140.0, "short"))
            buy = book.market_order("SOL", 0.33333333, 140.0, "frac")
            self.assertIsNotNone(buy)
            sold = book.market_order("SOL", -10.0, 141.0, "flatten")
            self.assertIsNotNone(sold)
            self.assertFalse(book.positions)
            self.assertGreater(book.cash, 0)

    def test_strategy_concentrated(self) -> None:
        quotes = {
            "BTC": {"symbol": "BTC", "last": 80000.0, "day_pct": 0.2, "momentum": 0.1, "breakout": -0.2},
            "ETH": {"symbol": "ETH", "last": 2500.0, "day_pct": 4.5, "momentum": 1.2, "breakout": 0.1},
            "SOL": {"symbol": "SOL", "last": 140.0, "day_pct": -1.0, "momentum": -0.4, "breakout": -0.8},
            "DOGE": {"symbol": "DOGE", "last": 0.16, "day_pct": 0.1, "momentum": 0.0, "breakout": -0.3},
            "SUI": {"symbol": "SUI", "last": 0.80, "day_pct": 3.1, "momentum": 0.4, "breakout": -0.1},
        }
        orders = signals(quotes, {}, equity=1000.0, cash=1000.0)
        buys = [o for o in orders if o["qty"] > 0]
        self.assertTrue(buys)
        self.assertLessEqual(len(buys), 2)
        self.assertEqual(buys[0]["symbol"], "ETH")
        self.assertGreater(buys[0]["qty"] * buys[0]["last"], 700)

    def test_republish_skips_runtime(self) -> None:
        names = [name for name, _ in collect_files(DASH)]
        self.assertIn("index.html", names)
        self.assertIn("dash.js", names)
        self.assertNotIn("data.json", names)

    def test_no_secrets_in_tree(self) -> None:
        import re

        secret_re = re.compile(
            r"(HERENOW_API_KEY=\S+|BEGIN (RSA |OPENSSH |EC )?PRIVATE|sk-[A-Za-z0-9]{20,})"
        )
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if any(part in {".venv", ".herenow", "__pycache__"} for part in path.parts):
                continue
            if path.name in {"data.json", "test_crypto_paper.py"} or ".bak" in path.name:
                continue
            blob = path.read_text(encoding="utf-8", errors="replace")
            match = secret_re.search(blob)
            self.assertIsNone(match, msg=f"{path} looks like it contains a secret")


if __name__ == "__main__":
    unittest.main()
