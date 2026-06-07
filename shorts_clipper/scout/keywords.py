"""
Niche-aware keyword map for scout query generation.
Add new niches here. Do not use rotating random keywords.
Each niche maps to specific, relevant search terms.
"""

NICHE_KEYWORDS: dict[str, list[str]] = {
    "tech": [
        "AI news",
        "OpenAI",
        "Anthropic",
        "Apple",
        "Google",
        "Tesla",
        "robotics",
        "startups",
        "programming",
        "cybersecurity",
        "GPU",
        "semiconductor",
        "smartphone review",
        "software engineering",
        "machine learning",
        "open source",
    ],
    "gaming": [
        "gameplay",
        "boss fight",
        "speedrun",
        "game review",
        "tips tricks",
        "esports",
        "tournament",
        "game update",
        "patch notes",
        "walkthrough",
        "new release",
        "indie game",
    ],
    "finance": [
        "stock market",
        "investing",
        "crypto",
        "economy news",
        "earnings report",
        "Federal Reserve",
        "inflation",
        "day trading",
        "ETF",
        "portfolio",
        "recession",
        "interest rates",
    ],
    "fitness": [
        "workout routine",
        "diet plan",
        "weight loss",
        "muscle building",
        "nutrition",
        "cardio",
        "strength training",
        "running tips",
        "yoga",
        "recovery",
        "meal prep",
    ],
    "news": [
        "breaking news",
        "politics",
        "world news",
        "analysis",
        "interview",
        "election",
        "policy",
        "government",
        "geopolitics",
    ],
    "cooking": [
        "recipe",
        "cooking tips",
        "meal prep",
        "restaurant review",
        "baking",
        "cuisine",
        "food hack",
        "chef",
    ],
    "sports": [
        "highlights",
        "match recap",
        "transfer news",
        "analysis",
        "player interview",
        "training",
        "championship",
    ],
}


def get_keywords(niche: str) -> list[str]:
    """
    Return keyword list for a niche.
    Falls back to [niche] if not found — never injects unrelated terms.
    """
    niche_lower = niche.lower().strip()
    for key, kws in NICHE_KEYWORDS.items():
        if key in niche_lower or niche_lower in key:
            return kws
    # Unknown niche: use the niche itself as the only keyword
    # This is intentional — unknown niche gets clean searches, not random words
    return [niche_lower]


def build_queries(niche: str, keyword: str | None, count: int = 4) -> list[str]:
    """
    Build search queries for discovery.
    If keyword is provided by user, use it directly — don't inject niche terms.
    If niche only, sample from keyword map.
    """
    import random

    if keyword:
        return [
            f"ytsearch15:{keyword}",
            f"ytsearch15:{keyword} explained",
            f"ytsearch15:{keyword} review",
            f"ytsearch15:best {keyword}",
        ]
    kws = get_keywords(niche)
    selected = random.sample(kws, min(count, len(kws)))
    return [f"ytsearch15:{niche} {kw}" for kw in selected]
