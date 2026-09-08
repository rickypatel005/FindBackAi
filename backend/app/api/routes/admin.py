import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.session import get_db
from app.models.match import Match
from app.models.report import FOUND_TRANSITIONS, LOST_TRANSITIONS, Report, ReportStatus, ReportType
from app.schemas.duplicate import DuplicatePairOut, MatchResolveOut
from app.schemas.report import ReportOut
from app.services.duplicates import find_duplicate_pairs
from app.services.reports import transition_status

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """SRS FR-17.1 — total/lost/found/potential-match/recovered/pending counts."""
    total = db.query(Report).count()
    lost = db.query(Report).filter(Report.type == ReportType.LOST).count()
    found = db.query(Report).filter(Report.type == ReportType.FOUND).count()
    potential = db.query(Report).filter(
        Report.status.in_([ReportStatus.MATCH_FOUND.value, ReportStatus.POTENTIAL_OWNER_FOUND.value])
    ).count()
    recovered = db.query(Report).filter(
        Report.status.in_([ReportStatus.RECOVERED.value, ReportStatus.RETURNED.value])
    ).count()
    # Phase 7 — FR-16 duplicate-review queue folded into the same stat
    # card row so "pending review" doesn't need its own dashboard trip.
    pending_review = len(find_duplicate_pairs(db))

    # Phase 9 — Sample analytics: category distribution & recovery rate
    category_counts: dict[str, int] = {}
    reports = db.query(Report).all()
    for r in reports:
        category_counts[r.category] = category_counts.get(r.category, 0) + 1

    recovery_rate = round((recovered / total * 100), 1) if total > 0 else 0.0

    return {
        "total": total,
        "lost": lost,
        "found": found,
        "potential_matches": potential,
        "recovered": recovered,
        "pending_review": pending_review,
        "recovery_rate": recovery_rate,
        "category_counts": category_counts,
    }


@router.get("/reports", response_model=list[ReportOut])
def list_all_reports(
    type: ReportType | None = None,
    status_filter: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
):
    """SRS FR-17.2 / UIUX Sec. 5 'bulk filters'. Query param is
    `status_filter` (not `status`) to avoid colliding with FastAPI's
    reserved `status` import used elsewhere in this module."""
    stmt = db.query(Report)
    if type is not None:
        stmt = stmt.filter(Report.type == type)
    if status_filter:
        stmt = stmt.filter(Report.status == status_filter)
    if category:
        stmt = stmt.filter(Report.category == category)
    return stmt.all()


@router.get("/duplicates", response_model=list[DuplicatePairOut])
def get_duplicate_candidates(type: ReportType | None = None, db: Session = Depends(get_db)):
    """SRS FR-16.1 — same-type pairs flagged for admin review. Never
    auto-merged; the admin decides what (if anything) to do with each
    pair via the existing `mark_duplicate` moderation action."""
    pairs = find_duplicate_pairs(db, report_type=type)
    # Explicit ReportOut conversion (see resolve_match's comment above)
    # rather than leaning on implicit dict-of-ORM-objects coercion.
    return [
        DuplicatePairOut(
            report_a=ReportOut.model_validate(p["report_a"]),
            report_b=ReportOut.model_validate(p["report_b"]),
            similarity=p["similarity"],
            type=p["type"],
        )
        for p in pairs
    ]


@router.patch("/reports/{report_id}", response_model=ReportOut)
def moderate_report(report_id: uuid.UUID, action: str, db: Session = Depends(get_db)):
    """SRS FR-17.2 — mark duplicate / remove / resolve / close, admin-only."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if action == "remove":
        report.is_active = "false"
    elif action == "close":
        report.status = ReportStatus.CLOSED.value
    elif action == "mark_duplicate":
        report.is_active = "false"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown action")

    db.commit()
    db.refresh(report)
    return report


def _advance_to_terminal(db: Session, report: Report) -> Report:
    """Walks a report toward its terminal recovered/returned status,
    stepping through the required intermediate state first when
    necessary (SRS FR-14.1 — no arbitrary jumps, even for admins).
    No-ops if the report is already terminal (RECOVERED/RETURNED/CLOSED)."""
    transitions = LOST_TRANSITIONS if report.type == ReportType.LOST else FOUND_TRANSITIONS
    terminal = ReportStatus.RECOVERED if report.type == ReportType.LOST else ReportStatus.RETURNED
    intermediate = ReportStatus.MATCH_FOUND if report.type == ReportType.LOST else ReportStatus.POTENTIAL_OWNER_FOUND

    current = ReportStatus(report.status)
    if current == terminal or current == ReportStatus.CLOSED:
        return report
    if current != intermediate and intermediate in transitions.get(current, set()):
        report = transition_status(db, report, intermediate)
        current = ReportStatus(report.status)
    if terminal in transitions.get(current, set()):
        report = transition_status(db, report, terminal)
    return report


@router.patch("/matches/{match_id}/resolve", response_model=MatchResolveOut)
def resolve_match(match_id: uuid.UUID, db: Session = Depends(get_db)):
    """SRS FR-17.2 'resolve match' admin action — advances both sides of
    a confirmed match toward their terminal recovered/returned status."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    lost = db.query(Report).filter(Report.id == match.lost_report_id).first()
    found = db.query(Report).filter(Report.id == match.found_report_id).first()
    if not lost or not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Underlying report(s) not found")

    lost = _advance_to_terminal(db, lost)
    found = _advance_to_terminal(db, found)
    # Constructed explicitly (rather than returning a raw dict of ORM
    # objects) so the ReportOut.from_attributes conversion is guaranteed
    # to run for both nested reports regardless of response_model wiring.
    return MatchResolveOut(lost_report=ReportOut.model_validate(lost), found_report=ReportOut.model_validate(found))
