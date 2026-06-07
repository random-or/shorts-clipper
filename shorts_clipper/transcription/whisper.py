"""Local Whisper transcription using faster-whisper with Gemini Flash acceleration."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from shorts_clipper.core.models import TranscriptSegment, TranscriptWord

log = logging.getLogger(__name__)


def _get_audio_bytes(media_path: Path) -> tuple[bytes, str]:
    """Ensure we have audio bytes and the correct mime type."""
    suffix = media_path.suffix.lower()
    if suffix in {".m4a", ".mp3", ".wav", ".ogg", ".aac"}:
        mime = f"audio/{suffix[1:]}"
        if suffix == ".m4a":
            mime = "audio/m4a"
        return media_path.read_bytes(), mime

    # If it is a video or other format, extract audio to a temporary m4a file
    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(media_path),
            "-vn",
            "-c:a",
            "aac",
            str(tmp_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return tmp_path.read_bytes(), "audio/m4a"
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _transcribe_with_gemini(
    media_path: Path,
    api_key: str | None = None,
) -> list[TranscriptSegment] | None:
    """Attempt to transcribe the media file using Gemini 2.5 Flash."""
    try:
        from google import genai
        from google.genai import types

        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            log.warning("Gemini API key not found. Skipping Gemini transcription.")
            return None

        log.info("🚀 Attempting fast transcription with Gemini 2.5 Flash...")
        audio_bytes, mime_type = _get_audio_bytes(media_path)

        client = genai.Client(api_key=api_key)

        prompt = (
            "Transcribe this audio file. Format the response as a JSON array of objects, "
            "where each object represents a segment:\n"
            '- "start": float representing segment start in seconds\n'
            '- "end": float representing segment end in seconds\n'
            '- "text": string representing segment text\n'
            '- "words": list of objects representing each word in the segment, '
            "where each object has:\n"
            '  - "word": string representing the word\n'
            '  - "start": float representing when the word starts in seconds\n'
            '  - "end": float representing when the word ends in seconds\n\n'
            "Do NOT include any markdown code blocks, introductory, or concluding text. "
            "Return ONLY the raw valid JSON."
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        raw_text = response.text.strip()
        json_match = re.search(r"```(?:json)?(.*?)```", raw_text, re.DOTALL)
        if json_match:
            raw_text = json_match.group(1).strip()

        data = json.loads(raw_text)
        segments: list[TranscriptSegment] = []
        for item in data:
            words = []
            for w in item.get("words", []):
                words.append(
                    TranscriptWord(
                        start=float(w["start"]),
                        end=float(w["end"]),
                        word=str(w["word"]).strip(),
                    )
                )
            segments.append(
                TranscriptSegment(
                    start=float(item["start"]),
                    end=float(item["end"]),
                    text=str(item["text"]).strip(),
                    words=words,
                )
            )

        log.info("✅ Gemini transcription successful: %d segments", len(segments))
        return segments
    except Exception as exc:
        log.warning("⚠️  Gemini transcription failed (%s). Falling back to local Whisper.", exc)
        return None


@lru_cache(maxsize=1)
def _get_model(model_size: str, device: str, compute_type: str):
    """Load and cache the Whisper model (loaded once, reused across calls)."""
    from faster_whisper import WhisperModel  # lazy import — heavy dependency

    log.info("Loading Whisper model '%s' on %s...", model_size, device)
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def transcribe_clip(
    video_path: str | Path,
    *,
    model_size: str = "tiny.en",
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

    # Try Gemini first for ultra-fast, premium transcription
    gemini_segments = _transcribe_with_gemini(video_path)
    if gemini_segments is not None:
        return gemini_segments

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
