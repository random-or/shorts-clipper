"""Main pipeline runner — the orchestration brain.

Wires together every module into a single clean flow:
  Scout → Subtitles → Gemini → Download → Crop → Burn Subs → Output

Pipeline encode passes:
  Pass 1 — crop + scale to vertical (lossless-ish CRF 18)
  Pass 2 — burn ASS subtitles + 1.15× pacing in ONE combined ffmpeg call

No intermediate re-encode for pacing; it is baked into the subtitle step
so we never triple-encode the video.
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
from shorts_clipper.downloader.yt_dlp import download_audio, download_clip, fetch_subtitles
from shorts_clipper.providers.gemini import GeminiProvider
from shorts_clipper.rendering.crop import process_to_vertical
from shorts_clipper.scout.trending import get_trending_link
from shorts_clipper.transcription.whisper import transcribe_clip

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-step helpers
# ---------------------------------------------------------------------------


def _get_window_and_segments(
    url: str,
    work_path: Path,
    settings: Settings,
) -> tuple[list[TranscriptSegment], float, float, str]:
    """
    Two-pass architecture for maximum speed and precision.

    Pass 1 — fetch native subtitles (or tiny Whisper) so Gemini can pick
              the best window without downloading the whole video.
    Pass 2 — download only the selected micro-clip, then run the full
              Whisper model for word-level timestamps.

    Returns:
        (precision_segments, window_start, window_end, layout_str)
    """
    log.info("\n--- PASS 1: ROUGH TRANSCRIPT FOR AI SELECTION ---")
    rough_segments = fetch_subtitles(url, work_path)

    if not rough_segments:
        log.warning(
            "⚠️  No native subtitles. Downloading 5-min audio sample for rough transcript..."
        )
        audio_path = work_path / "rough_audio.m4a"
        download_audio(url, audio_path, start_time=0.0, end_time=300.0)
        rough_segments = transcribe_clip(
            audio_path,
            model_size="tiny.en",
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )

    provider = GeminiProvider(api_key=settings.gemini_api_key)
    window, layout = provider.select_clip_raw(rough_segments)

    log.info("\n--- PASS 2: PRECISION TRANSCRIPTION ---")
    micro_path = work_path / "micro_clip.mp4"
    download_clip(url, micro_path, start_time=window.start, end_time=window.end)

    log.info("Running Whisper (%s) on micro-clip for word-level timing...", settings.whisper_model)
    precision_segments = transcribe_clip(
        micro_path,
        model_size=settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )

    return precision_segments, window.start, window.end, layout


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

    Encode flow (2 passes — no triple re-encode):
      1. process_to_vertical   — scale + crop to 1080×1920
      2. burn_subtitles        — ASS subtitles + 1.15× pacing in one pass

    Args:
        url:         YouTube video URL.
        settings:    App settings (loaded from .env if not provided).
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
            # ── Steps 1-2: Two-pass transcript + AI selection ─────────────
            segments, start_time, end_time, layout = _get_window_and_segments(
                url, work_path, settings
            )
            log.info(
                "📍 Clip window: %.1fs → %.1fs (%.1fs) [%s]",
                start_time,
                end_time,
                end_time - start_time,
                layout,
            )

            micro_path = work_path / "micro_clip.mp4"

            # ── Step 3: Vertical crop ─────────────────────────────────────
            log.info("\n--- VERTICAL CROP ---")
            cropped_path = work_path / "cropped.mp4"
            process_to_vertical(micro_path, cropped_path, layout=layout)

            # ── Step 4: Burn subtitles + 1.15× pacing (single pass) ───────
            log.info("\n--- BURNING SUBTITLES + PACING ---")
            burn_subtitles(
                cropped_path,
                segments,
                start_offset=0.0,  # precision segments are relative to micro_clip
                output_path=output_path,
                pacing=1.15,
            )

        except Exception as exc:
            log.exception("❌ PIPELINE FAILED")
            raise MediaProcessingError(str(exc)) from exc

    log.info("\n✅ SUCCESS — Clip ready at: %s", output_path)
    return output_path


def run_autopilot(settings: Settings | None = None) -> Path | None:
    """
    Autopilot mode: scout a trending video, then run the full pipeline.

    Returns:
        Output path on success, or None if no suitable video was found.
    """
    if settings is None:
        settings = Settings.from_env()

    log.info("🤖 AUTOPILOT MODE: Scouting trending content...")
    url = get_trending_link()
    if not url:
        log.error("Scout returned no suitable video. Aborting.")
        return None

    return run(url, settings=settings)
