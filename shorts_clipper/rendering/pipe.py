"""Stream-piped video rendering module.

Pipes the yt-dlp download output directly into FFmpeg stdin, running
scale, crop, speed/pacing, and subtitle burning in a single process loop.
This completely bypasses writing heavy intermediate video clips to disk.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from shorts_clipper.captions.generator import generate_ass_file
from shorts_clipper.core.models import TranscriptSegment
from shorts_clipper.cropping.geometry import CropBox

log = logging.getLogger(__name__)


def _get_base_yt_dlp_cmd() -> list[str]:
    import random

    cmd = [
        "yt-dlp",
        "--extractor-args",
        "youtube:player_client=default,-android_sdkless",
    ]
    # Check if curl-cffi is available for impersonation
    try:
        import curl_cffi  # noqa: F401

        cmd.extend(["--impersonate", "Chrome"])
    except ImportError:
        pass

    proxy_str = os.environ.get("SHORTS_PROXY")
    if proxy_str:
        proxies = [p.strip() for p in proxy_str.split(",") if p.strip()]
        if proxies:
            cmd.extend(["--proxy", random.choice(proxies)])
    return cmd


_TARGET_W = 1080
_TARGET_H = 1920


def get_url_dimensions(url: str) -> tuple[int, int]:
    """Fetch video width and height from YouTube URL using yt-dlp without downloading."""
    log.info("🔍 Probing video dimensions for %s...", url)
    cmd = _get_base_yt_dlp_cmd()
    cmd.extend(
        [
            "--skip-download",
            "--dump-json",
            "--socket-timeout",
            "10",
            url,
        ]
    )
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            width = data.get("width")
            height = data.get("height")
            if width and height:
                log.info("Fetched dimensions: %dx%d", width, height)
                return int(width), int(height)
    except Exception as e:
        log.warning("Failed to fetch dimensions from url: %s. Using default 1920x1080.", e)
    return 1920, 1080


def run_face_detection(url: str, start_time: float, end_time: float) -> int | None:
    """Download a tiny 3-second sample clip, extract frames, and detect speaker face center."""
    try:
        import cv2
    except ImportError:
        log.warning("⚠️  OpenCV (opencv-python-headless) not installed. Face tracking disabled.")
        return None

    log.info("🤖 Running auto face-tracking detection...")
    with tempfile.TemporaryDirectory(prefix="face_detect_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        sample_path = tmp_path / "sample.mp4"

        # Download 3s low-res clip
        cmd = _get_base_yt_dlp_cmd()
        cmd.extend(
            [
                "-f",
                "worstvideo[ext=mp4][height<=360]/worst",
                "--download-sections",
                f"*{start_time}-{start_time + 3.0}",
                "-o",
                str(sample_path),
                url,
            ]
        )
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=25)
        except Exception as err:
            log.warning("Failed to download sample clip for face tracking: %s", err)
            return None

        # Extract 3 frames
        try:
            cap = cv2.VideoCapture(str(sample_path))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if frame_count <= 0:
                return None

            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            x_centers = []

            for index in [10, frame_count // 2, frame_count - 10]:
                cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, min(index, frame_count - 1)))
                ret, frame = cap.read()
                if not ret:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.2, 4)
                for x, _y, w, _h in faces:
                    x_centers.append(x + w // 2)

            cap.release()
            if x_centers:
                # Map sample pixel coordinate back to relative ratio
                cap_ref = cv2.VideoCapture(str(sample_path))
                vid_width = cap_ref.get(cv2.CAP_PROP_FRAME_WIDTH)
                cap_ref.release()
                if vid_width > 0:
                    avg_center_ratio = sum(x_centers) / len(x_centers) / vid_width
                    log.info("🎯 Detected speaker center at %.2f%% width", avg_center_ratio * 100)
                    return avg_center_ratio
        except Exception as face_err:
            log.warning("Error running face detection cascade: %s", face_err)
    return None


def compute_custom_crop(
    width: int, height: int, layout: str, url: str, start_time: float, end_time: float
) -> CropBox:
    """Compute crop coordinates supporting custom layout offsets and face tracking."""
    target_ratio = _TARGET_W / _TARGET_H

    # Calculate initial crop box fill sizing
    source_ratio = width / height
    if source_ratio > target_ratio:
        crop_height = height
        crop_width = max(1, round(height * target_ratio))
        y = 0

        # Center x offset
        center_x = (width - crop_width) // 2
        x = center_x

        # Parse layout offset settings
        if layout.startswith("custom_offset_"):
            try:
                # E.g. "custom_offset_-150" or "custom_offset_200"
                offset_val = int(layout.split("_")[-1])
                # Shift relative to center
                x = center_x + offset_val
                logger_msg = f"Applying manual crop offset shift of {offset_val}px"
                log.info(logger_msg)
            except Exception:
                pass
        elif layout == "crop_left":
            x = 0
        elif layout == "crop_right":
            x = width - crop_width
        elif layout == "auto_track":
            center_ratio = run_face_detection(url, start_time, end_time)
            if center_ratio is not None:
                # Align crop box around face center
                face_x = round(width * center_ratio)
                x = face_x - crop_width // 2
            else:
                log.info("Face tracking fallback: using center crop.")
                x = center_x
    else:
        crop_width = width
        crop_height = max(1, round(width / target_ratio))
        x = 0
        y = (height - crop_height) // 2

    # Clamp bounds to verify it is within video dimensions
    x = max(0, min(x, width - crop_width))
    y = max(0, min(y, height - crop_height))

    return CropBox(x=x, y=y, width=crop_width, height=crop_height)


def stream_render_pipeline(
    url: str,
    start_time: float,
    end_time: float,
    layout: str,
    segments: list[TranscriptSegment],
    output_path: Path,
    pacing: float = 1.15,
    video_codec: str = "libx264",
    preset: str = "ultrafast",
    subtitle_style: str = "default",
    enable_gpu: bool = False,
) -> Path:
    """Run pipelined stream transcode: yt-dlp -> ffmpeg (crop, speed, ASS subtitles) -> file."""
    output_path = Path(output_path)

    # 1. Fetch dimensions
    src_w, src_h = get_url_dimensions(url)

    # 2. Compute custom crop box
    crop = compute_custom_crop(src_w, src_h, layout, url, start_time, end_time)

    # 3. Create temporary ASS subtitles file
    with tempfile.TemporaryDirectory(prefix="pipe_ass_") as tmp_dir:
        ass_path = Path(tmp_dir) / "subs.ass"
        generate_ass_file(segments, 0.0, ass_path, pacing=pacing, style_name=subtitle_style)

        # Escape paths
        escaped_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")

        # Build complex filters
        vf_parts = [
            f"crop={crop.width}:{crop.height}:{crop.x}:{crop.y}",
            f"scale={_TARGET_W}:{_TARGET_H}",
        ]

        af_parts = [
            "acompressor=threshold=-20dB:ratio=4:makeup=4",
            "aformat=channel_layouts=stereo",
        ]

        if pacing != 1.0:
            pts_factor = round(1.0 / pacing, 6)
            vf_parts.append(f"setpts={pts_factor}*PTS")
            af_parts.insert(0, f"atempo={pacing}")

        vf_parts.append(f"ass='{escaped_ass}'")

        # Construct yt-dlp stream command
        fmt = "bestvideo[ext=mp4][height<=1080][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        yt_cmd = _get_base_yt_dlp_cmd()
        yt_cmd.extend(
            [
                "--retries",
                "5",
                "--socket-timeout",
                "15",
                "--no-part",
                "-f",
                fmt,
                "--merge-output-format",
                "mkv",
                "--download-sections",
                f"*{start_time}-{end_time}",
                "-o",
                "-",
                url,
            ]
        )

        # Construct ffmpeg render command
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            "pipe:0",
            "-vf",
            ",".join(vf_parts),
            "-af",
            ",".join(af_parts),
            "-c:v",
            video_codec,
        ]

        if video_codec == "libx264":
            ffmpeg_cmd.extend(["-crf", "18", "-preset", preset])
        elif video_codec == "h264_nvenc":
            ffmpeg_cmd.extend(["-rc:v", "vbr", "-cq", "18", "-preset", preset])
        else:
            ffmpeg_cmd.extend(["-preset", preset])

        ffmpeg_cmd.extend(
            ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output_path)]
        )

        log.info("Launching Stream-Piped subprocesses:")
        log.info("yt-dlp: %s", " ".join(yt_cmd))
        log.info("ffmpeg: %s", " ".join(ffmpeg_cmd))

        yt_proc = subprocess.Popen(yt_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd, stdin=yt_proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        if yt_proc.stdout:
            yt_proc.stdout.close()

        _, errs = ffmpeg_proc.communicate()
        yt_proc.wait()

        if ffmpeg_proc.returncode != 0:
            log.error("FFmpeg stream rendering failed: %s", errs.decode(errors="ignore")[-2000:])
            raise RuntimeError(f"FFmpeg stream render failed (exit {ffmpeg_proc.returncode})")

    log.info("✅ Pipelined stream render successfully output to %s", output_path)
    return output_path
