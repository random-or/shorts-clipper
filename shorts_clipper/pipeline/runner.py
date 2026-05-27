"""Main pipeline runner — the orchestration brain.

Wires together every module into a single clean flow:
  Scout → Subtitles → Gemini → Download → Crop → Burn Subs → Output

Every step uses the package modules, Settings, and structured logging.
No more root-level flat scripts doing everything.
"""

from __future__ import annotations

import logging
import tempfile
from datetime import datetime
from pathlib import Path

from shorts_clipper.captions.generator import burn_subtitles
from shorts_clipper.core.exceptions import MediaProcessingError
from shorts_clipper.core.logging import configure_logging
from shorts_clipper.core.models import TranscriptSegment
from shorts_clipper.core.settings import Settings
from shorts_clipper.downloader.yt_dlp import download_clip, fetch_subtitles
from shorts_clipper.providers.gemini import GeminiProvider
from shorts_clipper.rendering.crop import process_to_vertical
from shorts_clipper.scout.trending import get_trending_link
from shorts_clipper.transcription.whisper import transcribe_clip

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-step helpers
# ---------------------------------------------------------------------------


def _get_segments_and_window(
    url: str,
    work_path: Path,
    settings: Settings,
) -> tuple[list[TranscriptSegment], float, float, str]:
    """
    Obtain transcript segments + best clip window via Gemini.

    Returns (segments, start_time, end_time, visual_layout).
    If native subtitles aren't available, falls back to local Whisper
    on a pre-downloaded micro-clip.
    """
    segments = fetch_subtitles(url, work_path)

    if segments:
        # Fast path: use native YouTube subtitles + Gemini
        provider = GeminiProvider(api_key=settings.gemini_api_key)
        window, layout = provider.select_clip_raw(segments)
        return segments, window.start, window.end, layout

    # Slow path: download a 30s sample and transcribe locally
    log.warning("⚠️  No native subtitles. Engaging local Whisper fallback...")
    micro_path = work_path / "micro_clip.mp4"
    start_time, end_time = 10.0, 40.0
    download_clip(url, micro_path, start_time=start_time, end_time=end_time)

    segments = transcribe_clip(
        micro_path,
        model_size=settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )
    return segments, start_time, end_time, "crop_center"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run(
    url: str,
    *,
    settings: Settings | None = None,
    output_path: Path | None = None,
) -> Path:
    """
    Run the full shorts clipping pipeline for a given YouTube URL.

    Args:
        url: YouTube video URL.
        settings: App settings (loaded from .env if not provided).
        output_path: Override output path (default: outputs/clip_TIMESTAMP.mp4).

    Returns:
        Path to the final output video.

    Raises:
        MediaProcessingError: If any stage of the pipeline fails.
    """
    if settings is None:
        settings = Settings.from_env()

    configure_logging(settings.log_level)
    log.info("🚀 PIPELINE START: %s", url)

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = settings.output_dir / f"clip_{ts}.mp4"

    with tempfile.TemporaryDirectory(prefix="shorts_clipper_") as work_dir:
        work_path = Path(work_dir)

        try:
            # ── Step 1 + 2: Subtitles + Gemini window selection ──────────
            segments, start_time, end_time, layout = _get_segments_and_window(
                url, work_path, settings
            )
            log.info(
                "📍 Clip window: %.1fs → %.1fs [%s]",
                start_time,
                end_time,
                layout,
            )

            # ── Step 3: Download the exact clip section ───────────────────
            micro_path = work_path / "micro_clip.mp4"
            if not micro_path.exists():
                download_clip(
                    url,
                    micro_path,
                    start_time=start_time,
                    end_time=end_time,
                )

            # ── Step 4: Vertical crop (pure FFmpeg, no MoviePy) ──────────
            log.info("\n--- VERTICAL CROP ---")
            cropped_path = work_path / "cropped.mp4"
            process_to_vertical(micro_path, cropped_path, layout=layout)

            # ── Step 5: Burn subtitles (FFmpeg ASS, not MoviePy) ─────────
            log.info("\n--- BURNING SUBTITLES ---")
            burn_subtitles(
                cropped_path,
                segments,
                start_offset=start_time,
                output_path=output_path,
            )

        except Exception as exc:
            log.exception("❌ PIPELINE FAILED")
            raise MediaProcessingError(str(exc)) from exc

    log.info("\n✅ SUCCESS — Clip ready at: %s", output_path)
    return output_path


def run_autopilot(settings: Settings | None = None) -> Path | None:
    """
    Autopilot mode: scout a trending video, then run the full pipeline.

    Returns the output path, or None if no suitable video was found.
    """
    if settings is None:
        settings = Settings.from_env()

    log.info("🤖 AUTOPILOT MODE: Scouting trending content...")
    url = get_trending_link()
    if not url:
        log.error("Scout returned no suitable video. Aborting.")
        return None

    return run(url, settings=settings)
