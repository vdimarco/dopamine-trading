"""Publish dashboard/ to here.now as the live1 site. Never writes secrets into git."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DASHBOARD = ROOT / "dashboard"
DEFAULT_SLUG = "lucid-tablet-tgx3"
API = "https://here.now"
CRED_PATH = Path.home() / ".herenow" / "credentials"


def _api_key() -> str:
    env = (os.environ.get("HERENOW_API_KEY") or "").strip()
    if env:
        return env
    if CRED_PATH.exists():
        return CRED_PATH.read_text(encoding="utf-8").splitlines()[0].strip()
    return ""


def _headers(api_key: str) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-HereNow-Client": "cursor/dopamine-trading-paper",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _json(method: str, url: str, body: dict | None, api_key: str) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=_headers(api_key), method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} -> {exc.code}: {detail}") from exc
    return json.loads(raw) if raw else {}


def _put_bytes(url: str, blob: bytes, content_type: str) -> None:
    req = urllib.request.Request(
        url,
        data=blob,
        headers={"Content-Type": content_type},
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        resp.read()


def collect_files(folder: Path) -> list[tuple[str, Path]]:
    skip = {".DS_Store", "data.json"}
    items: list[tuple[str, Path]] = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        if path.name in skip or path.name.endswith(".bak"):
            continue
        rel = path.relative_to(folder).as_posix()
        items.append((rel, path))
    return items


def publish(folder: Path, slug: str, api_key: str) -> dict:
    files = collect_files(folder)
    if not files:
        raise RuntimeError(f"no dashboard files in {folder}")
    manifest = [{"path": name, "size": path.stat().st_size} for name, path in files]
    created = _json("POST", f"{API}/api/v1/publish", {"files": manifest, "slug": slug}, api_key)
    uploads = created.get("uploads") or created.get("files") or []
    by_path = {item.get("path"): item for item in uploads if isinstance(item, dict)}
    for name, path in files:
        target = by_path.get(name) or {}
        url = target.get("url") or target.get("uploadUrl")
        if not url:
            raise RuntimeError(f"missing upload url for {name}")
        ctype = "text/html" if name.endswith(".html") else "application/javascript" if name.endswith(".js") else "application/octet-stream"
        _put_bytes(url, path.read_bytes(), ctype)
    finalize_url = created.get("finalizeUrl") or f"{API}/api/v1/publish/{slug}/finalize"
    finalized = _json("POST", finalize_url, created.get("finalize") or {}, api_key)
    site_url = finalized.get("siteUrl") or created.get("siteUrl") or f"https://{slug}.here.now/"
    return {
        "slug": slug,
        "siteUrl": site_url,
        "files": [name for name, _ in files],
        "anonymous": not bool(api_key),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Republish dashboard/ to here.now (live1).")
    parser.add_argument("--dir", default=str(DASHBOARD))
    parser.add_argument("--slug", default=os.environ.get("HERENOW_SLUG") or DEFAULT_SLUG)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    folder = Path(args.dir)
    files = collect_files(folder)
    print(f"dashboard files: {', '.join(name for name, _ in files) or '(none)'}")
    if args.dry_run:
        print(f"dry-run slug={args.slug}")
        return 0
    result = publish(folder, args.slug, _api_key())
    print(result["siteUrl"])
    if result["anonymous"]:
        print("anonymous publish expires in 24h (HERENOW_API_KEY not set)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
