"""Write crypto-paper/dashboard/data.json. Optional here.now republish hook."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from engine import DATA_PATH, PaperBroker

ROOT = Path(__file__).resolve().parent
DASHBOARD = ROOT / "dashboard"
DASH_DATA = DASHBOARD / "data.json"


def sync(data_path: Path | None = None, dest: Path | None = None, republish: bool = False) -> Path:
    src = Path(data_path) if data_path else DATA_PATH
    out = Path(dest) if dest else DASH_DATA
    out.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copyfile(src, out)
    else:
        snap = PaperBroker.load(path=src).snapshot()
        out.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    if republish:
        from republish_dashboard import republish as do_republish

        do_republish(DASHBOARD)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync CRYPTO PAPER snapshot into dashboard/.")
    parser.add_argument("--data", default=str(DATA_PATH))
    parser.add_argument("--dest", default=str(DASH_DATA))
    parser.add_argument("--republish", action="store_true", help="Optional here.now republish after write.")
    args = parser.parse_args(argv)
    dest = sync(Path(args.data), Path(args.dest), republish=args.republish)
    rel = dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest
    print(f"synced {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
