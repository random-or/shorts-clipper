"""Safe ffmpeg command builders.

These helpers only build argv lists. Callers should pass the result to
`subprocess.run(command, check=True)` without `shell=True`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shorts_clipper.cropping.geometry import compute_center_crop


@dataclass(frozen=True, slots=True)
class FfmpegRenderOptions:
    target_width: int = 1080
    target_height: int = 1920
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    crf: int = 18
    preset: str = "medium"
    overwrite: bool = True
    extra_input_args: tuple[str, ...] = ()
    extra_output_args: tuple[str, ...] = ()


def build_vertical_render_command(
    *,
    input_path: str | Path,
    output_path: str | Path,
    start: float,
    end: float,
    source_width: int,
    source_height: int,
    options: FfmpegRenderOptions | None = None,
) -> list[str]:
    if start < 0:
        raise ValueError("start must be non-negative")
    if end <= start:
        raise ValueError("end must be greater than start")

    opts = options or FfmpegRenderOptions()
    crop = compute_center_crop(
        width=source_width,
        height=source_height,
        target_width=opts.target_width,
        target_height=opts.target_height,
    )
    video_filter = f"{crop.as_ffmpeg_filter()},scale={opts.target_width}:{opts.target_height}"

    command = ["ffmpeg"]
    if opts.overwrite:
        command.append("-y")
    command.extend([
        "-ss",
        f"{start:.3f}",
        "-to",
        f"{end:.3f}",
    ])
    command.extend(opts.extra_input_args)
    command.extend([
        "-i",
        str(input_path),
        "-vf",
        video_filter,
        "-c:v",
        opts.video_codec,
    ])
    if opts.video_codec == "libx264":
        command.extend(["-crf", str(opts.crf), "-preset", opts.preset])
    else:
        command.extend(["-preset", opts.preset])
    command.extend([
        "-c:a",
        opts.audio_codec,
        "-movflags",
        "+faststart",
    ])
    command.extend(opts.extra_output_args)
    command.append(str(output_path))
    return command
