"""
Report-quality suggestions service (SRS FR-18, Architecture Sec. 4).

Simple, dependency-free heuristics that flag weak/short descriptions and
suggest distinguishing details before submission. Deliberately
conservative — this is advisory only (UIUX Sec. 1: "show AI, don't
lecture") and never blocks submission (SRS Sec. 8 edge-case table has no
entry that rejects a report for a weak description).
"""
from __future__ import annotations

MIN_DESCRIPTION_LENGTH = 30

# Distinguishing-detail keywords (FR-18.1 example list: "scratches,
# stickers, serial numbers"). Kept small and generic for MVP.
_DISTINGUISHING_KEYWORDS = [
    "scratch", "sticker", "serial", "engrav", "dent", "mark", "logo",
    "crack", "chip", "initial", "monogram", "tag", "keychain", "case",
    "cover", "strap", "charm",
]

_VAGUE_TITLES = {"item", "thing", "stuff", "object", "lost item", "found item"}


def check_description(description: str) -> dict:
    """FR-18.1 — flags weak/short descriptions, suggests adding
    distinguishing details. Returns `is_weak` plus a list of concrete,
    actionable suggestions (never a bare pass/fail)."""
    text = (description or "").strip()
    suggestions: list[str] = []

    if len(text) < MIN_DESCRIPTION_LENGTH:
        suggestions.append(
            "Your description is quite short — consider adding a sentence or two of detail."
        )

    if not any(keyword in text.lower() for keyword in _DISTINGUISHING_KEYWORDS):
        suggestions.append(
            "Mentioning unique marks (scratches, stickers, serial numbers, engravings) helps matching."
        )

    word_count = len(text.split())
    if 0 < word_count < 5:
        suggestions.append("Try describing the item in a full sentence rather than a few words.")

    return {"is_weak": len(suggestions) > 0, "suggestions": suggestions}


def check_title(title: str) -> list[str]:
    """Lightweight companion check for the title field — flags generic
    placeholders like 'Item' or 'Lost item' that carry no search signal."""
    text = (title or "").strip().lower()
    if not text or text in _VAGUE_TITLES:
        return ["Try a more specific title, e.g. the brand or color plus the item type."]
    return []


def check_report_quality(title: str | None, description: str) -> dict:
    """Convenience wrapper combining title + description checks, used by
    the /ai/check-report-quality route."""
    result = check_description(description)
    result["suggestions"] = check_title(title) + result["suggestions"]
    result["is_weak"] = len(result["suggestions"]) > 0
    return result
