from __future__ import annotations

import json
import logging
import os

from google import genai
from google.genai import types

from shorts_clipper.core.models import ClipWindow, TranscriptSegment

log = logging.getLogger(__name__)


class EditorialFinisher:
    """
    Decides whether a generated Short is editorially complete before it is rendered.
    If it's not, it modifies the boundaries to snap to nearest sentences.
    """

    def snap_boundaries(
        self, target_start: float, target_end: float, segments: list[TranscriptSegment]
    ) -> ClipWindow:
        all_words = []
        for s in segments:
            if s.words:
                all_words.extend(s.words)
            else:
                all_words.append(s)

        if not all_words:
            return ClipWindow(start=target_start, end=target_end)

        # Find the word indices closest to the target_start and target_end
        initial_start_idx = 0
        for i, w in enumerate(all_words):
            if (getattr(w, "end", w.start) > target_start) or (w.start >= target_start):
                initial_start_idx = i
                break

        initial_end_idx = len(all_words) - 1
        for i in range(initial_start_idx, len(all_words)):
            if all_words[i].start >= target_end:
                initial_end_idx = max(initial_start_idx, i - 1)
                break

        transcript_text = ""
        for i, w in enumerate(all_words):
            text = getattr(w, "word", getattr(w, "text", "")).strip()
            transcript_text += f"[{i}] {text} "

        prompt = f"""
You are the Editorial Finisher.
Your job is to find the optimal start and end point for a short-form video clip.
The initial AI cut suggested starting around word ID {initial_start_idx} and ending around word ID {initial_end_idx}.
However, the initial cut is often editorially incomplete.

Here is the transcript:
<transcript>
{transcript_text}
</transcript>

RULES FOR START:
- You MUST scan the transcript from word 0 up to word {initial_end_idx} to find the absolute best, most viral hook.
- The start point must be the beginning of a completely new thought that requires ZERO previous context.
- The first 5 seconds MUST hook a stranger instantly.

FATAL ERRORS (You MUST shift the start_id to avoid these):
1. Starting with a conjunction ("And", "But", "So", "Because").
2. Starting with a pronoun ("He", "She", "They", "It", "This", "That") where the name wasn't said yet.
3. Starting with a specific person's name (e.g. "Lawrence", "Beth") if they haven't been introduced yet, unless they are world-famous.
4. Starting mid-sentence (if the first word is lowercase, or if it feels like the middle of a thought).
5. Starting where the viewer has to ask "Who is that?" or "What are they talking about?".
6. Starting with a boring textbook definition or dry fact (e.g., "If density is greater than water, it sinks."). You MUST find a more emotional, mysterious, or high-stakes hook.

If your chosen start_id violates ANY of the FATAL ERRORS, you MUST pick a different sentence, even if you have to shift the start_id forward or backward by 100 words!
You MUST maximize the "Beginning Quality Score" by picking a start that creates an intense curiosity gap.

RULES FOR END:
- Must end on a complete, final thought.
- Must NOT end on a cliffhanger, conjunction (and, so, but), or mid-sentence.
- Must NOT introduce a new topic that isn't finished.
- Move the end point backwards or forwards to satisfy this.

RETURN:
Return ONLY valid JSON with no markdown and no commentary.
{{
  "start_evaluation": {{
    "requires_previous_context": <boolean>,
    "begins_mid_conversation": <boolean>,
    "stranger_would_understand_first_5_seconds": <boolean>,
    "has_stronger_hook_nearby": <boolean>,
    "creates_curiosity_question": <boolean>
  }},
  "start_id": <int>,
  "end_id": <int>,
  "reasoning": "<string>"
}}
"""

        from shorts_clipper.core.settings import Settings

        settings = Settings.from_env()

        import time

        for attempt in range(1, 4):
            try:
                client = genai.Client(
                    api_key=settings.gemini_api_key or os.environ.get("GEMINI_API_KEY")
                )
                response = client.models.generate_content(
                    model="gemini-3.1-flash-lite",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json",
                    ),
                )
                data = json.loads(response.text)
                start_id = int(data.get("start_id", initial_start_idx))
                end_id = int(data.get("end_id", initial_end_idx))

                # Ensure valid bounds
                start_id = max(0, min(start_id, len(all_words) - 1))
                end_id = max(start_id, min(end_id, len(all_words) - 1))

                log.info(
                    f"EditorialFinisher LLM adjusted: start {initial_start_idx} -> {start_id}, end {initial_end_idx} -> {end_id}"
                )
                log.info(f"Reasoning: {data.get('reasoning')}")
                break
            except Exception as e:
                if attempt == 3:
                    log.warning(
                        f"EditorialFinisher LLM failed after 3 attempts: {e}. Falling back to original bounds."
                    )
                    start_id = initial_start_idx
                    end_id = initial_end_idx
                    break

                log.warning(f"EditorialFinisher LLM failed (attempt {attempt}): {e}. Retrying...")
                time.sleep(2**attempt)

        final_start = all_words[start_id].start
        final_end = getattr(all_words[end_id], "end", all_words[end_id].start)

        log.info(
            f"EditorialFinisher adjusted timestamps: start {target_start:.2f} -> {final_start:.2f}, end {target_end:.2f} -> {final_end:.2f}"
        )

        # Return exact bounds; do not add arbitrary padding, or it will bleed into the next word's audio
        return ClipWindow(start=final_start, end=final_end)
