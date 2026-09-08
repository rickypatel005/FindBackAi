import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.match import Match
from app.models.report import Report
from app.models.user import User
from app.schemas.match import MatchOut
from app.services.matching import find_and_persist_matches
from app.services.notifications import create_notifications_for_matches

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("/find/{report_id}", response_model=list[MatchOut])
def find_matches(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    top_matches = find_and_persist_matches(db, report)

    # SRS FR-12.1 — notify the owner(s) of any match that just crossed the
    # threshold on this run (Phase 6: dedup lives in the matching service's
    # `just_qualified` flag, so re-running this endpoint never re-notifies
    # a pair that already qualified on an earlier call).
    create_notifications_for_matches(db, top_matches)

    return top_matches


@router.get("/{report_id}", response_model=list[MatchOut])
def get_matches_for_report(report_id: uuid.UUID, db: Session = Depends(get_db)):
    matches = (
        db.query(Match)
        .filter((Match.lost_report_id == report_id) | (Match.found_report_id == report_id))
        .order_by(Match.final_score.desc())
        .all()
    )
    return matches


@router.get("/{match_id}/details", response_model=MatchOut)
def get_match_details(match_id: uuid.UUID, db: Session = Depends(get_db)):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return match
