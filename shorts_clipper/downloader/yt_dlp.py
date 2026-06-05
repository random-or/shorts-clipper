"""yt-dlp video downloader with subtitle fetching."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from shorts_clipper.core.models import TranscriptSegment

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Subtitle fetching + SRT parsing
# ---------------------------------------------------------------------------


def _srt_time_to_seconds(t: str) -> float:
    h, m, s_ms = t.split(":")
    s, ms = s_ms.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def fetch_subtitles(url: str, work_dir: Path) -> list[TranscriptSegment]:
    """
    Download English subtitles (auto or manual) from YouTube.

    Returns parsed TranscriptSegment list, or empty list if unavailable.
    """
    log.info("\n--- FETCHING NATIVE ENGLISH SUBTITLES ---")
    output_base = work_dir / "subs"
    cmd = [
        "yt-dlp",
        "--extractor-args",
        "youtube:player_client=default,-android_sdkless",
        "--write-auto-subs",
        "--write-subs",
        "--sub-lang",
        "en,en-orig",
        "--sub-format",
        "srt",
        "--skip-download",
        "--socket-timeout",
        "15",
        "--retries",
        "3",
        "-o",
        str(output_base),
        url,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        log.warning("Subtitle fetch timed out for %s — will rely on Whisper", url)
        return []
    except subprocess.CalledProcessError:
        log.warning("No English auto-subtitles found for %s", url)
        return []

    srt_files = list(work_dir.glob("subs.en*.srt"))
    if not srt_files:
        return []

    srt_path = srt_files[0]
    content = srt_path.read_text(encoding="utf-8")

    blocks = re.split(r"\n\s*\n", content.strip())
    segments: list[TranscriptSegment] = []
    for block in blocks:
        lines = block.split("\n")
        if len(lines) >= 3:
            times = re.findall(r"(\d+:\d+:\d+,\d+)", lines[1])
            if len(times) == 2:
                start = _srt_time_to_seconds(times[0])
                end = _srt_time_to_seconds(times[1])
                text = " ".join(lines[2:]).strip()
                segments.append(TranscriptSegment(start=start, end=end, text=text))

    log.info("✅ Loaded %d English subtitle segments.", len(segments))
    return segments


def download_audio(
    url: str,
    output_path: str | Path,
    *,
    start_time: float | None = None,
    end_time: float | None = None,
) -> Path:
    """Download best audio only for transcription."""
    output_path = Path(output_path)

    # Clean up leftovers from previous partial downloads
    part_path = Path(str(output_path) + ".part")
    for p in (output_path, part_path):
        if p.exists():
            p.unlink()

    if start_time is not None and end_time is not None:
        log.info("⬇ Downloading audio section %.1fs–%.1fs from %s", start_time, end_time, url)
    else:
        log.info("⬇ Downloading full audio from %s", url)

    cmd = [
        "yt-dlp",
        "--extractor-args",
        "youtube:player_client=default,-android_sdkless",
        "--retries",
        "5",
        "--socket-timeout",
        "15",
        "--extract-audio",
        "--audio-format",
        "m4a",
        "-o",
        str(output_path),
    ]

    if start_time is not None and end_time is not None:
        cmd.extend(["--download-sections", f"*{start_time}-{end_time}"])

    cmd.append(url)
    subprocess.run(cmd, check=True)
    log.info("✅ Audio download complete: %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# Video download
# ---------------------------------------------------------------------------


def download_clip(
    url: str,
    output_path: str | Path,
    *,
    start_time: float | None = None,
    end_time: float | None = None,
    max_height: int = 1080,
) -> Path:
    """
    Download a video (or section) via yt-dlp.

    Uses --download-sections for pre-snipped clips, avoiding a full
    download when only a 30-45s window is needed.

    Args:
        url: YouTube or other yt-dlp-compatible URL.
        output_path: Destination path for the downloaded file.
        start_time: Section start in seconds (optional).
        end_time: Section end in seconds (optional).
        max_height: Max vertical resolution to request.

    Returns:
        Path to the downloaded file.
    """
    output_path = Path(output_path)

    # Clean up leftovers from previous partial downloads
    part_path = Path(str(output_path) + ".part")
    for p in (output_path, part_path):
        if p.exists():
            p.unlink()

    if start_time is not None and end_time is not None:
        log.info("⬇ Downloading section %.1fs–%.1fs from %s", start_time, end_time, url)
    else:
        log.info("⬇ Downloading full video from %s", url)

    fmt = (
        f"bestvideo[ext=mp4][height<={max_height}][vcodec^=avc1]"
        f"+bestaudio[ext=m4a]/best[ext=mp4]/best"
    )
    cmd = [
        "yt-dlp",
        "--extractor-args",
        "youtube:player_client=default,-android_sdkless",
        "--retries",
        "5",
        "--fragment-retries",
        "5",
        "--socket-timeout",
        "15",
        "--no-part",
        "-f",
        fmt,
        "--merge-output-format",
        "mp4",
        "-o",
        str(output_path),
    ]

    if start_time is not None and end_time is not None:
        cmd.extend(["--download-sections", f"*{start_time}-{end_time}"])

    cmd.append(url)
    subprocess.run(cmd, check=True)
    log.info("✅ Download complete: %s", output_path)
    return output_path
