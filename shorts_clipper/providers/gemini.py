"""Gemini AI highlight provider.

Uses Gemini 2.5 Pro (thinking model) to select the best clip window.
Implements HighlightProvider ABC so it can be swapped for any other LLM.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Sequence

from shorts_clipper.core.exceptions import ProviderError
from shorts_clipper.core.models import ClipWindow, TranscriptSegment
from shorts_clipper.providers.base import HighlightProvider
from shorts_clipper.transcription.formatting import format_transcript

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """\
You are an elite viral shorts editor with 10 years of experience on TikTok,
Instagram Reels, and YouTube Shorts. Your clips consistently hit 1M+ views.

Analyze the transcript below, identify the SINGLE best clip window,
and score it from 0 to 100 based on the evaluation criteria.

{transcript}

━━━ EVALUATION CRITERIA (Score 0-100) ━━━

Score the clip window strictly based on these 5 dimensions (0 to 100 overall score):

1. EMOTIONAL PEAK MOMENTS: Genuinely surprising, hilarious, or high-impact
moments. Do NOT just select loud or high-volume noise; prioritize authentic
humor or shocking surprises.
2. CLIP-ABILITY: The segment must have a clean, logical start and a
satisfying end. It must make perfect sense standing alone as a
self-contained video.
3. NICHE RELEVANCE: The clip must highly align with and fit the specific
topic, theme, or channel style.
4. HOOK QUALITY: The first 3 seconds of the clip must grab attention
immediately with extreme hook power (tension, question, mystery, shock,
or surprise).
5. AVOID ENTIRELY (Score < 85 if any of these are present):
   - Reaction compilations.
   - Generic motivational filler/pacing.
   - Anything requiring external context or explanation from the rest of the video to be understood.

Only select and return a clip if its final combined score is 85 or higher.
If no clip reaches a score of 85 or above, return a low score under 85
and explain why in the reason.

━━━ FRAMING — choose the best vertical crop ━━━
• crop_center   — single subject, centered
• crop_left     — subject is left of frame
• crop_right    — subject is right of frame

━━━ RESPONSE FORMAT ━━━

Return ONLY valid JSON, no markdown, no commentary:
{{
  "start": <float seconds>,
  "end": <float seconds>,
  "layout": "<framing_strategy>",
  "virality_score": <int 0-100>,
  "emotional_category": "<tension|shock|humor|confrontation|revelation>",
  "strongest_hook_line": "<exact phrase from transcript>",
  "reason": "<one sentence why this clip meets the criteria and how it was scored>"
}}"""


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class GeminiProvider(HighlightProvider):
    """Uses Gemini 2.5 Flash to select the best clip window from a transcript."""

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

        # Lazy import — keeps the package importable without google-genai installed
        from google import genai  # type: ignore[import]

        self._client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))

    def select_clip(self, segments: Sequence[TranscriptSegment]) -> ClipWindow:
        """Return the best clip window. Falls back gracefully on any failure."""
        transcript_text = format_transcript(segments)
        prompt = _PROMPT_TEMPLATE.format(transcript=transcript_text)

        log.info("\n--- CONSULTING %s ---", self._model)
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
            )
            raw = response.text.strip()
            log.debug("Gemini raw response: %r", raw)

            # Strip markdown code fences if present
            json_str = raw
            json_match = re.search(r"```(?:json)?(.*?)```", raw, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as exc:
                raise ProviderError(f"Gemini returned unparseable JSON: {raw!r}") from exc

            start = float(data["start"])
            end = float(data["end"])
            layout = str(data.get("layout", self._fallback_layout)).strip()
            score = int(data.get("virality_score", 0))

            if score < 85:
                raise ProviderError(
                    f"Selected clip score ({score}) is below the minimum threshold of 85."
                )

            # Enforce duration bounds — if Gemini goes out of spec, clamp it
            duration = end - start
            if duration < 30:
                log.warning(
                    "Gemini returned %.1fs clip (< 30s). Extending end to %.1fs.",
                    duration,
                    start + 35,
                )
                end = start + 35
            elif duration > 65:
                log.warning(
                    "Gemini returned %.1fs clip (> 65s). Trimming to %.1fs.",
                    duration,
                    start + 55,
                )
                end = start + 55

            log.info(
                "✅ Gemini selected: %.1fs → %.1fs [%s] | score=%d | %s",
                start,
                end,
                layout,
                score,
                data.get("emotional_category", "?"),
            )
            log.info("   Hook: %r", data.get("strongest_hook_line", ""))
            log.info("   Why:  %s", data.get("reason", ""))

            window = ClipWindow(start=start, end=end)
            return window, layout  # type: ignore[return-value]

        except Exception as exc:  # noqa: BLE001
            fb_start, fb_end = self._fallback_window
            log.warning(
                "Gemini failed (%s). Using fallback %.1fs→%.1fs [%s]",
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
