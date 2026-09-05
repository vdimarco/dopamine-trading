"""Checks for Matrix jack-in dashboard + paper snapshot fields."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import build_dash
from engine import STARTING_CASH, TARGET_PCT, PaperBroker


class MatrixDashTests(unittest.TestCase):
    def test_build_dash_matrix1(self) -> None:
        built = build_dash.build()
        self.assertEqual(built, ["dashboard/index.html", "dashboard/dash.js"])

    def test_html_viewport_contract(self) -> None:
        html = Path("dashboard/index.html").read_text(encoding="utf-8")
        self.assertIn("viewport-fit=cover", html)
        self.assertIn("safe-area-inset-top", html)
        self.assertNotIn("onclick=", html)
        self.assertNotIn("—", html)
        self.assertIn("dash.js?v=matrix1", html)
        self.assertIn("overflow-x:hidden", html)

    def test_js_single_fs_handler(self) -> None:
        js = Path("dashboard/dash.js").read_text(encoding="utf-8")
        self.assertEqual(js.count("btn.addEventListener('click'"), 1)
        self.assertNotIn("window.toggleChartFullscreen", js)
        self.assertIn("vs SPY", js + Path("dashboard/index.html").read_text(encoding="utf-8"))
        self.assertIn("label:'SPY'", js)

    def test_snapshot_matrix_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            book = PaperBroker(cash=STARTING_CASH, path=path)
            book.last_quotes = {"SPY": {"last": 500.0, "change_pct": 0.01}}
            book.mark(book.last_quotes)
            book.save()
            snap = book.snapshot()
        self.assertEqual(snap["version"], "matrix1")
        self.assertEqual(snap["start"], STARTING_CASH)
        self.assertAlmostEqual(snap["target_equity"], STARTING_CASH * (1 + TARGET_PCT))
        self.assertAlmostEqual(snap["spy_pct"], 1.0)
        self.assertGreaterEqual(len(snap["snaps"]), 2)
        self.assertIn("spy_eq", snap["snaps"][-1])
        self.assertIn("mark", snap["positions"][0] if snap["positions"] else {"mark": 0})
        self.assertTrue(abs(snap["pnl_pct"]) < 50 or snap["equity"] != STARTING_CASH)


if __name__ == "__main__":
    unittest.main()
