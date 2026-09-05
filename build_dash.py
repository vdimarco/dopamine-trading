"""Verify dashboard/ Matrix jack-in files. Stub over the checked-in index + dash.js."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DASHBOARD = ROOT / "dashboard"
REQUIRED = ("index.html", "dash.js")

HTML_MUST = (
    'viewport-fit=cover',
    'dash.js?v=matrix1',
    '--safe-t:env(safe-area-inset-top',
    '--safe-r:env(safe-area-inset-right',
    '--safe-b:env(safe-area-inset-bottom',
    '--safe-l:env(safe-area-inset-left',
    'id="fsBtn"',
    'id="chartPanel"',
    'id="pnl"',
    'id="curve"',
    'vs SPY',
    'PAPER DESK // JACKED IN',
    'type="button"',
)
HTML_MUST_NOT = (
    'onclick=',
    '—',
    'dash.js?v=live1',
    'CRYPTO PAPER',
)
JS_MUST = (
    'function wireFullscreen',
    'addEventListener(\'click\'',
    'visualViewport',
    'label:\'SPY\'',
    'function normalize',
)
JS_MUST_NOT = (
    'onclick=',
    'window.toggleChartFullscreen',
    'CRYPTO PAPER',
    '—',
)


def _need(blob: str, needle: str, label: str) -> None:
    if needle not in blob:
        raise RuntimeError(f"{label} missing {needle!r}")


def _forbid(blob: str, needle: str, label: str) -> None:
    if needle in blob:
        raise RuntimeError(f"{label} must not contain {needle!r}")


def build(dest: Path | None = None) -> list[str]:
    folder = Path(dest) if dest else DASHBOARD
    folder.mkdir(parents=True, exist_ok=True)
    missing = [name for name in REQUIRED if not (folder / name).is_file()]
    if missing:
        raise RuntimeError(f"dashboard missing {', '.join(missing)} under {folder}")
    html = (folder / "index.html").read_text(encoding="utf-8")
    js = (folder / "dash.js").read_text(encoding="utf-8")
    for needle in HTML_MUST:
        _need(html, needle, "index.html")
    for needle in HTML_MUST_NOT:
        _forbid(html, needle, "index.html")
    for needle in JS_MUST:
        _need(js, needle, "dash.js")
    for needle in JS_MUST_NOT:
        _forbid(js, needle, "dash.js")
    if html.count('id="fsBtn"') != 1:
        raise RuntimeError("index.html must have exactly one fullscreen button")
    if js.count("btn.addEventListener('click'") != 1 and js.count('btn.addEventListener("click"') != 1:
        raise RuntimeError("dash.js must wire exactly one FS click handler")
    return [str((folder / name).relative_to(ROOT)) for name in REQUIRED]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build/verify Matrix jack-in dashboard files.")
    parser.add_argument("--dir", default=str(DASHBOARD))
    args = parser.parse_args(argv)
    built = build(Path(args.dir))
    print("matrix1 " + " ".join(built))
    return 0


if __name__ == "__main__":
    sys.exit(main())
