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
    "amazing", "insane", "crazy", "shocking", "unbelievable", "love", "hate",
    "angry", "terrified", "secret", "best", "worst", "changed", "everything",
}
VIRAL_WORDS = {"secret", "hack", "trick", "mistake", "truth", "viral", "million", "money"}


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
        retention = 1.0 if 15 <= segment.duration <= 60 else max(0.0, 1.0 - abs(segment.duration - 35) / 35)
        silence = 1.0 if words_per_second >= 1.6 else words_per_second / 1.6
        topic = min(1.0, max(0.0, word_count / 20))
        speaker_emphasis = min(1.0, text.count("!") * 0.3 + text.count("?") * 0.2)
        caption_density = min(1.0, len(segment.words) / max(1, word_count)) if segment.words else 0.0

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
