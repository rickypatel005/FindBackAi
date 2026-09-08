"""
Duplicate detection (SRS FR-16, PRD Sec. 10 "Strong Addition", Phase 7).

Flags reports with very high mutual similarity *within the same type*
(LOST-LOST or FOUND-FOUND) for admin review — never auto-merged
(FR-16.1: "flagged for admin review, not auto-merged"). This is
deliberately a distinct question from matching.py's job, which scores
*opposite*-type pairs to find candidate reunions; this module looks for
same-type pairs that likely describe the exact same report (e.g. a
duplicate submission, or two different people reporting the same found
item) rather than two different items that happen to belong together.

Reuses matching.py's cosine-similarity math so a "duplicate" is judged
against the same yardstick used for match scoring.
"""
from __future__ import annotations

import itertools

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.report import Report, ReportType
from app.services.matching import _cosine_similarity  # reuse identical scoring math

settings = get_settings()


def _pair_similarity(a: Report, b: Report) -> float:
    """Average of image + text cosine similarity (0-100) — the two
    strongest identity signals (60% combined weight in matching.py).
    Metadata fields (category/color/location) are deliberately excluded:
    two genuinely different items of the same category/color/location
    shouldn't get flagged as duplicates just because their metadata lines
    up; a duplicate needs the photo and description to actually match.
    """
    image_sim = _cosine_similarity(
        list(a.image_embedding) if a.image_embedding is not None else None,
        list(b.image_embedding) if b.image_embedding is not None else None,
    )
    text_sim = _cosine_similarity(
        list(a.text_embedding) if a.text_embedding is not None else None,
        list(b.text_embedding) if b.text_embedding is not None else None,
    )
    return (image_sim + text_sim) / 2.0


def find_duplicate_pairs(db: Session, report_type: ReportType | None = None) -> list[dict]:
    """FR-16.1 — scans active reports within the same type for mutual
    similarity at/above DUPLICATE_SIMILARITY_THRESHOLD.

    O(n^2) over active reports of a given type: acceptable at MVP/admin-
    review scale since this runs on-demand for the admin dashboard, not
    on the report-submission hot path (matching.py's candidate retrieval
    is the one that needs the pgvector prefilter, per Architecture Sec.
    12). Revisit with a pgvector self-join if report volume grows past
    what a demo/MVP needs.
    """
    types = [report_type] if report_type is not None else [ReportType.LOST, ReportType.FOUND]
    flagged: list[dict] = []

    for t in types:
        stmt = select(Report).where(Report.type == t, Report.is_active == "true")
        reports = list(db.execute(stmt).scalars().all())

        for a, b in itertools.combinations(reports, 2):
            similarity = _pair_similarity(a, b)
            if similarity >= settings.DUPLICATE_SIMILARITY_THRESHOLD:
                flagged.append(
                    {
                        "report_a": a,
                        "report_b": b,
                        "similarity": round(similarity, 2),
                        "type": t.value,
                    }
                )

    flagged.sort(key=lambda f: f["similarity"], reverse=True)
    return flagged
