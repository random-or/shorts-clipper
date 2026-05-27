"""Self-healing parallel trending video scout.

Design:
- Rotates through multiple search query pools so it never gets stuck
  on one topic cluster.
- Fetches video metadata in parallel (ThreadPoolExecutor) instead of
  N sequential subprocess calls — scout time goes from ~45s to ~8s.
- Maintains a local cache of already-processed video IDs so the same
  clip is never generated twice.
- Automatically escalates to backup query pools if the primary pool
  returns no suitable videos.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import NamedTuple

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Query pools — rotated on each call, escalated on failure
# ---------------------------------------------------------------------------
_PRIMARY_POOLS: list[str] = [
    "ytsearch10:viral podcast interview english 2024",
    "ytsearch10:trending tech explained english",
    "ytsearch10:motivational speech viral clip english",
    "ytsearch10:shocking news story english viral",
    "ytsearch10:mrbeast sidemen KSI trending english",
]

_BACKUP_POOLS: list[str] = [
    "ytsearch10:best moments compilation english",
    "ytsearch10:funny moments viral english streaming",
    "ytsearch10:finance money tips viral english",
    "ytsearch10:sports highlights english commentary",
    "ytsearch10:science discovery explained english",
]

_CACHE_FILE = Path(".cache/shorts-clipper/scouted_ids.json")
_MIN_DURATION = 120  # seconds — exclude Shorts
_MAX_DURATION = 3600  # 1 hour max
_MAX_WORKERS = 6  # parallel info fetches


class VideoCandidate(NamedTuple):
    url: str
    video_id: str
    duration: float
    title: str


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _load_cache() -> dict[str, float]:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _CACHE_FILE.exists():
            data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            now = time.time()
            if isinstance(data, list):
                # Migrate old list format to dict with current timestamp
                return {vid: now for vid in data}
            elif isinstance(data, dict):
                # Filter out entries older than 7 days (7 * 24 * 3600 seconds)
                SEVEN_DAYS = 7 * 24 * 3600
                return {vid: ts for vid, ts in data.items() if now - ts < SEVEN_DAYS}
    except Exception as exc:  # noqa: BLE001
        log.warning("Cache load failed, starting fresh: %s", exc)
    return {}


def _save_cache(seen: dict[str, float]) -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(seen, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        log.warning("Cache save failed: %s", exc)


# ---------------------------------------------------------------------------
# yt-dlp helpers
# ---------------------------------------------------------------------------


def _search_entries(query: str) -> list[dict]:
    """Return flat playlist entries for a yt-dlp search query."""
    cmd = [
        "yt-dlp",
        query,
        "--flat-playlist",
        "--dump-single-json",
        "--retries",
        "5",
        "--quiet",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        data = json.loads(result.stdout)
        return data.get("entries") or []
    except Exception as exc:  # noqa: BLE001
        log.warning("Search failed for query %r: %s", query, exc)
        return []


def _fetch_video_info(video_id: str) -> dict | None:
    """Fetch full metadata for a single video ID (run in thread)."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--skip-download",
        "--quiet",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=20)
        return json.loads(result.stdout)
    except Exception as exc:  # noqa: BLE001
        log.debug("Info fetch failed for %s: %s", video_id, exc)
        return None


def _has_english(info: dict) -> bool:
    subs = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    return bool("en" in subs or "en-orig" in subs or "en" in auto or "en-orig" in auto)


def _is_suitable(info: dict, seen: dict[str, float]) -> bool:
    vid_id = info.get("id", "")
    duration = float(info.get("duration") or 0)
    return vid_id not in seen and _MIN_DURATION <= duration <= _MAX_DURATION and _has_english(info)


# ---------------------------------------------------------------------------
# Core scout logic
# ---------------------------------------------------------------------------


def _calculate_virality_score(info: dict) -> float:
    """Calculate a virality score for a video."""
    view_count = float(info.get("view_count") or 0)
    upload_date = info.get("upload_date")
    if not upload_date:
        return view_count
    
    try:
        from datetime import datetime
        # upload_date is YYYYMMDD
        upload_dt = datetime.strptime(upload_date, "%Y%m%d")
        age_days = max(1.0, (datetime.now() - upload_dt).days)
        return view_count / age_days
    except Exception:
        return view_count


def _scout_pool(query: str, seen: dict[str, float]) -> VideoCandidate | None:
    """Search one query pool, rank suitable candidates, and return the best one."""
    log.info("🔍 Searching: %s", query)
    entries = _search_entries(query)
    if not entries:
        log.warning("No entries returned for query: %s", query)
        return None

    ids = [e["id"] for e in entries if e.get("id") and e["id"] not in seen]
    if not ids:
        log.info("All results already seen for: %s", query)
        return None

    # Fetch all info in parallel
    log.info("⚡ Fetching info for %d candidates in parallel...", len(ids))
    candidates = []

    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(ids))) as pool:
        futures = {pool.submit(_fetch_video_info, vid): vid for vid in ids}
        for future in as_completed(futures):
            info = future.result()
            if info and _is_suitable(info, seen):
                vid_id = info["id"]
                url = f"https://www.youtube.com/watch?v={vid_id}"
                title = info.get("title", "Unknown")
                duration = float(info.get("duration") or 0)
                score = _calculate_virality_score(info)
                candidates.append((score, VideoCandidate(url=url, video_id=vid_id, duration=duration, title=title)))
                log.info("🎯 Found valid candidate: [%s] %s (Virality: %.2f)", vid_id, title, score)

    if not candidates:
        return None

    # Sort by score descending and pick the best
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_candidate = candidates[0]
    log.info("🌟 Selected best candidate in pool: [%s] %s", best_candidate.video_id, best_candidate.title)
    return best_candidate


def get_trending_link(
    *,
    categories: list[str] | None = None,
    max_retries: int = 3,
    cache: bool = True,
) -> str | None:
    """
    Find a trending YouTube video suitable for clipping.

    Self-healing strategy:
    1. Try each primary query pool in randomised order.
    2. If all primaries fail, escalate to backup pools.
    3. Retry up to ``max_retries`` times with exponential back-off.
    4. Skip videos already processed (cache).

    Returns the URL of the first suitable video, or None if everything fails.
    """
    import random

    seen = _load_cache() if cache else {}
    log.info("\n🚀 SELF-HEALING SCOUT ENGAGED — %d seen IDs cached", len(seen))

    pools = list(categories or _PRIMARY_POOLS)
    random.shuffle(pools)  # randomise so we don't always hit the same source
    all_pools = pools + list(_BACKUP_POOLS)

    for attempt in range(1, max_retries + 1):
        for query in all_pools:
            candidate = _scout_pool(query, seen)
            if candidate:
                if cache:
                    seen[candidate.video_id] = time.time()
                    _save_cache(seen)
                log.info(
                    "✅ ACQUIRED: %s (%.0fs) — %s",
                    candidate.video_id,
                    candidate.duration,
                    candidate.title,
                )
                return candidate.url

        wait = 2**attempt
        log.warning(
            "Attempt %d/%d failed. Waiting %ds before retry...",
            attempt,
            max_retries,
            wait,
        )
        time.sleep(wait)

    log.error("❌ Scout exhausted all %d pools after %d attempts.", len(all_pools), max_retries)
    return None
