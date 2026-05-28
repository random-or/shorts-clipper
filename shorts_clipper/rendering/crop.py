"""Video crop + vertical layout processor using FFmpeg.

Single-pass scale+crop to 1080×1920.  No Python frame loop,
no MoviePy, no zoompan (which forces 30 fps and tanks CPU perf).
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from shorts_clipper.cropping.geometry import compute_center_crop
from shorts_clipper.utils.video import get_video_metadata

log = logging.getLogger(__name__)

_TARGET_W = 608
_TARGET_H = 1080


def _build_crop_filter(src_w: int, src_h: int, layout: str) -> str:
    """Return an FFmpeg -vf / -filter_complex string for the requested layout."""
    src_ratio = src_w / src_h

    if layout == "crop_left":
        scale_h = _TARGET_H
        scale_w = max(_TARGET_W, round(_TARGET_H * src_ratio))
        return f"scale={scale_w}:{scale_h},crop={_TARGET_W}:{_TARGET_H}:0:0"

    if layout == "crop_right":
        scale_h = _TARGET_H
        scale_w = max(_TARGET_W, round(_TARGET_H * src_ratio))
        x_offset = scale_w - _TARGET_W
        return f"scale={scale_w}:{scale_h},crop={_TARGET_W}:{_TARGET_H}:{x_offset}:0"

    if layout == "split_screen":
        # Stack top half and bottom half — podcast/debate dual-view
        half_h = _TARGET_H // 2
        scale_w = max(_TARGET_W, round(half_h * src_ratio))
        x_c = (scale_w - _TARGET_W) // 2
        top = f"scale={scale_w}:{half_h},crop={_TARGET_W}:{half_h}:{x_c}:0"
        bot = f"scale={scale_w}:{half_h},crop={_TARGET_W}:{half_h}:{x_c}:{half_h // 2}"
        return (
            f"[0:v]split=2[top][bot];"
            f"[top]{top}[top_out];"
            f"[bot]{bot}[bot_out];"
            f"[top_out][bot_out]vstack=inputs=2"
        )

    # Default: crop_center — compute precise center crop box
    crop = compute_center_crop(
        width=src_w,
        height=src_h,
        target_width=_TARGET_W,
        target_height=_TARGET_H,
    )
    # Scale so the crop region exactly fills the target frame
    scale = max(_TARGET_W / crop.width, _TARGET_H / crop.height)
    scaled_w = round(src_w * scale)
    scaled_h = round(src_h * scale)
    x = (scaled_w - _TARGET_W) // 2
    y = (scaled_h - _TARGET_H) // 2
    return f"scale={scaled_w}:{scaled_h},crop={_TARGET_W}:{_TARGET_H}:{x}:{y}"


def process_to_vertical(
    input_path: str | Path,
    output_path: str | Path,
    *,
    layout: str = "crop_center",
    crf: int = 18,
    preset: str = "ultrafast",
) -> Path:
    """
    Crop and scale a video to 1080×1920 vertical using pure FFmpeg.

    Args:
        input_path: Source video file.
        output_path: Destination file (will be overwritten if it exists).
        layout: crop_center | crop_left | crop_right | split_screen.
        crf: Constant rate factor (18 = near-lossless, 23 = default).
        preset: FFmpeg x264 preset (fast / medium / slow).

    Returns:
        Path to the output file.

    Raises:
        RuntimeError: If FFmpeg exits with a non-zero status.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    meta = get_video_metadata(str(input_path))
    vf = _build_crop_filter(meta.width, meta.height, layout)

    log.info(
        "\n--- VERTICAL CROP [%s] %dx%d → %dx%d ---",
        layout,
        meta.width,
        meta.height,
        _TARGET_W,
        _TARGET_H,
    )

    # split_screen uses -filter_complex; everything else uses -vf
    filter_flag = "-filter_complex" if layout == "split_screen" else "-vf"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        filter_flag,
        vf,
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

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error("FFmpeg crop stderr:\n%s", result.stderr[-3000:])
        raise RuntimeError(f"FFmpeg crop failed (exit {result.returncode})")

    log.info("✅ Vertical crop done → %s", output_path)
    return output_path
