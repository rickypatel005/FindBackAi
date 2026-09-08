"""
Notifications service (Architecture Sec. 4: "Notifications service
(services/notifications.py): threshold checks + notification creation.")

Phase 6 adds this file: the threshold check and Notification creation used
to live inline inside app/api/routes/matches.py. Pulling it out here does
two things:

1. Matches the component boundary the Architecture doc already described,
   so the route stays a thin HTTP adapter (find matches -> notify -> return).
2. Makes the "who gets notified for what" logic unit-testable without a
   live Postgres/pgvector connection (see tests/test_notifications_service.py),
   the same "test the pure logic, not the DB" pattern already used for
   matching.py's scoring helpers.

SRS FR-12.1 — a new report producing a match at/above the configured
threshold creates an in-app notification for the affected user(s).
Dedup: this only acts on matches whose `just_qualified` flag (set by
`app/services/matching.py::find_and_persist_matches`) is True, so a match
that already cleared the threshold on an earlier run — and so already has
a notification — is never re-notified just because /matches/find was
called again (e.g. the user re-checks, or edits an unrelated field).
"""
import logging

from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.notification import Notification
from app.models.report import Report

logger = logging.getLogger(__name__)


def create_notifications_for_matches(db: Session, matches: list[Match]) -> list[Notification]:
    """Create a Notification for each owner of every match that just
    crossed the notification threshold on this run. Safe to call with a
    mix of qualifying and non-qualifying matches — non-qualifying ones
    (`just_qualified` False or unset) are skipped."""
    created: list[Notification] = []

    for match in matches:
        if not getattr(match, "just_qualified", False):
            continue

        lost = db.query(Report).filter(Report.id == match.lost_report_id).first()
        found = db.query(Report).filter(Report.id == match.found_report_id).first()
        if not lost or not found:
            # Shouldn't happen (FKs enforce this), but never crash the
            # matching response over a notification-side lookup miss.
            logger.warning("Match %s references a missing report; skipping notification.", match.id)
            continue

        for owner_id in {lost.user_id, found.user_id}:
            notification = Notification(
                user_id=owner_id,
                match_id=match.id,
                title="Strong potential match found",
                message=f"A potential match scored {match.final_score:.0f}/100.",
            )
            db.add(notification)
            created.append(notification)

    if created:
        db.commit()

    return created
