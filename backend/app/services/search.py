"""
Manual search / filter service (SRS FR-15, Architecture Sec. 4
`services/search.py`, Phase 7).

This is the fallback path UIUX Sec. 1 promises alongside automatic
matching ("Users can filter/search reports manually as a fallback to
automatic matching" — PRD Sec. 8): a straightforward filtered browse over
*active* reports, independent of the matching engine. It deliberately
does not touch embeddings/pgvector — that's matching.py's job — this is
plain metadata filtering (category, color, brand, location, date, status)
plus an optional keyword search over title/description/features, per
FR-15.1. Natural-language (semantic) search is explicitly a post-core
strong addition (FR-15.2) and out of scope here.
"""
from __future__ import annotations

import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.report import Report, ReportType

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


def search_reports(
    db: Session,
    *,
    type: ReportType | None = None,
    category: str | None = None,
    color: str | None = None,
    brand: str | None = None,
    location: str | None = None,
    status: str | None = None,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    q: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[Report]:
    """FR-15.1 — filter by category, color, brand, location, date, and
    status (plus type and a free-text keyword match). Only active reports
    are browsable (PRD/SRS never describe surfacing removed/closed
    reports to other users) unless `status` explicitly narrows further.

    Every filter is optional and additive (AND'd together); omitting all
    of them returns the most recent active reports, which is a reasonable
    "browse everything" default for the Search/Browse screen (UIUX Sec. 5).
    """
    stmt = select(Report).where(Report.is_active == "true")

    if type is not None:
        stmt = stmt.where(Report.type == type)
    if category:
        stmt = stmt.where(Report.category.ilike(category))
    if color:
        stmt = stmt.where(Report.color.ilike(color))
    if brand:
        stmt = stmt.where(Report.brand.ilike(f"%{brand}%"))
    if location:
        stmt = stmt.where(Report.location.ilike(f"%{location}%"))
    if status:
        stmt = stmt.where(Report.status == status)
    if date_from:
        stmt = stmt.where(Report.report_date >= date_from)
    if date_to:
        stmt = stmt.where(Report.report_date <= date_to)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Report.title.ilike(like),
                Report.description.ilike(like),
                Report.features.ilike(like),
            )
        )

    safe_limit = max(1, min(limit, MAX_LIMIT))
    stmt = stmt.order_by(Report.created_at.desc()).limit(safe_limit)

    return list(db.execute(stmt).scalars().all())
