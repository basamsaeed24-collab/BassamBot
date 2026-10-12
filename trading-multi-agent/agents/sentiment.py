from __future__ import annotations

from typing import Any


POSITIVE_TERMS = {
    "beat", "beats", "growth", "gain", "gains", "positive", "profit", "record",
    "rise", "rises", "strong", "upgrade", "upgraded", "surge", "surges",
}
NEGATIVE_TERMS = {
    "decline", "declines", "drop", "drops", "downgrade", "downgraded", "fall",
    "falls", "loss", "losses", "negative", "risk", "weak", "warning", "warns",
    "miss", "misses",
}


def analyze_sentiment(news: list[dict[str, Any]]) -> dict[str, Any]:
    positive = 0
    negative = 0
    for item in news:
        words = set("".join(char.lower() if char.isalnum() else " " for char in item.get("title", "")).split())
        positive += len(words & POSITIVE_TERMS)
        negative += len(words & NEGATIVE_TERMS)

    total = positive + negative
    score = (positive - negative) / total if total else 0.0
    label = "POSITIVE" if score > 0.15 else "NEGATIVE" if score < -0.15 else "NEUTRAL"
    return {"score": score, "label": label, "headlines_analyzed": len(news), "positive_terms": positive, "negative_terms": negative}