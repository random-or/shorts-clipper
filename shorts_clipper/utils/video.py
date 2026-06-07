import json
import subprocess
from dataclasses import dataclass


@dataclass
class VideoMetadata:
    width: int
    height: int
    duration: float


def get_video_metadata(path: str) -> VideoMetadata:
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    video_stream = next(
        (s for s in data["streams"] if s["codec_type"] == "video"), None
    )
    if video_stream is None:
        raise RuntimeError(f"No video stream found in {path}")
    width = int(video_stream["width"])
    height = int(video_stream["height"])

    # Duration can be in format or stream
    duration = float(
        data["format"].get("duration", 0) or video_stream.get("duration", 0)
    )

    return VideoMetadata(width=width, height=height, duration=duration)
