"""
Self-healing parallel trending video scout.
Completely redesigned with Staged Pipeline Architecture.
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import subprocess
import threading
import time
from datetime import UTC, datetime, timedelta

from shorts_clipper.core.cache import get_cached, purge_expired, set_cached
from shorts_clipper.core.models import TranscriptSegment, TranscriptWord
from shorts_clipper.core.settings import Settings
from shorts_clipper.downloader.yt_dlp import fetch_subtitles, get_subtitle_metrics
from shorts_clipper.highlight_detection.scoring import RuleBasedHighlightScorer
from shorts_clipper.providers.gemini import GeminiProvider
from shorts_clipper.scout.keywords import build_queries
from shorts_clipper.scout.metrics import ScoutMetrics
from shorts_clipper.scout.youtube_api import YouTubeAPIClient

log = logging.getLogger(__name__)


def _is_english_key(k: str) -> bool:
    k_lower = k.lower().strip()
    return k_lower == "en" or k_lower.startswith("en-")




def compute_scout_v2_intermediate_score(
    video: dict, now: datetime, channel_history: dict[str, dict]
) -> float:
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

    views = max(int(video.get("view_count") or 0), 1)
    likes = int(video.get("like_count") or 0)
    comments = int(video.get("comment_count") or 0)

    views_velocity = views / hours_live

    # Cap velocity logarithmically (max 15.0)
    velocity_score = min(15.0, math.log1p(views_velocity) * 1.5)

    # Cap engagement (max 15.0)
    engagement_ratio = (likes + (comments * 2)) / views if views > 0 else 0
    engagement_score = min(15.0, engagement_ratio * 150)

    # Recency (max 10.0)
    recency_bonus = 10.0 if hours_live < 24 else (5.0 if hours_live < 72 else 0.0)

    # Momentum (max 5.0)
    momentum_score = min(5.0, math.log1p(likes) / math.log1p(10_000) * 5)

    # Channel Feedback (max 15.0)
    channel_id = video.get("channel_id", "")
    channel_bonus = 0.0
    if channel_id in channel_history:
        stats = channel_history[channel_id]
        channel_bonus = min(
            15.0, stats.get("success_count", 0) * 2.5 + stats.get("avg_virality", 0.0) * 0.1
        )

    # Subtitle quality hint
    lang_bonus = 0.0
    lang = video.get("language")
    if lang and str(lang).lower().startswith("en"):
        lang_bonus = 2.0

    score = (
        velocity_score
        + engagement_score
        + recency_bonus
        + momentum_score
        + channel_bonus
        + lang_bonus
    )
    return round(score, 2)


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
            results_found = False
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    results.append(json.loads(line))
                    results_found = True
                except json.JSONDecodeError:
                    continue
            
            if result.returncode == 0 or results_found:
                _yt_record_success()
            else:
                err_str = result.stderr or ""
                log.error(
                    "Batch metadata fetch failed (exit code %d). Stderr: %s",
                    result.returncode,
                    err_str,
                )
                if "429" in err_str or "too many requests" in err_str.lower():
                    log.warning(
                        "YouTube THROTTLING/RATE LIMIT (429) detected during metadata fetch!"
                    )
                elif "403" in err_str:
                    log.warning("YouTube Access Forbidden (403) detected during metadata fetch!")
                _yt_record_failure()
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

    views_velocity = views / hours_live
    velocity_score = views_velocity / 1000

    engagement_ratio = (likes + (comments * 2)) / views if views > 0 else 0
    engagement_score = min(20.0, engagement_ratio * 200)

    recency_bonus = 15.0 if hours_live < 24 else (5.0 if hours_live < 72 else 0.0)

    momentum_score = math.log1p(likes) / math.log1p(10_000) * 5

    score = velocity_score + engagement_score + recency_bonus + momentum_score

    video["_score_breakdown"] = {
        "velocity": round(velocity_score, 2),
        "engagement": round(engagement_score, 2),
        "recency": round(recency_bonus, 2),
        "momentum": round(momentum_score, 2),
        "base_total": round(score, 2),
    }
    return round(score, 2)


def _get_attempt_max_age(base_days: int, attempt: int) -> int | None:
    if attempt == 1:
        return base_days
    if attempt == 2:
        relaxed = max(base_days * 2, 30) if base_days < 30 else base_days * 2
        log.warning("Scout: no candidates found. Relaxing window to %d days.", relaxed)
        return relaxed
    if attempt == 3:
        relaxed = max(base_days * 4, 90)
        log.warning("Scout: still no candidates. Relaxing window to %d days.", relaxed)
        return base_days * 10
    return None


def _has_english(info: dict) -> bool:
    subs = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    title = info.get("title", "").lower()
    lang = info.get("language")
    if lang and not str(lang).lower().startswith("en"):
        return False
    has_non_en_orig = any(k.endswith("-orig") and not _is_english_key(k) for k in auto)
    if has_non_en_orig:
        return False
    has_en_sub = any(_is_english_key(k) for k in subs) or any(_is_english_key(k) for k in auto)
    if not has_en_sub:
        return False
    strict_ascii = str(os.getenv("SCOUT_STRICT_ASCII", "true")).lower() == "true"
    if strict_ascii and any(ord(c) > 127 for c in title if c.isalpha()):
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
                "view_count": int(stats.get("viewCount") or 0),
                "like_count": int(stats.get("likeCount") or 0),
                "comment_count": int(stats.get("commentCount") or 0),
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
        cmd.extend(["--dateafter", f"now-{max_age_days}days"])
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

        if result.returncode == 0 or videos:
            _yt_record_success()
        else:
            err_str = result.stderr or ""
            log.error(
                "yt-dlp flat search failed (exit code %d). Stderr: %s", result.returncode, err_str
            )
            if "429" in err_str or "too many requests" in err_str.lower():
                log.warning("YouTube THROTTLING/RATE LIMIT (429) detected during search!")
            elif "403" in err_str:
                log.warning("YouTube Access Forbidden (403) detected during search!")
            _yt_record_failure()
            return []

        metrics.video_ids_discovered += len(videos)
        return videos
    except Exception as exc:
        _yt_record_failure()
        log.warning("yt-dlp flat search failed for %s: %s", query, exc)
        return []


# removed _transcribe_mp_worker


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
    log.info(f"SCOUT RECEIVED:\nniche={niche}\nkeyword={keyword}")
    import uuid
    job_id_str = job_id or str(uuid.uuid4())[:8]
    metrics = ScoutMetrics(
        run_id=job_id_str, niche=niche or "", keyword=keyword or "", time_window_days=max_age_days or 0
    )
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    client = YouTubeAPIClient(api_key) if api_key else None
    now = datetime.now(UTC)

    settings = Settings.from_env()

    # Load channel history for feedback ranking bonus (Bug #1 Fix: filter by niche)
    channel_history = {}
    try:
        import sqlite3
        from pathlib import Path

        db_path = Path("outputs/scout_memory.db")
        if db_path.exists():
            import contextlib
            with contextlib.closing(sqlite3.connect(db_path, check_same_thread=False)) as con:
                rows = con.execute(
                    "SELECT channel_id, success_count, avg_virality, niche FROM successful_channels"
                ).fetchall()

            channel_history = {
                r[0]: {"success_count": r[1], "avg_virality": r[2], "niche": r[3]} for r in rows
            }
    except Exception as e:
        log.warning("Failed to load channel history for feedback loop: %s", e)

    try:
        for attempt in range(1, 4):
            if _is_cancelled(job_id):
                metrics.finish(None, "Cancelled by user")
                return None

            actual_max_age_days = _get_attempt_max_age(max_age_days or 90, attempt)
            if actual_max_age_days is None:
                metrics.finish(None, "No candidates within allowed time window")
                log.error(
                    "No videos found.\n"
                    "Reason breakdown:\n"
                    f"- {metrics.rejected_no_subtitles} rejected: missing subtitles\n"
                    f"- {metrics.rejected_too_long} rejected: duration too long\n"
                    f"- {metrics.rejected_too_short} rejected: duration too short\n"
                    f"- {metrics.rejected_too_old} rejected: too old\n"
                    f"- {metrics.rejected_low_views} rejected: low views"
                )
                return None

            cutoff = now - timedelta(days=actual_max_age_days)
            queries = []

            # Stage 1: Discovery

            # Parse multiple niches
            niches = [n.strip() for n in (niche or "tech").split(",")]

            if channel:
                queries.append(f"ytsearch15:from:{channel}")
            else:
                for current_niche in niches:
                    current_queries = []
                    if attempt == 1 and not keyword:
                        # Find channels that match this exact niche
                        niche_channels = [
                            cid
                            for cid, stats in channel_history.items()
                            if stats.get("niche")
                            and current_niche.lower() in stats.get("niche", "").lower()
                        ]
                        if niche_channels:
                            for kc in niche_channels[:2]:
                                current_queries.append(f"ytsearch15:from:{kc} {current_niche}")

                        # Always include generic discovery to maintain diversity
                        current_queries.extend(build_queries(current_niche, keyword))
                    else:
                        current_queries.extend(build_queries(current_niche, keyword))
                    queries.extend(current_queries)

            discovered = []
            for q in queries:
                if _is_cancelled(job_id):
                    return None
                log.info("DISCOVERY QUERY: %s", q)
                metrics.queries_fired += 1
                if client and client.searches_available:
                    metrics.api_used = True
                    discovered.extend(_discover_via_api(client, q, cutoff, metrics))
                else:
                    discovered.extend(_discover_via_ytdlp(q, actual_max_age_days, metrics))

            if not discovered:
                continue

            # Deduplicate discovered videos
            unique_discovered = []
            seen_ids = set()
            for video in discovered:
                vid = video.get("id")
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    unique_discovered.append(video)
            discovered = unique_discovered

            metrics.queries_with_results += 1

            # ── PHASE 1.5: SEMANTIC RELEVANCE GATE ────────────────────────
            from shorts_clipper.scout.relevance import SemanticRelevanceGate

            gate = SemanticRelevanceGate(keyword=keyword or "", niche=niche or "")
            discovered = gate.filter_candidates(discovered)

            if not discovered:
                log.warning("Semantic Relevance Gate rejected all candidates.")
                continue

            survivors = []

            # Stages 2 & 3: Freshness & Quality
            for video in discovered:
                vid = video.get("id")
                if not vid or get_cached(vid):
                    continue

                title_lower = video.get("title", "").lower()

                # ── PHASE 3: HARD FILTERS ─────────────────────────────
                niche_lower = niche.lower() if niche else ""

                if niche_lower == "ai":
                    music_terms = [
                        "music video",
                        "official music video",
                        "lyrics",
                        "remix",
                        "song",
                        "audio",
                        "live performance",
                    ]
                    if any(term in title_lower for term in music_terms):
                        log.info("Rejected video %s: music content in AI niche", vid)
                        continue

                if "tech" in niche_lower:
                    demo_terms = [
                        "8k",
                        "hdr",
                        "dolby",
                        "test video",
                        "demo",
                        "visual showcase",
                        "4k 60fps",
                    ]
                    if any(term in title_lower for term in demo_terms):
                        log.info("Rejected video %s: visual demo in Tech niche", vid)
                        continue

                # Reject non-English videos (checks subtitles, captions, language, and ascii title)
                if not _has_english(video):
                    log.info("Rejected video %s: non-English content detected", vid)
                    metrics.rejected_low_quality += 1
                    continue
                # ──────────────────────────────────────────────────────

                if video.get("_source") == "youtube_api":
                    try:
                        pub = datetime.fromisoformat(video["published_at"].replace("Z", "+00:00"))
                        if (now - pub).days > actual_max_age_days:
                            metrics.rejected_too_old += 1
                            log.info("Rejected video %s: too old", vid)
                            continue
                    except Exception:
                        pass

                dur = float(video.get("duration") or video.get("duration_s") or 0)
                if dur > 0:
                    if dur < _MIN_DURATION:
                        metrics.rejected_too_short += 1
                        log.info("Rejected video %s: duration too short", vid)
                        continue
                    if dur > _MAX_DURATION:
                        metrics.rejected_too_long += 1
                        log.info("Rejected video %s: duration too long", vid)
                        continue

                views = int(video.get("view_count") or 0)
                if views > 0 and views < _MIN_VIEWS:
                    metrics.rejected_low_views += 1
                    log.info("Rejected video %s: views below threshold", vid)
                    continue

                survivors.append(video)

            if not survivors:
                continue

            # Stage 4: Intermediate Virality Scoring (Capped Multi-Dimensional)
            for v in survivors:
                v["_score"] = compute_scout_v2_intermediate_score(v, now, channel_history)
            survivors.sort(key=lambda x: x["_score"], reverse=True)

            # ══════════════════════════════════════════════════════════════
            # STAGE A: Cheap metadata-only ranking (no transcription)
            # ══════════════════════════════════════════════════════════════
            finalist_pool_limit = int(os.getenv("SCOUT_FINALIST_LIMIT", "15"))
            max_per_category = max(1, int(finalist_pool_limit * 0.40))  # Max 40% per category

            def _categorize(title: str) -> str:
                t = title.lower()
                if any(x in t for x in ["phone", "iphone", "pixel", "galaxy", "smartphone"]):
                    return "phones"
                if any(x in t for x in ["macbook", "laptop", "pc", "computer", "desktop"]):
                    return "pc_hardware"
                if any(
                    x in t for x in ["ai", "gpt", "openai", "claude", "gemini", "anthropic", "llm"]
                ):
                    return "ai"
                if any(x in t for x in ["camera", "lens", "sony", "canon", "lumix"]):
                    return "cameras"
                if any(
                    x in t for x in ["game", "nintendo", "xbox", "playstation", "ps5", "switch"]
                ):
                    return "gaming"
                return "general_tech"

            all_finalists = []
            category_counts = {}

            for v in survivors:
                if len(all_finalists) >= finalist_pool_limit:
                    break
                cat = _categorize(v.get("title", ""))
                if category_counts.get(cat, 0) < max_per_category:
                    all_finalists.append(v)
                    category_counts[cat] = category_counts.get(cat, 0) + 1

            if all_finalists:
                log.info("\n========== SCOUT STAGE A: METADATA RANKING (DIVERSIFIED) ==========")
                log.info(f"{'Rank':<5} | {'Video ID':<11} | {'Views':<10} | {'Score':<8} | Title")
                for idx, v in enumerate(all_finalists, 1):
                    log.info(
                        f"{idx:<5} | {v.get('id', ''):<11} | {v.get('view_count', 0):<10} | {v.get('_score', 0):<8} | {v.get('title', '')[:50]}"
                    )
                log.info("=====================================================")

            # Stage A gate: keep only top 3 for expensive evaluation
            stage_b_limit = int(os.getenv("SCOUT_STAGE_B_LIMIT", "3"))
            finalists = all_finalists[:stage_b_limit]

            if len(all_finalists) > stage_b_limit:
                log.info(
                    "[SCOUT] Stage A complete: %d candidates ranked, top %d promoted to Stage B. "
                    "%d candidates eliminated without transcription.",
                    len(all_finalists),
                    len(finalists),
                    len(all_finalists) - len(finalists),
                )

            # ══════════════════════════════════════════════════════════════
            # STAGE B: Expensive evaluation (subtitle fetch + Gemini)
            # ══════════════════════════════════════════════════════════════
            winner = None
            evaluated_count = 0
            winning_threshold = float(os.getenv("SCOUT_WINNING_THRESHOLD", "75"))

            settings = Settings.from_env()

            import tempfile
            from pathlib import Path

            from shorts_clipper.highlight_detection.scoring import LocalTranscriptScorer

            with tempfile.TemporaryDirectory(prefix="scout_eval_") as temp_dir:
                temp_path = Path(temp_dir)

                local_scored_candidates = []
                stage_b_target = int(os.getenv("SCOUT_STAGE_B_LIMIT", "3"))

                # Iterate through all finalists until we successfully score enough
                for v in all_finalists:
                    if len(local_scored_candidates) >= stage_b_target:
                        break

                    vid = v.get("id")
                    candidate_start_time = time.time()
                    timing = {
                        "subtitle_fetch_s": 0.0,
                        "transcript_s": 0.0,
                        "gemini_s": 0.0,
                        "total_s": 0.0,
                    }
                    log.info(
                        "Fetching subtitles for candidate (Video ID: %s): %s", vid, v.get("title")
                    )

                    # ── PHASE 4: SUBTITLE-FIRST FILTER ──────────────────
                    has_native_subs = False
                    segments = []
                    transcript_source = "none"

                    cached_data = get_cached(vid)
                    if cached_data and "transcript_segments" in cached_data:
                        segments_data = cached_data["transcript_segments"]
                        for s in segments_data:
                            words = [TranscriptWord(**w) for w in s.get("words", [])]
                            segments.append(
                                TranscriptSegment(
                                    start=s["start"],
                                    end=s["end"],
                                    text=s["text"],
                                    words=words,
                                    speaker=s.get("speaker"),
                                )
                            )
                        log.info("Loaded transcript from cache for video %s", vid)
                        transcript_source = "cache"
                        has_native_subs = cached_data.get("has_native_subs", True)
                    else:
                        metrics.cache_misses += 1
                        t_sub_start = time.time()
                        from shorts_clipper.core.exceptions import (
                            SUBTITLE_NOT_AVAILABLE,
                            YOUTUBE_RATE_LIMIT_429,
                        )
                        from shorts_clipper.scout.subtitle_cache import get_status, set_status

                        cache_status = get_status(vid)
                        if cache_status == "RATE_LIMITED":
                            log.warning(
                                "[429 CACHED] %s queued, score=%.2f, retry in 60s",
                                vid,
                                v.get("_score", 0),
                            )
                            continue

                        try:
                            segments = fetch_subtitles(
                                f"https://www.youtube.com/watch?v={vid}", temp_path
                            )
                            set_status(vid, "AVAILABLE")
                            has_native_subs = True
                            transcript_source = "native"
                        except YOUTUBE_RATE_LIMIT_429:
                            set_status(vid, "RATE_LIMITED")
                            log.warning(
                                "[429 QUARANTINE] %s queued, score=%.2f, retry in 60s",
                                vid,
                                v.get("_score", 0),
                            )
                            time.sleep(15)  # Cooldown API to prevent cascading limits
                            continue
                        except SUBTITLE_NOT_AVAILABLE:
                            set_status(vid, "MISSING")
                            log.info(
                                "[SCOUT] skipped: no subtitles for %s — TRANSCRIPT_UNAVAILABLE", vid
                            )
                            metrics.rejected_no_subtitles += 1
                            continue
                        timing["subtitle_fetch_s"] = round(time.time() - t_sub_start, 2)

                        if segments:
                            v_copy = v.copy()
                            v_copy["has_native_subs"] = has_native_subs
                            v_copy["transcript_segments"] = [
                                {
                                    "start": s.start,
                                    "end": s.end,
                                    "text": s.text,
                                    "words": [
                                        {
                                            "start": w.start,
                                            "end": w.end,
                                            "word": w.word,
                                            "probability": w.probability,
                                        }
                                        for w in s.words
                                    ],
                                    "speaker": s.speaker,
                                }
                                for s in segments
                            ]
                            set_cached(vid, v_copy, int(os.getenv("SCOUT_METADATA_CACHE_TTL", "6")))

                    if not segments:
                        log.warning("Candidate %s rejected: Empty or failed transcript.", vid)
                        metrics.rejected_low_quality += 1
                        continue

                    # Score transcript locally
                    evaluated_count += 1
                    local_scorer = LocalTranscriptScorer()
                    local_score, best_local_window, local_reasoning = local_scorer.score_transcript(
                        segments
                    )
                    log.info("Candidate %s local transcript score: %.2f", vid, local_score)

                    local_scored_candidates.append(
                        {
                            "video": v,
                            "local_score": local_score,
                            "local_reasoning": local_reasoning,
                            "segments": segments,
                            "transcript_source": transcript_source,
                            "has_native_subs": has_native_subs,
                            "best_local_window": best_local_window,
                            "timing": timing,
                            "candidate_start_time": candidate_start_time,
                        }
                    )

                # PHASE 2: Gemini ONLY on highest scoring local candidate
                passing_candidates = []
                if local_scored_candidates:
                    local_scored_candidates.sort(key=lambda x: x["local_score"], reverse=True)
                    top_candidate = local_scored_candidates[0]

                    v = top_candidate["video"]
                    vid = v.get("id")
                    segments = top_candidate["segments"]
                    local_score = top_candidate["local_score"]
                    best_local_window = top_candidate["best_local_window"]
                    timing = top_candidate["timing"]
                    candidate_start_time = top_candidate["candidate_start_time"]
                    transcript_source = top_candidate["transcript_source"]
                    has_native_subs = top_candidate["has_native_subs"]

                    log.info("\n========== FINALIST SELECTED ==========")
                    log.info(
                        "Video %s selected as finalist with Local Score: %.2f", vid, local_score
                    )
                    log.info("Calling Gemini ONCE for timestamp extraction...")

                    t_gemini_start = time.time()
                    highlights = []
                    provider = GeminiProvider(api_key=settings.gemini_api_key)
                    gemini_failed = False
                    try:
                        highlights = provider.select_multiple_clips_detailed(segments, count=1)
                    except Exception as gemini_err:
                        log.warning(
                            "[SCOUT] Gemini unavailable or failed for %s: %s", vid, gemini_err
                        )
                        gemini_failed = True

                    valid_highlights = [h for h in highlights if h.get("virality_score", 0) >= 85]
                    timing["gemini_s"] = round(time.time() - t_gemini_start, 2)

                    # PHASE 4: FALLBACK MODE
                    if not valid_highlights:
                        if gemini_failed:
                            if True:
                                log.warning("[FALLBACK] Local transcript scorer selected clip due to API failure.")
                                start_t = best_local_window[0].start if best_local_window else 0.0
                                end_t = best_local_window[-1].end if best_local_window else 60.0
                                if end_t - start_t < 15.0:
                                    end_t = start_t + 45.0

                                valid_highlights = [
                                    {
                                        "start": start_t,
                                        "end": end_t,
                                        "layout": "crop_center",
                                        "virality_score": int(local_score),
                                        "reason": f"[FALLBACK] Local Transcript Scorer: {top_candidate.get('local_reasoning', 'Selected fallback clip')}",
                                    }
                                ]
                            else:
                                log.warning(
                                    "Fallback candidate rejected: Local score %.1f is below threshold 75",
                                    local_score,
                                )
                        else:
                            log.info(
                                "Top candidate %s rejected: Gemini virality score too low", vid
                            )
                    # Calculate final components for reporting
                    max_ai_score = max(h.get("virality_score", 0) for h in valid_highlights)
                    ai_points = max_ai_score * 0.4

                    scorer = RuleBasedHighlightScorer()
                    max_rule_hook, max_rule_emotion, max_rule_virality, total_caption_density = (
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                    )
                    for seg in segments:
                        seg_score = scorer.score_segment(seg)
                        max_rule_hook = max(max_rule_hook, seg_score.hook)
                        max_rule_emotion = max(max_rule_emotion, seg_score.emotion)
                        max_rule_virality = max(max_rule_virality, seg_score.virality)
                        total_caption_density += seg_score.caption_density
                    avg_caption_density = total_caption_density / len(segments) if segments else 0.0

                    rule_hook_points = min(10.0, max_rule_hook * 5.0)
                    rule_emotion_points = min(10.0, max_rule_emotion * 5.0)
                    rule_virality_points = min(10.0, max_rule_virality * 5.0)

                    views = max(v.get("view_count", 0), 1)
                    likes = v.get("like_count", 0)
                    comments = v.get("comment_count", 0)
                    pub_str = v.get("published_at") or v.get("upload_date") or ""
                    try:
                        pub_dt = (
                            datetime.strptime(pub_str, "%Y%m%d").replace(tzinfo=UTC)
                            if len(pub_str) == 8 and pub_str.isdigit()
                            else datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                        )
                    except Exception:
                        pub_dt = now

                    hours_live = max(
                        (now.replace(tzinfo=UTC) - pub_dt.replace(tzinfo=UTC)).total_seconds()
                        / 3600,
                        1,
                    )
                    views_velocity = views / hours_live
                    velocity_points = min(10.0, math.log1p(views_velocity) * 1.0)
                    engagement_ratio = (likes + (comments * 2)) / views
                    engagement_points = min(10.0, engagement_ratio * 100)

                    subtitle_quality = 10.0 if transcript_source in ("native", "cache") else 0.0

                    channel_id = v.get("channel_id", "")
                    channel_bonus = 0.0
                    if channel_id in channel_history:
                        stats = channel_history[channel_id]
                        channel_bonus = min(
                            15.0,
                            stats.get("success_count", 0) * 2.5
                            + stats.get("avg_virality", 0.0) * 0.1,
                        )

                    final_score = round(
                        ai_points
                        + rule_hook_points
                        + rule_emotion_points
                        + rule_virality_points
                        + velocity_points
                        + engagement_points
                        + channel_bonus
                        + subtitle_quality,
                        2,
                    )
                    timing["total_s"] = round(time.time() - candidate_start_time, 2)

                    if valid_highlights:
                        passing_candidates.append(
                            {
                                "video": v,
                                "final_score": final_score,
                                "valid_highlights": valid_highlights,
                                "rule_virality_points": rule_virality_points,
                                "rule_hook_points": rule_hook_points,
                                "rule_emotion_points": rule_emotion_points,
                                "avg_caption_density": avg_caption_density,
                                "subtitle_quality": subtitle_quality,
                                "momentum_score": min(
                                    5.0, math.log1p(likes) / math.log1p(10_000) * 5
                                ),
                                "likes": likes,
                                "has_native_subs": has_native_subs,
                                "timing": timing,
                            }
                        )

                if passing_candidates:
                    passing_candidates.sort(key=lambda x: x["final_score"], reverse=True)
                    best = passing_candidates[0]
                    v = best["video"]
                    vid = v.get("id")

                    log.info("\n========== EVALUATION RESULTS ==========\n")
                    log.info(f"{'Rank':<5} | {'Video':<12} | {'Final Score':<11}\n")
                    for rank_idx, pc in enumerate(passing_candidates, 1):
                        log.info(
                            f"{rank_idx:<5} | {pc['video'].get('id', ''):<12} | {pc['final_score']:<11}"
                        )
                    log.info(f"\nWinner: {vid}\n")

                    eval_times = [
                        pc["timing"]["total_s"] for pc in passing_candidates if "timing" in pc
                    ]
                    if eval_times:
                        log.info("PERFORMANCE SUMMARY:")
                        log.info("  Slowest candidate: %.1fs", max(eval_times))
                        log.info("  Fastest candidate: %.1fs", min(eval_times))
                        log.info("  Average eval time: %.1fs", sum(eval_times) / len(eval_times))

                    final_score = best["final_score"]
                    valid_highlights = best["valid_highlights"]
                    rule_virality_points = best["rule_virality_points"]
                    rule_hook_points = best["rule_hook_points"]
                    rule_emotion_points = best["rule_emotion_points"]
                    avg_caption_density = best["avg_caption_density"]
                    subtitle_quality = best["subtitle_quality"]
                    momentum_score = best["momentum_score"]
                    likes = best["likes"]
                    has_native_subs = best["has_native_subs"]

                    # Cache the selected clips under video ID
                    v_cached = get_cached(vid) or v.copy()
                    v_cached["selected_clips"] = [
                        {
                            "start": h["start"],
                            "end": h["end"],
                            "layout": h["layout"],
                            "virality_score": h["virality_score"],
                            "reason": h.get("reason", ""),
                        }
                        for h in valid_highlights
                    ]
                    set_cached(vid, v_cached, int(os.getenv("SCOUT_METADATA_CACHE_TTL", "6")))

                    # Generate scout_report.json
                    report = {
                        "video_id": vid,
                        "title": v.get("title", ""),
                        "relevance": round(rule_virality_points, 1),
                        "hook_score": round(rule_hook_points, 1),
                        "emotion_score": round(rule_emotion_points, 1),
                        "story_score": round(avg_caption_density * 10.0, 1),
                        "subtitle_quality": round(subtitle_quality, 1),
                        "momentum": round(momentum_score * 2.0, 1),
                        "final_score": final_score,
                        "selected_reason": valid_highlights[0].get(
                            "reason", "Strong structural hook and conversational velocity."
                        ),
                    }

                    try:
                        import uuid
                        job_suffix = f"_{job_id}" if job_id else f"_{uuid.uuid4().hex[:8]}"
                        report_path = Path(f"outputs/scout_report{job_suffix}.json")
                        report_path.parent.mkdir(parents=True, exist_ok=True)
                        report_path.write_text(
                            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
                        )
                        log.info("💾 Saved Scout V2 Explainability Report: %s", report_path)
                    except Exception as report_err:
                        log.warning("Failed to write scout_report.json: %s", report_err)

                    winner = v
                    winner["_score"] = final_score

            if winner:
                sub_metrics = get_subtitle_metrics()
                metrics.subtitle_fetch_success = sub_metrics.get("fetch_success", 0)
                metrics.subtitle_fetch_failure = sub_metrics.get("fetch_failure", 0)
                metrics.subtitle_429_count = sub_metrics.get("rate_limit_429", 0)

                if "eval_times" in locals() and eval_times:
                    metrics.avg_eval_time_s = sum(eval_times) / len(eval_times)
                    metrics.slowest_eval_time_s = max(eval_times)
                    metrics.fastest_eval_time_s = min(eval_times)

                metrics.winner_virality_score = winner.get("_score", 0.0)
                metrics.winning_query = winner.get("_source_query", "")
                metrics.finish(winner)
                vid = winner.get("id")

                log.info(
                    "Scout V2 Summary:\n"
                    f"- Candidates discovered: {metrics.video_ids_discovered}\n"
                    f"- Survivors: {len(survivors)}\n"
                    f"- Finalists evaluated: {evaluated_count}\n"
                    f"- Winner: {vid} ({winner.get('title')})"
                )
                result_url = f"https://www.youtube.com/watch?v={vid}"
                log.info("SCOUT RETURNING: %s", repr(result_url))
                return result_url

        metrics.finish(None, "No high-quality highlights found")
        log.error("❌ Scout V2: No candidate met the quality bar. Aborting cleanly.")
        log.info("SCOUT RETURNING: %s", repr(None))
        return None
    except Exception as exc:
        metrics.finish(None, f"Error: {exc}")
        log.info("SCOUT RETURNING: %s", repr(None))
        return None
