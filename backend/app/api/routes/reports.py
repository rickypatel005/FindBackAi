import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.report import Report, ReportType
from app.models.user import RoleEnum, User
from app.schemas.report import ReportCreate, ReportOut, ReportUpdate
from app.services import search as search_service
from app.services.reports import assert_owner_or_admin, create_report, maybe_reencode_text

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/lost", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_lost_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_report(db, current_user.id, ReportType.LOST, payload)


@router.post("/found", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_found_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_report(db, current_user.id, ReportType.FOUND, payload)


@router.get("/mine", response_model=list[ReportOut])
def list_my_reports(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Report).filter(Report.user_id == current_user.id).all()


@router.get("/search", response_model=list[ReportOut])
def search_reports(
    type: ReportType | None = None,
    category: str | None = None,
    color: str | None = None,
    brand: str | None = None,
    location: str | None = None,
    status: str | None = None,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS FR-15.1 — manual search/filter fallback (category, color,
    brand, location, date, status, plus a free-text `q`). Declared ahead
    of `/{report_id}` so "search" is never swallowed as a UUID path
    param. Requires auth like every other report-browsing route (SRS
    Section 2: search/browse is a `User` permission, not `Guest`).
    """
    return search_service.search_reports(
        db,
        type=type,
        category=category,
        color=color,
        brand=brand,
        location=location,
        status=status,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: uuid.UUID, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.patch("/{report_id}", response_model=ReportOut)
def update_report(
    report_id: uuid.UUID,
    payload: ReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    assert_owner_or_admin(report, current_user.id, current_user.role == RoleEnum.ADMIN)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(report, field, value)

    # FR-05.2 — re-encode the text embedding whenever title/description/
    # features change, so matching always reflects the current text.
    maybe_reencode_text(report, set(updates.keys()))

    db.commit()
    db.refresh(report)
    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS FR-19.4 — deleting a report removes it and (via cascade in the
    real DB schema) its dependent matches/notifications/images."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    assert_owner_or_admin(report, current_user.id, current_user.role == RoleEnum.ADMIN)

    db.delete(report)
    db.commit()
    return None
