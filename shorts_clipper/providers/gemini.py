"""Gemini AI highlight provider.

Migrated from root analyzer.py into the package. Implements the
HighlightProvider ABC so it can be swapped for any other LLM.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence

from shorts_clipper.core.exceptions import ProviderError
from shorts_clipper.core.models import ClipWindow, TranscriptSegment
from shorts_clipper.providers.base import HighlightProvider
from shorts_clipper.transcription.formatting import format_transcript

log = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """\
Analyze the following video transcript:

{transcript}

Your task: Identify the single highest-energy, most viral-worthy \
30-to-45 second hook suitable for Instagram Reels / TikTok / YouTube Shorts.

Focus on:
- High emotional peaks, surprising reveals, or funny moments
- Self-contained stories that work without prior context
- Strong opening hook in the first 3 seconds of the window

Choose the best vertical framing from: crop_center, crop_left, crop_right, split_screen.

Return ONLY: start_seconds,end_seconds,framing_strategy
Example: 143.5,178.0,crop_center

No other text. No labels. No explanation."""


class GeminiProvider(HighlightProvider):
    """Uses Gemini Flash to select the best clip window from a transcript."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "gemini-2.5-flash",
        fallback_window: tuple[float, float] = (60.0, 95.0),
        fallback_layout: str = "crop_center",
    ) -> None:
        self._model = model
        self._fallback_window = fallback_window
        self._fallback_layout = fallback_layout

        # Import lazily so the package can be imported without google-genai
        import os

        from google import genai  # type: ignore[import]

        self._client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))

    def select_clip(self, segments: Sequence[TranscriptSegment]) -> ClipWindow:
        """Return the best clip window. Falls back to a heuristic on failure."""
        transcript_text = format_transcript(segments)
        prompt = _PROMPT_TEMPLATE.format(transcript=transcript_text)

        log.info("\n--- CONSULTING GEMINI (%s) ---", self._model)
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
            )
            raw = response.text.strip()
            log.debug("Gemini raw response: %r", raw)

            match = re.search(r"(\d+\.?\d*),\s*(\d+\.?\d*),\s*([a-zA-Z_]+)", raw)
            if not match:
                raise ProviderError(f"Unrecognisable format: {raw!r}")

            start = float(match.group(1))
            end = float(match.group(2))
            layout = match.group(3).strip()

            window = ClipWindow(start=start, end=end)
            log.info(
                "Gemini selected: %.1fs \u2192 %.1fs [%s]",
                window.start,
                window.end,
                layout,
            )
            return window, layout  # type: ignore[return-value]

        except Exception as exc:  # noqa: BLE001
            fb_start, fb_end = self._fallback_window
            log.warning(
                "Gemini failed (%s). Using fallback %.1fs\u2192%.1fs [%s]",
                exc,
                fb_start,
                fb_end,
                self._fallback_layout,
            )
            return ClipWindow(start=fb_start, end=fb_end), self._fallback_layout  # type: ignore[return-value]

    def select_clip_raw(self, segments: Sequence[TranscriptSegment]) -> tuple[ClipWindow, str]:
        """Same as select_clip but always returns (ClipWindow, layout_str)."""
        result = self.select_clip(segments)
        if isinstance(result, tuple):
            return result
        return result, self._fallback_layout
