"""Assemble dashboard/ live1 files. Stub over the checked-in index + dash.js."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DASHBOARD = ROOT / "dashboard"
REQUIRED = ("index.html", "dash.js")


def build(dest: Path | None = None) -> list[str]:
    folder = Path(dest) if dest else DASHBOARD
    folder.mkdir(parents=True, exist_ok=True)
    missing = [name for name in REQUIRED if not (folder / name).is_file()]
    if missing:
        raise RuntimeError(f"dashboard missing {', '.join(missing)} under {folder}")
    html = (folder / "index.html").read_text(encoding="utf-8")
    if "dash.js?v=live1" not in html:
        raise RuntimeError("index.html must load dash.js?v=live1")
    return [str((folder / name).relative_to(ROOT)) for name in REQUIRED]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build/verify live1 dashboard files.")
    parser.add_argument("--dir", default=str(DASHBOARD))
    args = parser.parse_args(argv)
    built = build(Path(args.dir))
    print("live1 " + " ".join(built))
    return 0


if __name__ == "__main__":
    sys.exit(main())
