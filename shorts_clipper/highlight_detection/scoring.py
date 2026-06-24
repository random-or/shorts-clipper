"""Deterministic highlight scoring heuristics."""

from __future__ import annotations

import re

from shorts_clipper.core.models import HighlightScore, TranscriptSegment

HOOK_PATTERNS = (
    "you won't believe",
    "you will not believe",
    "secret",
    "mistake",
    "watch this",
    "here's why",
    "this is why",
    "changed everything",
    "the truth",
)
EMOTION_WORDS = {
    "amazing",
    "insane",
    "crazy",
    "shocking",
    "unbelievable",
    "love",
    "hate",
    "angry",
    "terrified",
    "secret",
    "best",
    "worst",
    "changed",
    "everything",
}
VIRAL_WORDS = {
    "secret",
    "hack",
    "trick",
    "mistake",
    "truth",
    "viral",
    "million",
    "money",
}


class RuleBasedHighlightScorer:
    def score_segment(self, segment: TranscriptSegment) -> HighlightScore:
        text = segment.text.strip()
        lower = text.lower()
        words = re.findall(r"[a-zA-Z']+", lower)
        word_count = len(words)
        duration = max(segment.duration, 0.001)
        words_per_second = word_count / duration

        hook = 0.0
        if any(pattern in lower for pattern in HOOK_PATTERNS):
            hook += 2.0
        if text.endswith("?") or lower.startswith(("why", "how", "what", "here")):
            hook += 0.75

        emotion_hits = sum(1 for word in words if word in EMOTION_WORDS)
        virality_hits = sum(1 for word in words if word in VIRAL_WORDS)

        emotion = min(2.0, emotion_hits * 0.35 + text.count("!") * 0.25)
        virality = min(2.0, virality_hits * 0.4)
        retention = (
            1.0 if 15 <= segment.duration <= 60 else max(0.0, 1.0 - abs(segment.duration - 35) / 35)
        )
        silence = 1.0 if words_per_second >= 1.6 else words_per_second / 1.6
        topic = min(1.0, max(0.0, word_count / 20))
        speaker_emphasis = min(1.0, text.count("!") * 0.3 + text.count("?") * 0.2)
        caption_density = (
            min(1.0, len(segment.words) / max(1, word_count)) if segment.words else 0.0
        )

        return HighlightScore(
            hook=hook,
            emotion=emotion,
            silence=silence,
            retention=retention,
            virality=virality,
            topic=topic,
            speaker_emphasis=speaker_emphasis,
            caption_density=caption_density,
            metadata={
                "word_count": word_count,
                "words_per_second": round(words_per_second, 3),
                "emotion_hits": emotion_hits,
                "virality_hits": virality_hits,
            },
        )


class AttentionScore:
    def __init__(self, score: float, reasoning: str, window: list[TranscriptSegment]):
        self.score = score
        self.reasoning = reasoning
        self.window = window


class LocalTranscriptScorer:
    """Evaluates transcripts using Gemini Flash for true semantic attention scoring."""

    def __init__(self):
        from shorts_clipper.core.settings import Settings

        self.settings = Settings.from_env()

    def _determine_dynamic_duration(self, current_dur: float) -> float:
        """Lock to specific dynamic durations based on closest fit."""
        allowed = [20.0, 30.0, 40.0, 50.0, 60.0]
        return min(allowed, key=lambda x: abs(x - current_dur))

    def _optimize_boundaries(
        self, segments: list[TranscriptSegment], target_start: float, target_end: float
    ) -> list[TranscriptSegment]:
        """
        Phase 3: Real Boundary Optimization
        Expands or shrinks the window slightly to find sentence/thought completion.
        """
        if not segments:
            return []

        # Find closest segments to target
        start_idx = 0
        end_idx = len(segments) - 1

        for i, s in enumerate(segments):
            if s.start >= target_start - 5.0:
                start_idx = i
                break

        for i in range(start_idx, len(segments)):
            if segments[i].end >= target_end:
                end_idx = i
                break

        # Expand start backwards if mid-sentence (look for punctuation ending the previous sentence)
        while start_idx > 0:
            prev_text = segments[start_idx - 1].text.strip()
            curr_text = segments[start_idx].text.strip()
            # If current starts with lowercase and prev didn't end in punctuation, it's mid-sentence
            if curr_text and curr_text[0].islower() and not prev_text.endswith((".", "!", "?")):
                start_idx -= 1
            else:
                break

        # Expand end forwards to complete sentence
        while end_idx < len(segments) - 1:
            curr_text = segments[end_idx].text.strip()
            if not curr_text.endswith((".", "!", "?")):
                end_idx += 1
            else:
                break

        # Ensure we don't exceed 60s
        while end_idx > start_idx and (segments[end_idx].end - segments[start_idx].start) > 60.0:
            end_idx -= 1

        return segments[start_idx : end_idx + 1]

    def score_transcript(
        self, segments: list[TranscriptSegment]
    ) -> tuple[float, list[TranscriptSegment], str]:
        """Scores transcript using LLM for true semantic understanding."""
        if not segments:
            return 0.0, [], "Empty transcript"

        import json
        import logging

        log = logging.getLogger(__name__)

        full_text_parts = []
        for s in segments:
            full_text_parts.append(f"[{s.start:.1f} - {s.end:.1f}] {s.text}")
        full_text = "\n".join(full_text_parts)

        prompt = f"""
You are an Attention Prediction Engine.
Analyze the following transcript and identify the TOP 3 BEST highlights (between 20s and 60s).
Evaluate based on true semantics: conflict, surprise, stakes, emotion, transformation, curiosity, tension, and resolution.
Do NOT rely on simple keywords. Look for story progression and emotional peaks.

Transcript:
{full_text}

Return ONLY valid JSON in this format:
{{
    "highlights": [
        {{
            "start_time": float,
            "end_time": float,
            "score": float (0-100),
            "signals_triggered": ["list", "of", "signals"],
            "why_it_won": "detailed explanation of emotional arc and tension"
        }}
    ]
}}
"""

        try:
            from google import genai

            from shorts_clipper.providers.gemini import GeminiProvider

            provider = GeminiProvider(api_key=self.settings.gemini_api_key)

            response = provider.generate_content(
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json", temperature=0.0
                ),
            )

            res = json.loads(response.text)
            highlights = res.get("highlights", [])
            if not highlights:
                return 0.0, [], "No highlights returned"

            # Sort highlights by score descending and pick the best one
            highlights.sort(key=lambda x: x.get("score", 0), reverse=True)
            best = highlights[0]

            start_t = best["start_time"]
            end_t = best["end_time"]
            score = best["score"]
            reasoning = f"Signals: {', '.join(best['signals_triggered'])}. Why it won: {best['why_it_won']}."

            # Phase 3 & 4: Optimize Boundaries and Dynamic Duration
            best_window = self._optimize_boundaries(segments, start_t, end_t)

            if not best_window:
                return 0.0, [], "Failed to map window"

            actual_dur = best_window[-1].end - best_window[0].start
            target_dur = self._determine_dynamic_duration(actual_dur)

            # If the optimized window is wildly off from target duration, we shrink it from the start or end
            # depending on where the payoff is, but for safety we just trim to target_dur.
            while best_window and (best_window[-1].end - best_window[0].start) > target_dur + 5.0:
                # Trim from the beginning if it's too long, assuming punchline is at the end
                best_window.pop(0)

            final_dur = best_window[-1].end - best_window[0].start
            reasoning += f" | Original Duration: {end_t - start_t:.1f}s | Calculated Target: {target_dur}s | Final Applied Duration: {final_dur:.1f}s"

            return float(score), best_window, reasoning

        except Exception as e:
            log.warning("Semantic scoring failed: %s", e)
            # True fallback (if offline)
            return 0.0, segments[:10], f"Failed semantic scoring: {e}"
