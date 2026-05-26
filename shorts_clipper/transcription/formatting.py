"""Transcript formatting helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from shorts_clipper.core.models import TranscriptSegment, TranscriptWord


def segment_from_any(segment: Any) -> TranscriptSegment:
    words = []
    for word in getattr(segment, "words", None) or []:
        words.append(
            TranscriptWord(
                start=float(getattr(word, "start")),
                end=float(getattr(word, "end")),
                word=str(getattr(word, "word")),
                probability=getattr(word, "probability", None),
            )
        )
    return TranscriptSegment(
        start=float(getattr(segment, "start")),
        end=float(getattr(segment, "end")),
        text=str(getattr(segment, "text", "")).strip(),
        words=words,
    )


def format_transcript(segments: Iterable[TranscriptSegment | Any]) -> str:
    formatted = []
    for raw_segment in segments:
        segment = raw_segment if isinstance(raw_segment, TranscriptSegment) else segment_from_any(raw_segment)
        formatted.append(f"[{segment.start:.2f}s -> {segment.end:.2f}s]: {segment.text}")
    return "\n".join(formatted)
