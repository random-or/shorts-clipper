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


_MULTI_PROMPT_TEMPLATE = """\
You are an elite viral shorts editor with 10 years of experience on TikTok,
Instagram Reels, and YouTube Shorts. Your clips consistently hit 1M+ views.

Analyze the transcript below, identify the top {count} non-overlapping, high-impact clip windows,
and score each from 0 to 100 based on the evaluation criteria.

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

Only select and return clips if their final combined score is 85 or higher.

━━━ FRAMING — choose the best vertical crop ━━━
• crop_center   — single subject, centered
• crop_left     — subject is left of frame
• crop_right    — subject is right of frame

━━━ RESPONSE FORMAT ━━━

Return ONLY valid JSON as a list/array of objects. No markdown, no commentary:
[
  {{
    "start": <float seconds>,
    "end": <float seconds>,
    "layout": "<framing_strategy>",
    "virality_score": <int 0-100>,
    "emotional_category": "<tension|shock|humor|confrontation|revelation>",
    "strongest_hook_line": "<exact phrase from transcript>",
    "reason": "<one sentence why this clip meets the criteria and how it was scored>"
  }}
]"""


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

    def _generate_content_with_retry(
        self, prompt: str, max_retries: int = 3, initial_delay: float = 2.0
    ) -> any:
        """Call generate_content with exponential backoff on transient errors."""
        import time

        delay = initial_delay
        for attempt in range(1, max_retries + 1):
            try:
                return self._client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                )
            except Exception as exc:
                if attempt == max_retries:
                    log.error(
                        "Gemini generate_content failed after %d attempts: %s", max_retries, exc
                    )
                    raise
                log.warning(
                    "Gemini API call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt,
                    max_retries,
                    exc,
                    delay,
                )
                time.sleep(delay)
                delay *= 2

    def select_clip(self, segments: Sequence[TranscriptSegment]) -> ClipWindow:
        """Return the best clip window. Falls back gracefully on any failure."""
        transcript_text = format_transcript(segments)
        prompt = _PROMPT_TEMPLATE.format(transcript=transcript_text)

        log.info("\n--- CONSULTING %s ---", self._model)
        try:
            response = self._generate_content_with_retry(prompt)
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

    def select_multiple_clips(
        self, segments: Sequence[TranscriptSegment], count: int = 1
    ) -> list[tuple[ClipWindow, str]]:
        """Return the best clip windows (up to count) from the transcript."""
        if count <= 1:
            win, lay = self.select_clip_raw(segments)
            return [(win, lay)]

        transcript_text = format_transcript(segments)
        prompt = _MULTI_PROMPT_TEMPLATE.format(count=count, transcript=transcript_text)

        log.info("\n--- CONSULTING %s FOR MULTIPLE CLIPS (up to %d) ---", self._model, count)
        try:
            response = self._generate_content_with_retry(prompt)
            raw = response.text.strip()
            log.debug("Gemini raw response: %r", raw)

            json_str = raw
            json_match = re.search(r"```(?:json)?(.*?)```", raw, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()

            try:
                items = json.loads(json_str)
            except json.JSONDecodeError as exc:
                raise ProviderError(f"Gemini returned unparseable JSON array: {raw!r}") from exc

            if not isinstance(items, list):
                raise ProviderError(f"Gemini response did not return a JSON list: {raw!r}")

            results: list[tuple[ClipWindow, str]] = []
            for item in items[:count]:
                try:
                    start = float(item["start"])
                    end = float(item["end"])
                    layout = str(item.get("layout", self._fallback_layout)).strip()
                    score = int(item.get("virality_score", 0))

                    if score < 85:
                        log.warning("Skipping selected clip with low score: %d (< 85)", score)
                        continue

                    # Clamp duration
                    duration = end - start
                    if duration < 30:
                        end = start + 35
                    elif duration > 65:
                        end = start + 55

                    log.info(
                        "✅ Gemini selected candidate: %.1fs → %.1fs [%s] | score=%d | %s",
                        start,
                        end,
                        layout,
                        score,
                        item.get("emotional_category", "?"),
                    )
                    results.append((ClipWindow(start=start, end=end), layout))
                except Exception as item_exc:
                    log.warning("Failed parsing individual clip candidate: %s", item_exc)

            if not results:
                raise ProviderError("No high-quality clips selected by Gemini.")

            return results

        except Exception as exc:
            log.warning("Gemini multi-clip selection failed (%s). Using fallback.", exc)
            win, lay = self.select_clip_raw(segments)
            return [(win, lay)]

    def generate_clip_metadata(self, segments: Sequence[TranscriptSegment]) -> dict:
        """Generate a viral title, description, and keywords for a clip using Gemini."""
        transcript_text = format_transcript(segments)
        prompt = f"""\
You are an expert viral content creator, YouTube growth strategist, and pro short-form editor.
Your short-form videos consistently hit millions of views.

Generate a highly engaging, viral, clickbaity YouTube Shorts title (maximum 70 characters, including 2-3 hot trending hashtags like #shorts, #viral, #trending) and a short viral description (with keywords, hashtags, and a call-to-action) for a vertical video with the following transcript:

{transcript_text}

Return ONLY valid JSON in the following format (no markdown, no other text, just raw JSON):
{{
  "title": "<viral_title>",
  "description": "<viral_description>",
  "tags": ["<tag1>", "<tag2>", "<tag3>"]
}}
"""
        log.info("🧠 Consulting Gemini to generate viral titles & metadata...")
        try:
            response = self._generate_content_with_retry(prompt)
            raw = response.text.strip()

            json_str = raw
            json_match = re.search(r"```(?:json)?(.*?)```", raw, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()

            data = json.loads(json_str)
            title = str(data.get("title", "")).strip()
            # Clean title: ensure it's not wrapped in quotes
            if title.startswith('"') and title.endswith('"'):
                title = title[1:-1].strip()

            return {
                "title": title or "Trending Highlight #shorts",
                "description": str(
                    data.get(
                        "description",
                        "Generated by Shorts Clipper Autopilot. #shorts #viral #trending",
                    )
                ).strip(),
                "tags": [str(t).strip() for t in data.get("tags", ["shorts", "viral", "trending"])],
                "publish_status": "idle",
                "publish_error": None,
            }
        except Exception as exc:
            log.warning("Failed to generate viral metadata from Gemini: %s", exc)
            return {
                "title": "Viral Highlight #shorts",
                "description": "Automatically generated by Shorts Clipper. #shorts #viral",
                "tags": ["shorts", "viral", "trending"],
                "publish_status": "idle",
                "publish_error": None,
            }
