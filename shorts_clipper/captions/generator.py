"""FFmpeg-native subtitle burning via ASS format.

Why ASS over MoviePy TextClip:
- MoviePy renders subtitles in Python frame-by-frame via ImageMagick.
  On a 30s clip this can take 3-5 minutes.
- FFmpeg's native ``ass`` filter hands subtitle rendering to the GPU-
  accelerated libass library. The same operation takes seconds.
- ASS gives precise per-word timing, custom fonts, drop shadows, and
  karaoke-style highlights that MoviePy cannot do cleanly.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from shorts_clipper.core.models import TranscriptSegment

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ASS file generation
# ---------------------------------------------------------------------------


def _ass_header() -> str:
    """Build the ASS subtitle file header (spec lines are intentionally long)."""
    style_format = (
        "Name, Fontname, Fontsize, PrimaryColour, SecondaryColour,"
        " OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut,"
        " ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow,"
        " Alignment, MarginL, MarginR, MarginV, Encoding"
    )
    style_def = (
        "Default,Arial Black,85,"
        "&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
        "-1,0,0,0,100,100,0.5,0,1,4,2,2,40,40,160,1"
    )
    event_format = "Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    return "\n".join(
        [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            f"Format: {style_format}",
            f"Style: {style_def}",
            "",
            "[Events]",
            f"Format: {event_format}",
            "",
        ]
    )


def _seconds_to_ass_time(seconds: float) -> str:
    """Convert float seconds to ASS timestamp H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)  # centiseconds
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _build_ass_chunks(
    segments: list[TranscriptSegment],
    start_offset: float,
    words_per_chunk: int = 3,
) -> list[dict]:
    """Break segments into timed 2-3 word chunks for punchy subtitle display."""
    chunks: list[dict] = []
    for seg in segments:
        if seg.words:
            # Word-level timing available — most accurate
            words = seg.words
            for i in range(0, len(words), words_per_chunk):
                group = words[i : i + words_per_chunk]
                text = " ".join(w.word for w in group).upper()
                chunks.append(
                    {
                        "text": text,
                        "start": max(0.0, group[0].start - start_offset),
                        "end": max(0.01, group[-1].end - start_offset),
                    }
                )
        else:
            # Fallback: split by word count, distribute time evenly
            words_list = seg.text.split()
            if not words_list:
                continue
            seg_start = max(0.0, seg.start - start_offset)
            seg_end = max(0.01, seg.end - start_offset)
            seg_dur = seg_end - seg_start
            n_chunks = max(1, (len(words_list) + words_per_chunk - 1) // words_per_chunk)
            chunk_dur = seg_dur / n_chunks
            for i in range(0, len(words_list), words_per_chunk):
                group = words_list[i : i + words_per_chunk]
                idx = i // words_per_chunk
                text = " ".join(group).upper()
                c_start = seg_start + idx * chunk_dur
                c_end = min(c_start + chunk_dur, seg_end)
                chunks.append({"text": text, "start": c_start, "end": c_end})
    return chunks


def generate_ass_file(
    segments: list[TranscriptSegment],
    start_offset: float,
    output_path: str | Path,
) -> Path:
    """Generate an ASS subtitle file from transcript segments."""
    out = Path(output_path)
    chunks = _build_ass_chunks(segments, start_offset)

    lines = [_ass_header(), ""]
    for chunk in chunks:
        start = _seconds_to_ass_time(chunk["start"])
        end = _seconds_to_ass_time(chunk["end"])
        # \an2 = bottom-center alignment; {\bord4} adds thick border
        text = chunk["text"]
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{{\\an2\\bord4\\shad2}}{text}")

    out.write_text("\n".join(lines), encoding="utf-8")
    log.debug("ASS file written: %s (%d chunks)", out, len(chunks))
    return out


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def burn_subtitles(
    video_path: str | Path,
    segments: list[TranscriptSegment],
    start_offset: float,
    output_path: str | Path,
    crf: int = 18,
    preset: str = "fast",
) -> Path:
    """
    Burn subtitles into a video using FFmpeg's native ASS filter.

    This replaces the MoviePy TextClip approach entirely.
    Speed improvement: typically 3-8x faster on CPU, 10x+ with GPU.

    Args:
        video_path: Input video file.
        segments: Transcript segments with timing information.
        start_offset: Start time offset for computing relative timestamps.
        output_path: Where to write the final video.
        crf: FFmpeg CRF quality (18 = near-lossless, 23 = default).
        preset: FFmpeg encode preset (fast, medium, slow).

    Returns:
        Path to the output video.
    """
    video_path = Path(video_path)
    output_path = Path(output_path)

    log.info("🎬 Burning subtitles via FFmpeg ASS filter...")

    with tempfile.TemporaryDirectory(prefix="ass_") as tmp:
        ass_path = Path(tmp) / "subs.ass"
        generate_ass_file(segments, start_offset, ass_path)

        # FFmpeg ASS filter — libass renders directly during encode
        # On Linux the path needs colons escaped
        escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"ass='{escaped}'",
            "-c:v",
            "libx264",
            "-crf",
            str(crf),
            "-preset",
            preset,
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        log.info("Running FFmpeg: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log.error("FFmpeg stderr: %s", result.stderr[-2000:])
            raise RuntimeError(f"FFmpeg subtitle burn failed (exit {result.returncode})")

    log.info("✅ Subtitles burned → %s", output_path)
    return output_path
