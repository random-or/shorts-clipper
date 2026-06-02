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
from shorts_clipper.core.settings import Settings
from shorts_clipper.downloader.yt_dlp import download_audio, download_clip, fetch_subtitles
from shorts_clipper.providers.gemini import GeminiProvider
from shorts_clipper.rendering.crop import process_to_vertical
from shorts_clipper.scout.trending import get_trending_link
from shorts_clipper.social.youtube import upload_short
from shorts_clipper.transcription.whisper import transcribe_clip

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run(
    url: str,
    *,
    settings: Settings | None = None,
    output_path: Path | None = None,
    count: int = 1,
    upload: bool = False,
) -> Path | list[Path]:
    """
    Run the full shorts clipping pipeline for a given YouTube URL.

    Encode flow (2 passes — no triple re-encode):
      1. process_to_vertical   — scale + crop to 1080×1920
      2. burn_subtitles        — ASS subtitles + 1.15× pacing in one pass

    Args:
        url:         YouTube video URL.
        settings:    App settings (loaded from .env if not provided).
        output_path: Override output path (default: outputs/clip_TIMESTAMP.mp4).
                     If count > 1, files are saved as PATH_1.mp4, PATH_2.mp4, etc.
        count:       Number of clips to extract.

    Returns:
        Path to the final output video if count == 1, or list of Paths if count > 1.

    Raises:
        MediaProcessingError: If any stage of the pipeline fails.
    """
    if settings is None:
        settings = Settings.from_env()

    configure_logging(settings.log_level)
    log.info("🚀 PIPELINE START: %s (extracting %d clip(s))", url, count)

    settings.output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="shorts_clipper_") as work_dir:
        work_path = Path(work_dir)

        try:
            # ── PASS 1: ROUGH TRANSCRIPT FOR AI SELECTION ────────────────
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
            clips = provider.select_multiple_clips(rough_segments, count=count)

            output_paths: list[Path] = []

            for idx, (window, layout) in enumerate(clips, 1):
                log.info(
                    "\n--- PROCESSING CLIP %d/%d: %.1fs → %.1fs [%s] ---",
                    idx,
                    len(clips),
                    window.start,
                    window.end,
                    layout,
                )

                # Determine output path for this specific clip
                if output_path is not None:
                    if count > 1:
                        stem = output_path.stem
                        ext = output_path.suffix
                        current_output_path = output_path.parent / f"{stem}_{idx}{ext}"
                    else:
                        current_output_path = output_path
                else:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    if count > 1:
                        current_output_path = settings.output_dir / f"clip_{ts}_{idx}.mp4"
                    else:
                        current_output_path = settings.output_dir / f"clip_{ts}.mp4"

                clip_work_dir = work_path / f"clip_{idx}"
                clip_work_dir.mkdir(parents=True, exist_ok=True)
                micro_path = clip_work_dir / "micro_clip.mp4"

                # ── PASS 2: PRECISION TRANSCRIPTION ───────────────────────
                log.info("\n--- PASS 2: PRECISION TRANSCRIPTION ---")
                download_clip(url, micro_path, start_time=window.start, end_time=window.end)

                log.info(
                    "Running Whisper (%s) on micro-clip for word-level timing...",
                    settings.whisper_model,
                )
                precision_segments = transcribe_clip(
                    micro_path,
                    model_size=settings.whisper_model,
                    device=settings.whisper_device,
                    compute_type=settings.whisper_compute_type,
                )

                # ── Step 3: Vertical crop ─────────────────────────────────────
                log.info("\n--- VERTICAL CROP ---")
                cropped_path = clip_work_dir / "cropped.mp4"
                process_to_vertical(
                    micro_path,
                    cropped_path,
                    layout=layout,
                    video_codec=settings.video_codec,
                    preset=settings.video_preset,
                )

                # ── Step 4: Burn subtitles + 1.15× pacing (single pass) ───────
                log.info("\n--- BURNING SUBTITLES + PACING ---")
                burn_subtitles(
                    cropped_path,
                    precision_segments,
                    start_offset=0.0,  # precision segments are relative to micro_clip
                    output_path=current_output_path,
                    pacing=1.15,
                    video_codec=settings.video_codec,
                    preset=settings.video_preset,
                )

                try:
                    from shorts_clipper.render.thumbnailer import extract_thumbnail

                    extract_thumbnail(current_output_path)
                except Exception as thumb_err:
                    log.warning("Thumbnail extraction failed: %s", thumb_err)

                output_paths.append(current_output_path)
                log.info("✅ Clip %d ready at: %s", idx, current_output_path)

                if upload:
                    log.info("Uploading Clip %d to YouTube Shorts...", idx)
                    clip_title = f"AI Generated Short #{idx} #shorts #viral"
                    clip_desc = "Automatically generated by Shorts Clipper Autopilot."
                    upload_short(
                        str(current_output_path),
                        title=clip_title,
                        description=clip_desc,
                        tags=["shorts", "viral", "trending"],
                    )

        except Exception as exc:
            log.exception("❌ PIPELINE FAILED")
            raise MediaProcessingError(str(exc)) from exc

    if count == 1:
        log.info("\n✅ SUCCESS — Single clip ready at: %s", output_paths[0])
        return output_paths[0]

    log.info("\n✅ SUCCESS — %d clips generated successfully!", len(output_paths))
    return output_paths


def run_autopilot(
    settings: Settings | None = None,
    *,
    channel: str | None = None,
    niche: str | None = None,
    keyword: str | None = None,
    count: int = 1,
    upload: bool = False,
) -> Path | list[Path] | None:
    """
    Autopilot mode: scout a trending video, then run the full pipeline.

    Returns:
        Output path (or list of paths) on success, or None if no suitable video was found.
    """
    if settings is None:
        settings = Settings.from_env()

    log.info("🤖 AUTOPILOT MODE: Scouting trending content...")
    url = get_trending_link(
        channel=channel,
        niche=niche,
        keyword=keyword,
        max_age_days=settings.scout_max_age_days,
    )
    if not url:
        log.error("Scout returned no suitable video. Aborting.")
        return None

    return run(url, settings=settings, count=count, upload=upload)
