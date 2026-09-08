"""
Matching engine (SRS FR-07/FR-08/FR-09/FR-10, Architecture Sec. 7).

Phase 1 note (historical): this module defined the pipeline shape and
scoring contract early so Phase 3 (image pipeline) and Phase 4 (text
pipeline) could plug in real embeddings without changing the interface.
Both are now wired in (app/services/vision.py, app/services/embeddings.py).
Phase 5 adds the actual pgvector similarity narrowing described in
FR-07.2 (see `_vector_prefilter_candidates` below) on top of the FR-07.1
hard filters that were already in place.
Component similarity functions still operate on whatever embeddings are
present; a report with a zero-vector fallback embedding (ML deps not
installed) simply scores 0 on that component rather than erroring.

Phase 6 note: `find_and_persist_matches` now upserts by (lost_report_id,
found_report_id) instead of inserting a fresh row per call, and only
flags a match `just_qualified` (see `_should_notify`) the first time it
crosses `MATCH_NOTIFICATION_THRESHOLD` — see
migrations/004_match_constraints.sql and services/notifications.py.
"""
import datetime
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.match import Match
from app.models.report import Report, ReportType
from app.services.embeddings import normalize_location

settings = get_settings()
logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b))) * 100.0


def _text_equal_score(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    return 100.0 if a.strip().lower() == b.strip().lower() else 0.0


def _location_score(a: str | None, b: str | None) -> float:
    """SRS FR-08.1 location component — normalized via
    embeddings.normalize_location (Phase 4 metadata normalization) so
    superficial phrasing differences ("Bldg 3" vs "Building 3") don't
    zero out an otherwise-real location match, without any GPS dependency
    (PRD Sec. 12/13)."""
    norm_a, norm_b = normalize_location(a), normalize_location(b)
    if not norm_a or not norm_b:
        return 0.0
    return 100.0 if norm_a == norm_b else 0.0


def _time_decay_score(date_a: datetime.date, date_b: datetime.date, half_life_days: int = 7) -> float:
    delta_days = abs((date_a - date_b).days)
    # Simple exponential decay: full score at 0 days, ~50% at half_life_days.
    return 100.0 * (0.5 ** (delta_days / half_life_days))


def _has_usable_embedding(vec) -> bool:
    """A stored embedding is only useful for pgvector distance ordering if
    it's non-null AND not an all-zero fallback vector (Phase 3/4's
    documented degrade path when CLIP/Sentence-Transformers aren't
    installed). pgvector's cosine_distance raises on zero-norm vectors, so
    treating an all-zero vector as "usable" would crash the query instead
    of just contributing no signal."""
    return vec is not None and any(v != 0 for v in vec)


def _vector_prefilter_candidates(db: Session, report: Report, base_stmt) -> list[Report] | None:
    """SRS FR-07.2 — narrow the FR-07.1 hard-filtered candidate set via
    pgvector cosine-distance ordering *before* full scoring (FR-07.3), so
    scoring doesn't run against the entire opposite-type table as report
    volume grows (Architecture Sec. 12).

    Returns None — signalling the caller to fall back to the full
    hard-filtered scan — whenever narrowing isn't possible or safe:
      - the report itself has no usable (non-zero) embedding to order by,
      - the connected DB doesn't support pgvector's `<=>` operator (e.g.
        the sqlite-backed unit test suite; see conftest.py), or
      - pgvector rejects the comparison for any other reason.
    This mirrors the rest of the codebase's "degrade, never crash" pattern
    (vision.py / embeddings.py).
    """
    order_expr = None
    if _has_usable_embedding(report.image_embedding):
        order_expr = Report.image_embedding.cosine_distance(list(report.image_embedding))
    if _has_usable_embedding(report.text_embedding):
        text_expr = Report.text_embedding.cosine_distance(list(report.text_embedding))
        order_expr = text_expr if order_expr is None else (order_expr + text_expr)

    if order_expr is None:
        return None  # no embedding signal on this report yet — nothing to narrow by

    try:
        stmt = base_stmt.order_by(order_expr).limit(settings.CANDIDATE_POOL_SIZE)
        return list(db.execute(stmt).scalars().all())
    except Exception:  # noqa: BLE001 - e.g. sqlite in tests, or a zero-norm candidate row
        logger.warning(
            "pgvector candidate prefilter unavailable/failed — falling back to the "
            "full hard-filtered scan for report %s.",
            report.id,
            exc_info=True,
        )
        db.rollback()
        return None


def get_candidates(db: Session, report: Report, category_filter: str | None = None) -> list[Report]:
    """SRS FR-07.1/07.2 — hard filters (opposite type, active status,
    optional category, no self-matching), then pgvector similarity
    narrowing on top when the report has a usable embedding and the DB
    supports it."""
    opposite_type = ReportType.FOUND if report.type == ReportType.LOST else ReportType.LOST

    base_stmt = select(Report).where(
        Report.type == opposite_type,
        Report.is_active == "true",
        Report.user_id != report.user_id,  # exclude self-matches (SRS Business Rules)
    )
    if category_filter:
        base_stmt = base_stmt.where(Report.category == category_filter)

    if settings.ENABLE_VECTOR_PREFILTER:
        narrowed = _vector_prefilter_candidates(db, report, base_stmt)
        if narrowed is not None:
            return narrowed

    # Fallback (also the whole path for small/MVP-scale demo data, or when
    # this report has no embeddings yet): score the full hard-filtered set
    # directly — still satisfies the same FR-07/FR-08 acceptance criteria.
    candidates = db.execute(base_stmt).scalars().all()
    return list(candidates)


def score_pair(lost: Report, found: Report) -> dict:
    """SRS FR-08.1 — weighted final score from normalized 0-100 components."""
    image_score = _cosine_similarity(
        list(lost.image_embedding) if lost.image_embedding is not None else None,
        list(found.image_embedding) if found.image_embedding is not None else None,
    )
    text_score = _cosine_similarity(
        list(lost.text_embedding) if lost.text_embedding is not None else None,
        list(found.text_embedding) if found.text_embedding is not None else None,
    )
    category_score = _text_equal_score(lost.category, found.category)
    color_score = _text_equal_score(lost.color, found.color)
    brand_score = _text_equal_score(lost.brand, found.brand)
    location_score = _location_score(lost.location, found.location)
    time_score = _time_decay_score(lost.report_date, found.report_date)
    other_score = 0.0  # reserved for distinguishing-feature matching (post-core)

    final_score = (
        image_score * settings.WEIGHT_IMAGE
        + text_score * settings.WEIGHT_TEXT
        + category_score * settings.WEIGHT_CATEGORY
        + color_score * settings.WEIGHT_COLOR
        + location_score * settings.WEIGHT_LOCATION
        + time_score * settings.WEIGHT_TIME
        + other_score * settings.WEIGHT_OTHER
    )

    return {
        "image_score": round(image_score, 2),
        "text_score": round(text_score, 2),
        "category_score": round(category_score, 2),
        "color_score": round(color_score, 2),
        "brand_score": round(brand_score, 2),
        "location_score": round(location_score, 2),
        "time_score": round(time_score, 2),
        "other_score": round(other_score, 2),
        "final_score": round(final_score, 2),
    }


def build_explanation(scores: dict) -> list[str]:
    """SRS FR-10.2 — a reason is never shown unless its component score
    exceeds the configured threshold. No fabricated explanations."""
    threshold = settings.EXPLANATION_COMPONENT_THRESHOLD
    reasons = []
    if scores["image_score"] >= threshold:
        reasons.append("Similar appearance")
    if scores["text_score"] >= threshold:
        reasons.append("Similar description")
    if scores["category_score"] >= threshold:
        reasons.append("Same category")
    if scores["color_score"] >= threshold:
        reasons.append("Same color")
    if scores["brand_score"] >= threshold:
        reasons.append("Same brand")
    if scores["location_score"] >= threshold:
        reasons.append("Same location")
    if scores["time_score"] >= threshold:
        reasons.append("Reported around the same time")
    return reasons


def _find_existing_match(db: Session, lost_report_id, found_report_id) -> Match | None:
    """Phase 6 fix — look up any previously-persisted Match for this exact
    (lost, found) pair. Without this, re-running /matches/find/{report_id}
    (a repeated "check matches" click, or a re-score after the user edits
    their report text) inserted a brand-new Match row every time, which
    both duplicated data and re-fired a notification on every call. See
    migrations/004_match_constraints.sql for the matching DB-level unique
    constraint that backstops this in application code.
    """
    stmt = select(Match).where(
        Match.lost_report_id == lost_report_id,
        Match.found_report_id == found_report_id,
    )
    return db.execute(stmt).scalars().first()


def _should_notify(previous_final_score: float | None, new_final_score: float) -> bool:
    """SRS FR-12.1 rising-edge check: a pair should notify the *first*
    time it crosses MATCH_NOTIFICATION_THRESHOLD, never on every re-score.
    `previous_final_score` is None for a pair with no prior Match row.
    If a pair drops below threshold and later crosses again, that's
    treated as a fresh notification-worthy event.
    """
    threshold = settings.MATCH_NOTIFICATION_THRESHOLD
    was_qualified = previous_final_score is not None and previous_final_score >= threshold
    now_qualified = new_final_score >= threshold
    return now_qualified and not was_qualified


def find_and_persist_matches(db: Session, report: Report) -> list[Match]:
    candidates = get_candidates(db, report)
    results: list[Match] = []

    for candidate in candidates:
        lost = report if report.type == ReportType.LOST else candidate
        found = candidate if report.type == ReportType.LOST else report

        scores = score_pair(lost, found)
        explanation = build_explanation(scores)

        existing = _find_existing_match(db, lost.id, found.id)
        previous_final_score = existing.final_score if existing is not None else None

        if existing is not None:
            # Upsert (Phase 6 fix): update the same row instead of
            # inserting a duplicate for a pair we've already scored.
            for field, value in scores.items():
                setattr(existing, field, value)
            existing.explanation = explanation
            existing.updated_at = datetime.datetime.now(datetime.timezone.utc)
            match = existing
        else:
            match = Match(
                id=uuid.uuid4(),
                lost_report_id=lost.id,
                found_report_id=found.id,
                explanation=explanation,
                **scores,
            )
            db.add(match)

        # Transient (non-persisted) flag consumed by
        # services/notifications.py::create_notifications_for_matches —
        # only True on a genuine threshold-crossing this run.
        match.just_qualified = _should_notify(previous_final_score, scores["final_score"])
        results.append(match)

    db.commit()
    for match in results:
        db.refresh(match)

    # SRS FR-09 — rank descending, return top-K (persist all, surface top-K).
    results.sort(key=lambda m: m.final_score, reverse=True)
    return results[: settings.TOP_K_MATCHES]
