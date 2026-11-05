from __future__ import annotations
"""Polite HTTP: descriptive User-Agent, per-host min spacing, retries w/ backoff, on-disk cache."""
import hashlib, json, os, time
from pathlib import Path
import requests

USER_AGENT = os.environ.get(
    "BRACKETOLOGY_UA", "bracketology-bot/0.1 (free open bracketology project; set BRACKETOLOGY_UA with contact)")
CACHE_DIR = Path(os.environ.get("BRACKETOLOGY_CACHE", "data/cache"))
# Minimum seconds between requests per host (Torvik robots.txt: Crawl-Delay 10; ncaa-api: 5 req/s limit).
MIN_SPACING = {"barttorvik.com": 10.0, "ncaa-api.henrygd.me": 0.5, "web.archive.org": 2.0}
_last: dict[str, float] = {}

class FetchError(RuntimeError):
    pass

def _host(url: str) -> str:
    return url.split("/")[2].removeprefix("www.")

def fetch(url: str, *, ttl: int = 3600, retries: int = 4, timeout: int = 60, allow_empty: bool = False) -> str:
    """GET url -> text. Cached for ttl seconds; stale cache is used if the network fails (graceful degradation)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = CACHE_DIR / hashlib.sha256(url.encode()).hexdigest()
    meta = key.with_suffix(".meta")
    if key.exists() and (key.stat().st_size or allow_empty) and time.time() - key.stat().st_mtime < ttl:
        return key.read_text(encoding="utf-8")
    host, last_err = _host(url), None
    for attempt in range(retries):
        wait = MIN_SPACING.get(host, 1.0) - (time.time() - _last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        _last[host] = time.time()
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
            if r.status_code == 200 and (r.text.strip() or allow_empty):
                key.write_text(r.text, encoding="utf-8")
                meta.write_text(json.dumps({"url": url, "fetched_at": time.time(), "status": 200}))
                return r.text
            last_err = f"HTTP {r.status_code}"
            if r.status_code in (400, 401, 403, 404):  # not transient; don't hammer
                break
        except requests.RequestException as e:
            last_err = repr(e)
        time.sleep(2 ** attempt)
    if key.exists():  # stale-but-better-than-nothing
        return key.read_text(encoding="utf-8")
    raise FetchError(f"{url}: {last_err}")
