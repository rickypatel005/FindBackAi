import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.report import FOUND_TRANSITIONS, LOST_TRANSITIONS, Report, ReportStatus, ReportType
from app.schemas.report import ReportCreate
from app.services import embeddings, vision


def create_report(db: Session, user_id: uuid.UUID, report_type: ReportType, payload: ReportCreate) -> Report:
    if not (1 <= len(payload.image_urls) <= 3):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A report requires between 1 and 3 images.",
        )

    initial_status = ReportStatus.SEARCHING if report_type == ReportType.LOST else ReportStatus.UNCLAIMED

    # image_embeddings isn't a Report column (Phase 3) — pop it off before
    # building the model and fold it into image_embedding instead (FR-06.2:
    # "embeddings may be averaged or the primary image used"; this MVP
    # averages).
    data = payload.model_dump(exclude={"image_embeddings"})

    report = Report(
        user_id=user_id,
        type=report_type,
        status=initial_status.value,
        **data,
    )

    if payload.image_embeddings:
        try:
            report.image_embedding = vision.average_embeddings(payload.image_embeddings)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # FR-05.1 — Title + Description + Features are concatenated and
    # encoded on every report creation, no client round-trip required
    # (mirrors how image_embedding is derived server-side above).
    report.text_embedding = embeddings.embed_report_text(
        report.title, report.description, report.features
    )

    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# Text fields that feed the embedding (FR-05.1) — used by
# `maybe_reencode_text` to decide whether a PATCH needs a re-encode.
_TEXT_EMBEDDING_FIELDS = {"title", "description", "features"}


def maybe_reencode_text(report: Report, updated_fields: set[str]) -> None:
    """FR-05.2 — re-encoding occurs whenever the underlying text fields
    (title/description/features) are edited. Callers pass the set of
    field names actually present in the PATCH payload so an unrelated
    update (e.g. just `status`) doesn't trigger a needless re-encode."""
    if updated_fields & _TEXT_EMBEDDING_FIELDS:
        report.text_embedding = embeddings.embed_report_text(
            report.title, report.description, report.features
        )


def transition_status(db: Session, report: Report, new_status: ReportStatus) -> Report:
    """Enforces SRS FR-14.1 — arbitrary status jumps are rejected."""
    transitions = LOST_TRANSITIONS if report.type == ReportType.LOST else FOUND_TRANSITIONS
    current = ReportStatus(report.status)
    allowed = transitions.get(current, set())

    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {current.value} to {new_status.value}. "
            f"Allowed: {[s.value for s in allowed]}",
        )

    report.status = new_status.value
    db.commit()
    db.refresh(report)
    return report


def assert_owner_or_admin(report: Report, user_id: uuid.UUID, is_admin: bool) -> None:
    if not is_admin and report.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the owner of this report")
