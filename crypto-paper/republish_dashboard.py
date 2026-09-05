"""Republish crypto-paper/dashboard to here.now using local .herenow state.

Never writes claim tokens, credentials, or .herenow into git. CoS owns live publish.
"""

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
DEFAULT_SLUG = "open-bodhi-a27f"
API = "https://here.now"
CRED_PATH = Path.home() / ".herenow" / "credentials"
STATE_PATH = ROOT / ".herenow" / "state.json"


def _api_key() -> str:
    env = (os.environ.get("HERENOW_API_KEY") or "").strip()
    if env:
        return env
    if CRED_PATH.exists():
        return CRED_PATH.read_text(encoding="utf-8").splitlines()[0].strip()
    return ""


def _local_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _state_record(slug: str) -> dict:
    state = _local_state()
    publishes = state.get("publishes") or {}
    rec = publishes.get(slug) or {}
    return rec if isinstance(rec, dict) else {}


def _headers(api_key: str) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-HereNow-Client": "cursor/dopamine-trading-crypto-paper",
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
        if path.name in skip or path.name.endswith(".bak") or ".bak" in path.name:
            continue
        if path.suffix in {".env", ".key", ".pem"}:
            continue
        rel = path.relative_to(folder).as_posix()
        if rel.startswith(".herenow/") or "claim" in rel.lower() or "token" in rel.lower():
            continue
        items.append((rel, path))
    return items


def publish(folder: Path, slug: str, api_key: str, claim_token: str = "") -> dict:
    files = collect_files(folder)
    if not files:
        raise RuntimeError(f"no dashboard files in {folder}")
    manifest = [{"path": name, "size": path.stat().st_size} for name, path in files]
    body: dict = {"files": manifest, "slug": slug}
    if claim_token and not api_key:
        body["claimToken"] = claim_token
    created = _json("POST", f"{API}/api/v1/publish", body, api_key)
    uploads = created.get("uploads") or created.get("files") or []
    by_path = {item.get("path"): item for item in uploads if isinstance(item, dict)}
    for name, path in files:
        target = by_path.get(name) or {}
        url = target.get("url") or target.get("uploadUrl")
        if not url:
            raise RuntimeError(f"missing upload url for {name}")
        ctype = (
            "text/html"
            if name.endswith(".html")
            else "application/javascript"
            if name.endswith(".js")
            else "application/octet-stream"
        )
        _put_bytes(url, path.read_bytes(), ctype)
    finalize_body = created.get("finalize") or {}
    if claim_token and not api_key and "claimToken" not in finalize_body:
        finalize_body = {**finalize_body, "claimToken": claim_token}
    finalize_url = created.get("finalizeUrl") or f"{API}/api/v1/publish/{slug}/finalize"
    finalized = _json("POST", finalize_url, finalize_body, api_key)
    site_url = finalized.get("siteUrl") or created.get("siteUrl") or f"https://{slug}.here.now/"
    return {
        "slug": slug,
        "siteUrl": site_url,
        "files": [name for name, _ in files],
        "anonymous": not bool(api_key),
    }


def republish(folder: Path | None = None, slug: str | None = None, dry_run: bool = False) -> dict:
    dest = Path(folder) if folder else DASHBOARD
    rec = _state_record(slug or "")
    resolved = slug or os.environ.get("HERENOW_SLUG") or rec.get("slug") or DEFAULT_SLUG
    rec = rec or _state_record(resolved)
    claim = ""
    if not _api_key():
        claim = str(rec.get("claimToken") or rec.get("claim_token") or "").strip()
    files = collect_files(dest)
    result = {
        "slug": resolved,
        "files": [name for name, _ in files],
        "siteUrl": rec.get("siteUrl") or f"https://{resolved}.here.now/",
        "dry_run": dry_run,
        "has_local_state": bool(rec),
        "has_claim": bool(claim),
    }
    if dry_run:
        return result
    published = publish(dest, resolved, _api_key(), claim_token=claim)
    published["has_local_state"] = bool(rec)
    published["has_claim"] = bool(claim)
    return published


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Republish crypto-paper dashboard to here.now.")
    parser.add_argument("--dir", default=str(DASHBOARD))
    parser.add_argument("--slug", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = republish(Path(args.dir), slug=args.slug or None, dry_run=args.dry_run)
    print(f"dashboard files: {', '.join(result.get('files') or []) or '(none)'}")
    print(result.get("siteUrl") or "")
    if result.get("dry_run"):
        print(f"dry-run slug={result.get('slug')} local_state={result.get('has_local_state')}")
        return 0
    if result.get("anonymous"):
        print("anonymous publish expires in 24h unless claimed (token not printed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
