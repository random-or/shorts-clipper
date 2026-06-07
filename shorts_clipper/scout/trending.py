"""
Self-healing parallel trending video scout.
Completely redesigned with Staged Pipeline Architecture.
"""

from __future__ import annotations

import json
import logging
import os
import random
import subprocess
import threading
import time
from datetime import UTC, datetime, timedelta

from shorts_clipper.core.cache import get_cached, purge_expired, set_cached
from shorts_clipper.scout.keywords import build_queries
from shorts_clipper.scout.memory import get_successful_channels
from shorts_clipper.scout.metrics import ScoutMetrics
from shorts_clipper.scout.youtube_api import YouTubeAPIClient

log = logging.getLogger(__name__)

_MAX_SCOUT_WORKERS = int(os.getenv("SCOUT_MAX_WORKERS", "1"))
_BATCH_SIZE = int(os.getenv("SCOUT_BATCH_SIZE", "10"))
_YT_DLP_TIMEOUT = int(os.getenv("SCOUT_YT_DLP_TIMEOUT", "90"))
_MIN_DURATION = int(os.getenv("SCOUT_MIN_DURATION_S", "180"))
_MAX_DURATION = int(os.getenv("SCOUT_MAX_DURATION_S", "2400"))
_MIN_VIEWS = int(os.getenv("SCOUT_MIN_VIEWS", "1000"))
_AGE_RELAXATION_ALLOWED = str(os.getenv("SCOUT_ALLOW_AGE_RELAXATION", "true")).lower() == "true"

_failure_lock = threading.Lock()
_consecutive_yt_failures = 0
_yt_paused_until: float = 0.0


def _yt_circuit_breaker_check() -> bool:
    global _yt_paused_until
    with _failure_lock:
        if _yt_paused_until and time.time() < _yt_paused_until:
            log.warning(
                "yt-dlp circuit breaker open. Resuming at %s",
                datetime.fromtimestamp(_yt_paused_until).strftime("%H:%M:%S"),
            )
            return False
        return True


def _yt_record_failure() -> None:
    global _consecutive_yt_failures, _yt_paused_until
    with _failure_lock:
        _consecutive_yt_failures += 1
        if _consecutive_yt_failures >= 5:
            _yt_paused_until = time.time() + 120
            log.warning(
                "yt-dlp: %d consecutive failures. Circuit breaker open for 2 minutes.",
                _consecutive_yt_failures,
            )
            _consecutive_yt_failures = 0


def _yt_record_success() -> None:
    global _consecutive_yt_failures
    with _failure_lock:
        _consecutive_yt_failures = 0


def _get_base_yt_dlp_cmd() -> list[str]:
    import sys

    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--extractor-args",
        "youtube:player_client=default,-android_sdkless",
    ]
    try:
        import curl_cffi  # noqa: F401

        cmd.extend(["--impersonate", "Chrome"])
    except ImportError:
        pass
    proxy_str = os.getenv("SHORTS_PROXY")
    if proxy_str:
        proxies = [p.strip() for p in proxy_str.split(",") if p.strip()]
        if proxies:
            cmd.extend(["--proxy", random.choice(proxies)])
    return cmd


def _is_cancelled(job_id: str | None) -> bool:
    if not job_id:
        return False
    try:
        from shorts_clipper.core.queue import JobQueue

        job = JobQueue().get(job_id)
        return job is not None and job.get("status") == "cancelled"
    except Exception:
        return False


def fetch_metadata_batch(video_ids: list[str]) -> list[dict]:
    if not video_ids:
        return []
    results = []
    for i in range(0, len(video_ids), _BATCH_SIZE):
        batch = video_ids[i : i + _BATCH_SIZE]
        urls = [f"https://www.youtube.com/watch?v={vid}" for vid in batch]
        if not _yt_circuit_breaker_check():
            break
        cmd = (
            _get_base_yt_dlp_cmd()
            + [
                "--dump-json",
                "--skip-download",
                "--retries",
                "1",
                "--socket-timeout",
                "20",
                "--quiet",
                "--no-warnings",
            ]
            + urls
        )
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=_YT_DLP_TIMEOUT)
            _yt_record_success()
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except subprocess.TimeoutExpired:
            _yt_record_failure()
            log.warning("Batch metadata fetch timed out for %d videos", len(batch))
        except Exception as exc:
            _yt_record_failure()
            log.warning("Batch metadata fetch failed: %s", exc)
    return results


def compute_virality_score(video: dict, now: datetime) -> float:
    import math

    try:
        pub_str = video.get("published_at") or video.get("upload_date") or ""
        if pub_str and len(pub_str) == 8 and pub_str.isdigit():
            published = datetime.strptime(pub_str, "%Y%m%d").replace(tzinfo=UTC)
        elif pub_str:
            published = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        else:
            return 0.0
    except Exception:
        return 0.0

    now_utc = now.replace(tzinfo=UTC) if now.tzinfo is None else now
    hours_live = max((now_utc - published).total_seconds() / 3600, 1)

    views = max(video.get("view_count", 0), 1)
    likes = video.get("like_count", 0)
    comments = video.get("comment_count", 0)

    velocity_raw = views / hours_live
    velocity_score = min(10.0, math.log1p(velocity_raw) / math.log1p(10_000) * 10)

    like_ratio = likes / views
    engagement_score = min(10.0, like_ratio * 250)

    comment_ratio = comments / views
    comment_score = min(10.0, comment_ratio * 1000)

    recency_score = 10.0 * math.exp(-hours_live / (7 * 24) * math.log(2))

    w_vel = float(os.getenv("SCOUT_WEIGHT_VELOCITY", "0.45"))
    w_eng = float(os.getenv("SCOUT_WEIGHT_ENGAGEMENT", "0.25"))
    w_com = float(os.getenv("SCOUT_WEIGHT_COMMENTS", "0.15"))
    w_rec = float(os.getenv("SCOUT_WEIGHT_RECENCY", "0.15"))

    score = (
        velocity_score * w_vel
        + engagement_score * w_eng
        + comment_score * w_com
        + recency_score * w_rec
    )
    video["_score_breakdown"] = {
        "velocity": velocity_score,
        "engagement": engagement_score,
        "comments": comment_score,
        "recency": recency_score,
        "total": score,
    }
    return round(score, 3)


def _get_attempt_max_age(base_days: int, attempt: int) -> int | None:
    if attempt == 1:
        return base_days
    if attempt == 2 and base_days >= 90 and _AGE_RELAXATION_ALLOWED:
        relaxed = base_days * 2
        log.warning(
            "Scout: no candidates in %d days. Relaxing to %d days (user window >= 90d).",
            base_days,
            relaxed,
        )
        return relaxed
    log.warning("Scout: exhausted all attempts for %d-day window. Returning None.", base_days)
    return None


def _has_english(info: dict) -> bool:
    subs = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    title = info.get("title", "").lower()
    lang = info.get("language")
    if lang and not str(lang).lower().startswith("en"):
        return False
    has_non_en_orig = any(k.endswith("-orig") and not k.startswith("en") for k in auto)
    if has_non_en_orig:
        return False
    has_en_sub = bool("en" in subs or "en-orig" in subs or "en" in auto or "en-orig" in auto)
    if not has_en_sub:
        return False
    if any(ord(c) > 127 for c in title if c.isalpha()):
        return False
    return True


def _discover_via_api(
    client: YouTubeAPIClient, query: str, cutoff: datetime, metrics: ScoutMetrics
) -> list[dict]:
    import re

    normalized_query = re.sub(r"^ytsearch\d*:", "", query).strip()
    video_ids = client.search(normalized_query, published_after=cutoff)
    if not video_ids:
        return []
    metrics.video_ids_discovered += len(video_ids)
    details = client.get_video_details(video_ids)
    results = []
    for item in details:
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        content = item.get("contentDetails", {})
        results.append(
            {
                "id": item["id"],
                "title": snippet.get("title", ""),
                "published_at": snippet.get("publishedAt", ""),
                "channel_id": snippet.get("channelId", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "language": snippet.get("defaultAudioLanguage", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "duration_s": client.parse_duration_seconds(content.get("duration", "PT0S")),
                "_source": "youtube_api",
                "_source_query": query,
            }
        )
    return results


def _discover_via_ytdlp(query: str, max_age_days: int, metrics: ScoutMetrics) -> list[dict]:
    if not _yt_circuit_breaker_check():
        return []
    cmd = _get_base_yt_dlp_cmd()
    if max_age_days:
        query += f" dateafter:now-{max_age_days}days"
    cmd.extend(
        [
            query,
            "--dump-json",
            "--skip-download",
            "--flat-playlist",
            "--retries",
            "1",
            "--socket-timeout",
            "15",
            "--quiet",
        ]
    )
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_YT_DLP_TIMEOUT)
        _yt_record_success()
        videos = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line:
                try:
                    v = json.loads(line)
                    v["_source_query"] = query
                    videos.append(v)
                except Exception:
                    continue
        metrics.video_ids_discovered += len(videos)
        return videos
    except Exception as exc:
        _yt_record_failure()
        log.warning("yt-dlp flat search failed for %s: %s", query, exc)
        return []


def get_trending_link(
    *,
    categories: list[str] | None = None,
    max_retries: int = 3,
    cache: bool = True,
    channel: str | None = None,
    niche: str | None = None,
    keyword: str | None = None,
    max_age_days: int | None = 90,
    job_id: str | None = None,
) -> str | None:
    purge_expired()
    metrics = ScoutMetrics(
        niche=niche or "", keyword=keyword or "", time_window_days=max_age_days or 0
    )
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    client = YouTubeAPIClient(api_key) if api_key else None
    now = datetime.now(UTC)

    try:
        for attempt in range(1, 4):
            if _is_cancelled(job_id):
                metrics.finish(None, "Cancelled by user")
                return None

            actual_max_age_days = _get_attempt_max_age(max_age_days or 90, attempt)
            if actual_max_age_days is None:
                metrics.finish(None, "No candidates within allowed time window")
                log.error(
                    "No suitable videos found within your selected time window. Try a longer window or different niche."
                )
                return None

            cutoff = now - timedelta(days=actual_max_age_days)
            queries = []

            # Stage 1: Discovery
            known_channels = get_successful_channels(niche or "tech")
            if channel:
                queries.append(f"ytsearch15:from:{channel}")
            elif attempt == 1 and known_channels:
                for kc in known_channels[:2]:
                    queries.append(f"ytsearch15:from:{kc}")
            else:
                if not known_channels and attempt == 1:
                    log.info("No learning data for niche '%s'. Using fresh discovery.", niche)
                queries.extend(build_queries(niche or "tech", keyword))

            discovered = []
            for q in queries:
                if _is_cancelled(job_id):
                    return None
                metrics.queries_fired += 1
                if client and client.searches_available:
                    metrics.api_used = True
                    discovered.extend(_discover_via_api(client, q, cutoff, metrics))
                else:
                    discovered.extend(_discover_via_ytdlp(q, actual_max_age_days, metrics))

            if not discovered:
                continue

            metrics.queries_with_results += 1
            survivors = []

            # Stages 2 & 3: Freshness & Quality
            for video in discovered:
                vid = video.get("id")
                if not vid or get_cached(vid):
                    continue

                if video.get("_source") == "youtube_api":
                    try:
                        pub = datetime.fromisoformat(video["published_at"].replace("Z", "+00:00"))
                        if (now - pub).days > actual_max_age_days:
                            metrics.rejected_too_old += 1
                            continue
                    except Exception:
                        pass

                dur = float(video.get("duration") or video.get("duration_s") or 0)
                if dur > 0:
                    if dur < _MIN_DURATION:
                        metrics.rejected_too_short += 1
                        continue
                    if dur > _MAX_DURATION:
                        metrics.rejected_too_long += 1
                        continue

                views = int(video.get("view_count") or 0)
                if views > 0 and views < _MIN_VIEWS:
                    metrics.rejected_low_views += 1
                    continue

                survivors.append(video)

            if not survivors:
                continue

            # Stage 4: Virality Scoring
            for v in survivors:
                v["_score"] = compute_virality_score(v, now)
            survivors.sort(key=lambda x: x["_score"], reverse=True)
            # Stages 5, 6, 7: Optimized Metadata Enrichment & Winner Selection
            finalists = []
            for v in survivors:
                if _is_cancelled(job_id):
                    return None
                vid = v.get("id")

                # Check cache first
                has_english = False
                c = get_cached(vid)
                if c and "has_english" in c:
                    metrics.cache_hits += 1
                    has_english = c["has_english"]
                else:
                    metrics.cache_misses += 1

                    has_english_api = None
                    if client and getattr(client, "has_english_captions", None):
                        has_english_api = client.has_english_captions(vid)

                    if has_english_api is not None:
                        # API succeeded. Spoof subtitles to reuse _has_english filtering for title/language
                        v_copy = v.copy()
                        v_copy["subtitles"] = {"en": []} if has_english_api else {}
                        has_english = _has_english(v_copy)
                    else:
                        # Fallback to yt-dlp only if API failed/unavailable
                        metrics.yt_dlp_calls += 1
                        fetched = fetch_metadata_batch([vid])
                        if fetched:
                            has_english = _has_english(fetched[0])

                    # Update the API dictionary with the flag so we remember
                    v["has_english"] = has_english
                    set_cached(vid, v, int(os.getenv("SCOUT_METADATA_CACHE_TTL", "6")))

                if not has_english:
                    metrics.rejected_no_subtitles += 1
                    continue

                finalists.append(v)
                break  # Single finalist enrichment

            if finalists:
                winner = finalists[0]
                # Re-score is technically optional since it was the highest already, but preserves behavior
                winner["_score"] = compute_virality_score(winner, now)
                metrics.winner_virality_score = winner.get("_score", 0.0)
                metrics.winning_query = winner.get("_source_query", "")
                metrics.finish(winner)
                vid = winner.get("id")
                log.info("✅ ACQUIRED: %s - %s", vid, winner.get("title"))
                return f"https://www.youtube.com/watch?v={vid}"

        metrics.finish(None, "Exhausted all retries")
        return None
    except Exception as exc:
        metrics.finish(None, f"Error: {exc}")
        return None
