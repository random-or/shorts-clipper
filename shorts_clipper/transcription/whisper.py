"""Local Whisper transcription using faster-whisper."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from shorts_clipper.core.models import TranscriptSegment, TranscriptWord

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_model(model_size: str, device: str, compute_type: str):
    """Load and cache the Whisper model (loaded once, reused across calls)."""
    from faster_whisper import WhisperModel  # lazy import — heavy dependency

    log.info("Loading Whisper model '%s' on %s...", model_size, device)
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def transcribe_clip(
    video_path: str | Path,
    *,
    model_size: str = "large-v3",
    device: str = "cpu",
    compute_type: str = "int8",
    beam_size: int = 5,
) -> list[TranscriptSegment]:
    """
    Transcribe a video/audio file locally with faster-whisper.

    The model is cached after the first load so repeated calls
    within the same process pay no cold-start penalty.

    Args:
        video_path: Path to the video or audio file.
        model_size: Whisper model variant (tiny, base, small, medium, large-v3).
        device: 'cpu' or 'cuda'.
        compute_type: Quantisation type (int8, float16, float32).
        beam_size: Beam search width (higher = more accurate, slower).

    Returns:
        List of TranscriptSegment with word-level timestamps where available.
    """
    video_path = Path(video_path)
    log.info("🎙 Transcribing %s with Whisper (%s)...", video_path.name, model_size)

    model = _get_model(model_size, device, compute_type)
    raw_segments, info = model.transcribe(
        str(video_path),
        beam_size=beam_size,
        word_timestamps=True,
    )

    if info.language != "en":
        log.warning(
            "⚠️  Whisper detected language '%s' (expected 'en'). "
            "Transcript may be inaccurate — continuing anyway.",
            info.language,
        )

    segments: list[TranscriptSegment] = []
    for seg in raw_segments:
        words = [
            TranscriptWord(
                start=float(w.start),
                end=float(w.end),
                word=w.word.strip(),
                probability=float(w.probability) if w.probability is not None else None,
            )
            for w in (seg.words or [])
        ]
        segments.append(
            TranscriptSegment(
                start=float(seg.start),
                end=float(seg.end),
                text=seg.text.strip(),
                words=words,
            )
        )

    log.info("✅ Transcription done: %d segments (lang=%s)", len(segments), info.language)
    return segments
