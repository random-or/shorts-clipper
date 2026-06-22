import logging
import re
from typing import Any

log = logging.getLogger(__name__)

STOP_WORDS = {
    "the",
    "and",
    "is",
    "in",
    "it",
    "to",
    "a",
    "of",
    "for",
    "on",
    "with",
    "as",
    "that",
    "this",
    "by",
    "from",
    "at",
    "but",
    "not",
    "are",
    "was",
    "be",
    "or",
    "an",
    "what",
    "so",
    "if",
    "they",
    "we",
    "you",
    "me",
    "my",
    "your",
    "he",
    "she",
    "his",
    "her",
    "their",
}


def generate_fallback_metadata(
    segments: list[Any], source_title: str = "", source_channel: str = "", niche: str = ""
) -> dict[str, Any]:
    """
    Generates production-grade metadata without any external API calls.
    Used as a fallback when Gemini is unavailable.
    """
    log.info("[FALLBACK] generating local metadata")

    source_title = source_title or ""
    source_channel = source_channel or ""
    niche = niche or ""

    full_text = " ".join([s.text.strip() for s in segments])

    # Split text into sentences for title candidates
    raw_sentences = re.split(r"(?<=[.!?]) +", full_text)
    sentences = [s.strip() for s in raw_sentences if 15 <= len(s) <= 100]

    if not sentences:
        # Fallback if no clean sentences found
        chunks = [full_text[i : i + 80] for i in range(0, len(full_text), 80)]
        sentences = [c.strip() + "..." for c in chunks if len(c.strip()) > 10]

    # Score sentences for Title Generation
    candidates = []
    for s in sentences:
        score = 0
        s_lower = s.lower()

        # Curiosity
        if "?" in s:
            score += 15
        if any(w in s_lower for w in ["why", "how", "secret", "truth", "reason", "never"]):
            score += 10

        # Surprise
        if any(w in s_lower for w in ["shock", "couldn't believe", "crazy", "insane", "wow"]):
            score += 10

        # Conflict
        if any(w in s_lower for w in ["disagree", "wrong", "no", "stop", "bad", "worst", "lie"]):
            score += 10

        # Emotion
        if "!" in s:
            score += 5
        if any(w in s_lower for w in ["hate", "love", "angry", "sad", "happy", "cry"]):
            score += 5

        # Stakes
        if any(w in s_lower for w in ["money", "$", "fail", "success", "life", "die", "win"]):
            score += 10

        candidates.append({"text": s, "score": score})

    # Sort and pick top 5
    candidates.sort(key=lambda x: x["score"], reverse=True)
    top_5 = candidates[:5]

    # Avoid generic or garbage titles if we have candidates
    # If no high score, we just use the text.

    log.info("\n[FALLBACK TITLE]")
    for i, c in enumerate(top_5, 1):
        log.info("Candidate %d (Score: %d): %s", i, c["score"], c["text"])

    selected_title = top_5[0]["text"] if top_5 else source_title[:100]
    # Clean up title formatting
    selected_title = selected_title.capitalize()
    if not selected_title.endswith((".", "!", "?")):
        selected_title += "..."
    if len(selected_title) > 100:
        selected_title = selected_title[:97] + "..."

    log.info("Selected: %s\n", selected_title)

    # Description Generation
    # What happened: first ~150 chars of transcript
    what_happened = full_text[:150] + ("..." if len(full_text) > 150 else "")
    # Why it matters: the hook (highest scoring sentence)
    why_it_matters = top_5[0]["text"] if top_5 else ""

    description_parts = []
    description_parts.append(f"What happened:\n{what_happened}")
    if why_it_matters and why_it_matters != what_happened:
        description_parts.append(
            f"Why it matters:\nThis highlights how {why_it_matters.lower().rstrip('.!?')}."
        )

    if source_title or source_channel:
        src = "Source video: "
        if source_title:
            src += f"'{source_title}' "
        if source_channel:
            src += f"by {source_channel}"
        description_parts.append(src)

    description = "\n\n".join(description_parts)

    # Tag Generation
    words = re.findall(r"\b[a-zA-Z]{4,}\b", full_text.lower())
    word_freq = {}
    for w in words:
        if w not in STOP_WORDS:
            word_freq[w] = word_freq.get(w, 0) + 1

    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    extracted_tags = [w[0] for w in sorted_words[:10]]

    base_tags = ["shorts"]
    if niche:
        base_tags.append(niche.lower())

    final_tags = list(dict.fromkeys(base_tags + extracted_tags))[:15]

    return {"title": selected_title, "description": description, "tags": final_tags}
