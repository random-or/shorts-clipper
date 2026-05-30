"""Self-healing parallel trending video scout.

Design:
- Rotates through multiple search query pools so it never gets stuck
  on one topic cluster.
- Fetches video metadata in parallel (ThreadPoolExecutor) instead of
  N sequential subprocess calls — scout time goes from ~45s to ~8s.
- Maintains a local cache of already-processed video IDs (with TTL)
  so the same clip is never generated twice within 7 days.
- Automatically generates dynamic query variations using viral vocabulary.
"""

from __future__ import annotations

import json
import logging
import random
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

log = logging.getLogger(__name__)

_NICHE_ROTATION_INDEX = 0

TRENDING_TOPICS_FALLBACK = [
    "podcast", "drama", "gaming", "ai", "streamer", 
    "interview", "debate", "reaction", "opinion", "expose"
]


def _get_current_trending_keywords() -> list[str]:
    """Helper to fetch 5 trending videos and extract key noun/topic words."""
    entries = _search_entries("ytsearch5:trending")
    if not entries:
        return []

    words: list[str] = []
    stop_words = {
        "to", "in", "and", "the", "a", "of", "for", "on", "with", "how", "start",
        "trading", "stock", "market", "beginners", "free", "guide", "dubbed",
        "movie", "full", "hindi", "new", "release", "trending", "viral", "slowed",
        "reverb", "mashup", "love", "non", "stop", "instagram", "song", "songs",
        "video", "videos", "shorts", "short", "clip", "clips", "part", "episode",
        "chera", "tu", "nahi", "aisa", "main", "lo", "fi", "ultra", "4k", "south",
        "techno", "thriller", "best", "latest", "today", "now"
    }
    for entry in entries:
        title = entry.get("title", "")
        for word in re.findall(r"[a-zA-Z]{3,}", title.lower()):
            if word not in stop_words:
                words.append(word)
    return list(set(words))

# ---------------------------------------------------------------------------
# Query pools — rotated on each call, escalated on failure
# ---------------------------------------------------------------------------

TREND_POOLS: dict[str, list[str]] = {
    "drama": [
        "heated podcast argument english",
        "streamer rage moment english",
        "viral awkward interview english",
        "funniest reaction stream english",
    ],
    "motivation": [
        "cold motivational speech english",
        "street interview controversial opinion english",
        "insane sports commentary english",
        "celebrity uncomfortable moment english",
    ],
}

VIRAL_VOCABULARY = [
    "crashout",
    "aura",
    "locked in",
    "cooked",
    "standing on business",
    "cold moment",
    "nah bro",
    "this is insane",
    "villain arc",
    "generational",
    "cinema",
    "no way",
    "wild take",
    "exposed",
    "cooked him",
    "listen to this",
    "impossible",
    "awkward silence",
]

_CACHE_FILE = Path(".cache/shorts-clipper/scouted_ids.json")
_MIN_DURATION = 120  # seconds — exclude YouTube Shorts
_MAX_DURATION = 3600  # 1 hour cap
_MAX_WORKERS = 6  # parallel yt-dlp info fetches
_CACHE_TTL = 7 * 24 * 3600  # 7 days in seconds

# ---------------------------------------------------------------------------
# Curated fallback videos — used when all yt-dlp searches fail (rate limiting)
# ---------------------------------------------------------------------------

FALLBACK_VIDEOS: list[str] = [
    "https://www.youtube.com/watch?v=tJxfA5HJVAc",  # Top 200 Elden Ring Rage Moments
    "https://www.youtube.com/watch?v=Uq5SxQGW2HU",  # MrBeast intense challenge
    "https://www.youtube.com/watch?v=AzFBFHSqoKY",  # Heated debate compilation
    "https://www.youtube.com/watch?v=lTTajzrSkCU",  # Viral sports moments
    "https://www.youtube.com/watch?v=QJO3ROT-A4E",  # Streamer rage moments
    "https://www.youtube.com/watch?v=xm3YgoEiEDc",  # Podcast argument compilation
    "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo (classic)
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Never gonna give you up
]


class VideoCandidate(NamedTuple):
    url: str
    video_id: str
    duration: float
    title: str


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _load_cache() -> dict[str, float]:
    """Load seen-video cache, migrating old list format and pruning expired TTLs."""
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _CACHE_FILE.exists():
            data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            now = time.time()
            if isinstance(data, list):
                # Migrate old list format → dict with current timestamp
                return {vid: now for vid in data}
            if isinstance(data, dict):
                return {vid: ts for vid, ts in data.items() if now - ts < _CACHE_TTL}
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


def _generate_dynamic_queries(pool_name: str, count: int = 5) -> list[str]:
    """Build randomised search queries from a named pool + viral vocabulary."""
    base_queries = TREND_POOLS.get(pool_name, [])
    if not base_queries:
        return []

    results: set[str] = set()
    for _ in range(count):
        base = random.choice(base_queries)
        # 50 % chance to spice the query with a trending vocab word
        if random.random() > 0.5:
            vocab = random.choice(VIRAL_VOCABULARY)
            results.add(f"ytsearch5:{base} {vocab}")
        else:
            results.add(f"ytsearch5:{base}")
    return list(results)


def _search_entries(query: str) -> list[dict]:
    """Return flat playlist entries for a yt-dlp search query."""
    cmd = [
        "yt-dlp",
        query,
        "--flat-playlist",
        "--dump-single-json",
        "--retries",
        "2",
        "--socket-timeout",
        "10",
        "--quiet",
    ]
    # If the query is a channel URL or user page, limit to recent 15 videos to avoid long downloads
    if "youtube.com/" in query or query.startswith("http"):
        cmd.extend(["--playlist-end", "15"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=20)
        data = json.loads(result.stdout)
        return data.get("entries") or []
    except Exception as exc:  # noqa: BLE001
        log.warning("Search failed for query %r: %s", query, exc)
        return []


def _fetch_video_info(video_id: str) -> dict | None:
    """Fetch full metadata for a single video ID (safe to run in thread)."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--skip-download",
        "--socket-timeout",
        "10",
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
    """Return True only if the video is primarily English (ignoring auto-translated captions)."""
    subs = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    title = info.get("title", "").lower()

    # 1. Check yt-dlp language field if present
    lang = info.get("language")
    if lang:
        if not str(lang).lower().startswith("en"):
            return False

    # 2. If there's an original auto-caption that is NOT English, reject it
    # YouTube lists the original language auto-caption as '[lang]-orig' (e.g. 'es-orig', 'hi-orig')
    has_non_en_orig = any(k.endswith("-orig") and not k.startswith("en") for k in auto)
    if has_non_en_orig:
        return False

    # 3. Must have English manual subtitles or English auto-captions
    has_en_sub = bool("en" in subs or "en-orig" in subs or "en" in auto or "en-orig" in auto)
    if not has_en_sub:
        return False

    # 4. Reject obvious non-English titles (non-ASCII alpha chars)
    if any(ord(c) > 127 for c in title if c.isalpha()):
        return False

    return True


def _is_suitable(info: dict, seen: dict[str, float], max_age_days: int | None = None) -> bool:
    vid_id = info.get("id", "")
    duration = float(info.get("duration") or 0)
    
    if vid_id in seen or not (_MIN_DURATION <= duration <= _MAX_DURATION) or not _has_english(info):
        return False

    if max_age_days is not None:
        upload_date = info.get("upload_date")
        if not upload_date:
            return False
        try:
            upload_dt = datetime.strptime(upload_date, "%Y%m%d")
            age_days = (datetime.now() - upload_dt).total_seconds() / 86400.0
            if age_days > max_age_days:
                log.info("   [Skip] Candidate %s is too old (age=%.1f days > %d)", vid_id, age_days, max_age_days)
                return False
        except Exception:  # noqa: BLE001
            return False

    return True


# ---------------------------------------------------------------------------
# Virality scoring
# ---------------------------------------------------------------------------


def _calculate_virality_score(info: dict) -> float:
    """Score a video by view velocity + title emotional intensity."""
    view_count = float(info.get("view_count") or 0)
    upload_date = info.get("upload_date")
    title = info.get("title", "").lower()

    # Emotional keyword bonuses
    emotion_keywords = [
        "crashout",
        "insane",
        "crazy",
        "argument",
        "fight",
        "destroyed",
        "awkward",
        "silence",
        "rage",
        "cries",
        "emotional",
        "heated",
        "shocking",
        "exposed",
        "confrontation",
        "chaos",
        "explosive",
    ]
    title_intensity = sum(2.0 for kw in emotion_keywords if kw in title)

    # Penalty for generic/educational content
    weak_keywords = [
        "lecture",
        "tutorial",
        "course",
        "education",
        "calm",
        "relaxing",
        "slow",
        "explanation",
    ]
    if any(kw in title for kw in weak_keywords):
        title_intensity -= 10.0

    if not upload_date:
        return view_count + (title_intensity * 2_000)

    try:
        upload_dt = datetime.strptime(upload_date, "%Y%m%d")
        age_hours = max(1.0, (datetime.now() - upload_dt).total_seconds() / 3600.0)
        velocity = view_count / age_hours
        return velocity * (1.0 + title_intensity * 0.2)
    except Exception:  # noqa: BLE001
        return view_count + (title_intensity * 2_000)


# ---------------------------------------------------------------------------
# Core scout logic
# ---------------------------------------------------------------------------


def _scout_pool(
    query: str,
    seen: dict[str, float],
    max_age_days: int | None = None,
) -> list[tuple[float, VideoCandidate]]:
    """
    Search one query pool, filter & score candidates.

    Returns a (possibly empty) list of (score, VideoCandidate) pairs sorted
    descending by score — never None.
    """
    log.info("🔍 Searching: %s", query)
    entries = _search_entries(query)
    if not entries:
        log.warning("No entries returned for query: %s", query)
        return []

    ids = [e["id"] for e in entries if e.get("id") and e["id"] not in seen]
    if not ids:
        log.info("All results already seen for: %s", query)
        return []

    log.info("⚡ Fetching info for %d candidates in parallel...", len(ids))
    candidates: list[tuple[float, VideoCandidate]] = []

    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(ids))) as pool:
        futures = {pool.submit(_fetch_video_info, vid): vid for vid in ids}
        for future in as_completed(futures):
            info = future.result()
            if info and _is_suitable(info, seen, max_age_days):
                vid_id = info["id"]
                url = f"https://www.youtube.com/watch?v={vid_id}"
                title = info.get("title", "Unknown")
                duration = float(info.get("duration") or 0)
                score = _calculate_virality_score(info)
                candidates.append(
                    (
                        score,
                        VideoCandidate(url=url, video_id=vid_id, duration=duration, title=title),
                    )
                )
                log.info("🎯 Found valid candidate: [%s] %s (virality=%.2f)", vid_id, title, score)

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates


def get_trending_link(
    *,
    categories: list[str] | None = None,
    max_retries: int = 3,
    cache: bool = True,
    channel: str | None = None,
    niche: str | None = None,
    keyword: str | None = None,
) -> str | None:
    """
    Find a trending YouTube video suitable for clipping.

    Uses parallel multi-pool hunting across randomised queries and returns
    the highest-virality-scored candidate not yet seen.

    Args:
        categories: Optional subset of pool names to search (default: all).
        max_retries: Number of retry rounds if no candidate is found.
        cache: Whether to use/update the local seen-video cache.
        channel: Search only this channel's recent videos.
        niche: Build 5 targeted search queries around this niche and rotate between them.
        keyword: Search specifically for this term across multiple platforms.

    Returns:
        A YouTube URL string, or None if no suitable video was found.
    """
    seen = _load_cache() if cache else {}
    log.info("\n🚀 ADVANCED VIRAL SCOUT — %d seen IDs cached", len(seen))

    # Pre-build queries if specific options are provided
    fixed_queries: list[str] | None = None
    if channel:
        if channel.startswith(("http://", "https://")):
            channel_query = channel
        elif channel.startswith("@"):
            channel_query = f"https://www.youtube.com/{channel}/videos"
        else:
            channel_query = f"https://www.youtube.com/@{channel}/videos"
        fixed_queries = [channel_query]
        log.info("📢 Channel mode enabled. Target: %s", channel_query)
    elif niche:
        # 1. Fetch current trending keywords dynamically, with fallback
        trending_kws = _get_current_trending_keywords()
        if not trending_kws:
            trending_kws = TRENDING_TOPICS_FALLBACK

        # 2. Get current date/time context
        now = datetime.now()
        year_str = now.strftime("%Y")
        month_str = now.strftime("%B")
        day_str = now.strftime("%A")
        week_str = f"week {now.isocalendar()[1]}"

        # Define 5 premium queries with time context & trending keyword injection
        # to ensure results are completely fresh and relevant.
        global _NICHE_ROTATION_INDEX
        idx = _NICHE_ROTATION_INDEX
        
        kw1 = trending_kws[idx % len(trending_kws)]
        kw2 = trending_kws[(idx + 1) % len(trending_kws)]
        kw3 = trending_kws[(idx + 2) % len(trending_kws)]
        kw4 = trending_kws[(idx + 3) % len(trending_kws)]
        kw5 = trending_kws[(idx + 4) % len(trending_kws)]

        base_queries = [
            f"ytsearch5:viral {niche} {kw1} english {day_str} today",
            f"ytsearch5:best {niche} {kw2} highlights english this week {week_str}",
            f"ytsearch5:insane {niche} {kw3} moment english {month_str} {year_str}",
            f"ytsearch5:heated {niche} {kw4} debate english this month {year_str}",
            f"ytsearch5:shocking {niche} {kw5} revelation english {year_str} new",
        ]
        
        # Rotate the order of queries based on rotation index
        idx_rot = idx % len(base_queries)
        fixed_queries = base_queries[idx_rot:] + base_queries[:idx_rot]
        _NICHE_ROTATION_INDEX += 1
        log.info("📢 Niche mode (with trending & time context) enabled. Target niche: %s (rotated start index: %d)", niche, idx_rot)
    elif keyword:
        fixed_queries = [
            f"ytsearch5:{keyword}",
            f"scsearch5:{keyword}",
            f"gvsearch5:{keyword}",
            f"yvsearch5:{keyword}",
        ]
        log.info("📢 Keyword mode enabled. Target: %s (across multiple platforms)", keyword)

    available_pools = list(TREND_POOLS.keys())
    pools_to_search = (
        [c for c in categories if c in available_pools] if categories else available_pools
    )

    if not pools_to_search and not fixed_queries:
        log.error("No valid trend pools selected.")
        return None

    for attempt in range(1, max_retries + 1):
        if fixed_queries is not None:
            queries = list(fixed_queries)
        else:
            # Build queries across all active pools — fewer queries, run throttled
            queries = []
            for pool_name in pools_to_search:
                queries.extend(_generate_dynamic_queries(pool_name, count=3))
            random.shuffle(queries)
            queries = list(dict.fromkeys(queries))  # deduplicate, preserve shuffle order

        log.info(
            "🔥 Throttled hunting: %d unique queries (attempt %d/%d)",
            len(queries),
            attempt,
            max_retries,
        )

        all_candidates: list[tuple[float, VideoCandidate]] = []

        # Determine if we should enforce a 30-day age limit (e.g. in channel mode)
        max_age_days = 30 if channel else None

        # Run at most 2 searches concurrently to avoid rate-limiting.
        # Exit early as soon as we have at least one viable candidate.
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(_scout_pool, q, seen, max_age_days): q for q in queries}
            for future in as_completed(futures):
                results = future.result()
                all_candidates.extend(results)
                if all_candidates:
                    # Cancel remaining pending futures — we have what we need
                    for f in futures:
                        f.cancel()
                    log.info("⚡ Early exit — candidate found, skipping remaining queries.")
                    break

        if all_candidates:
            all_candidates.sort(key=lambda x: x[0], reverse=True)
            best_score, best_candidate = all_candidates[0]
            log.info(
                "🌟 Best candidate globally: [%s] %s (score=%.2f)",
                best_candidate.video_id,
                best_candidate.title,
                best_score,
            )

            if cache:
                seen[best_candidate.video_id] = time.time()
                _save_cache(seen)

            log.info(
                "✅ ACQUIRED: %s (%.0fs) — %s",
                best_candidate.video_id,
                best_candidate.duration,
                best_candidate.title,
            )
            return best_candidate.url

        wait = 2**attempt
        log.warning(
            "Attempt %d/%d: no candidates found. Waiting %ds before retry...",
            attempt,
            max_retries,
            wait,
        )
        time.sleep(wait)

    log.error("❌ Scout exhausted all pools after %d attempts.", max_retries)

    # Last resort: pick a random unseen video from the curated fallback list
    unseen_fallbacks = [url for url in FALLBACK_VIDEOS if url.split("v=")[-1] not in seen]
    if unseen_fallbacks:
        fallback_url = random.choice(unseen_fallbacks)
        vid_id = fallback_url.split("v=")[-1]
        log.warning("⚠️  Using curated fallback video: %s", fallback_url)
        if cache:
            seen[vid_id] = time.time()
            _save_cache(seen)
        return fallback_url

    log.error("All fallback videos already seen. Giving up.")
    return None
