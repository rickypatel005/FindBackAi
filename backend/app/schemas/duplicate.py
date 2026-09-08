from pydantic import BaseModel

from app.schemas.report import ReportOut


class DuplicatePairOut(BaseModel):
    """SRS FR-16.1 — a same-type pair flagged for admin review. Never
    represents an auto-merge decision, only a suggestion."""

    report_a: ReportOut
    report_b: ReportOut
    similarity: float
    type: str


class MatchResolveOut(BaseModel):
    """Response for the admin 'resolve match' action (FR-17.2) — both
    sides of the match after being advanced toward their terminal
    recovered/returned status."""

    lost_report: ReportOut
    found_report: ReportOut
