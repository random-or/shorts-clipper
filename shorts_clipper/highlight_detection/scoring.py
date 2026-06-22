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


class LocalTranscriptScorer:
    """Lightweight scorer that operates directly on subtitle text. Returns 0-100 score and best segment."""
    
    def __init__(self):
        self.signals = [
            "?", "disagree", "shock", "i was wrong", "i couldn't believe", 
            "fail", "success", "controvers", "never", "always", "money", 
            "$", "percent", "%", "million", "billion", "secret", "truth"
        ]
        self.penalties = [
            "sponsor", "nordvpn", "skillshare", "welcome back", "hey guys", 
            "subscribe", "like and subscribe", "link in description",
            "outro", "music", "♪", "lyrics", "thanks for watching"
        ]

    def score_transcript(self, segments: list[TranscriptSegment]) -> tuple[float, list[TranscriptSegment]]:
        """Scores entire transcript, returns (0-100 score, list of segments for best window)"""
        if not segments:
            return 0.0, []

        best_window = []
        best_window_score = -1.0
        
        # We will scan through windows of ~60 seconds to find the best local clip
        window_duration = 60.0
        
        for i, start_seg in enumerate(segments):
            window_segs = []
            current_dur = 0.0
            
            curiosity = 0.0
            conflict = 0.0
            surprise = 0.0
            emotion = 0.0
            stakes = 0.0
            specificity = 0.0
            penalty = 0.0
            
            for j in range(i, len(segments)):
                seg = segments[j]
                window_segs.append(seg)
                current_dur = seg.end - start_seg.start
                
                text = seg.text.lower()
                
                # Signals
                if "?" in text:
                    curiosity += 5.0
                if any(w in text for w in ["disagree", "wrong", "no", "stop"]):
                    conflict += 5.0
                if any(w in text for w in ["shock", "couldn't believe", "crazy"]):
                    surprise += 5.0
                if "!" in text or any(w in text for w in ["hate", "love", "angry"]):
                    emotion += 5.0
                if any(w in text for w in ["money", "$", "fail", "success", "life"]):
                    stakes += 5.0
                if any(w in text for w in ["%", "percent", "million", "billion", "1", "2", "3", "4", "5", "6", "7", "8", "9"]):
                    specificity += 5.0
                
                # Penalties
                if any(w in text for w in self.penalties):
                    penalty += 15.0
                    
                if current_dur >= window_duration:
                    break
                    
            # Combine into 0-100 score for this window
            base_score = curiosity + conflict + surprise + emotion + stakes + specificity
            window_score = max(0.0, min(100.0, base_score - penalty))
            
            if window_score > best_window_score and 30.0 <= current_dur <= 75.0:
                best_window_score = window_score
                best_window = window_segs
                
        # Overall transcript score can be the max window score found
        final_score = max(0.0, min(100.0, best_window_score))
        return final_score, best_window

