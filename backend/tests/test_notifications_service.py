"""
Phase 6 — tests for services/notifications.py's dedup contract: only
matches whose `just_qualified` flag is True (set by
services/matching.py::find_and_persist_matches on a genuine
threshold-crossing) produce a Notification, so re-running
POST /matches/find/{report_id} never re-spams either report owner.
Uses mocked Session/Report/Match stand-ins, same pattern as
test_matching_candidates.py — no live Postgres needed.
"""
import uuid
from unittest.mock import MagicMock

from app.services.notifications import create_notifications_for_matches


class _FakeReport:
    def __init__(self, user_id=None):
        self.id = uuid.uuid4()
        self.user_id = user_id or uuid.uuid4()


class _FakeMatch:
    def __init__(self, lost_report_id, found_report_id, final_score=80.0, just_qualified=True):
        self.id = uuid.uuid4()
        self.lost_report_id = lost_report_id
        self.found_report_id = found_report_id
        self.final_score = final_score
        self.just_qualified = just_qualified


def _db_returning(*reports_in_order):
    """A MagicMock db whose db.query(Report).filter(...).first() calls
    return the given fake reports in order, one per call."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = list(reports_in_order)
    return db


def test_creates_notification_for_both_owners_when_qualified():
    lost = _FakeReport()
    found = _FakeReport()
    match = _FakeMatch(lost.id, found.id, final_score=82.0, just_qualified=True)
    db = _db_returning(lost, found)

    created = create_notifications_for_matches(db, [match])

    assert len(created) == 2
    assert {n.user_id for n in created} == {lost.user_id, found.user_id}
    assert all(n.match_id == match.id for n in created)
    db.commit.assert_called_once()


def test_skips_matches_that_did_not_just_qualify():
    """A match that already qualified on an earlier run (just_qualified
    False) must never produce a second notification."""
    match = _FakeMatch(uuid.uuid4(), uuid.uuid4(), final_score=95.0, just_qualified=False)
    db = MagicMock()

    created = create_notifications_for_matches(db, [match])

    assert created == []
    db.query.assert_not_called()
    db.commit.assert_not_called()


def test_missing_just_qualified_attribute_defaults_to_skip():
    """A match object without the transient attribute at all (e.g. one
    loaded directly from the DB outside find_and_persist_matches) must
    never notify — getattr(..., False) default."""

    class _BareMatch:
        def __init__(self):
            self.id = uuid.uuid4()
            self.lost_report_id = uuid.uuid4()
            self.found_report_id = uuid.uuid4()
            self.final_score = 99.0

    db = MagicMock()
    created = create_notifications_for_matches(db, [_BareMatch()])

    assert created == []


def test_same_user_owns_both_reports_gets_one_notification():
    """Self-matches shouldn't occur (matching.py excludes them), but the
    owner-dedup via `set` must hold defensively regardless."""
    shared_user = uuid.uuid4()
    lost = _FakeReport(user_id=shared_user)
    found = _FakeReport(user_id=shared_user)
    match = _FakeMatch(lost.id, found.id, final_score=90.0, just_qualified=True)
    db = _db_returning(lost, found)

    created = create_notifications_for_matches(db, [match])

    assert len(created) == 1
    assert created[0].user_id == shared_user


def test_skips_and_logs_when_referenced_report_is_missing():
    """Shouldn't happen (FKs enforce it) but must never crash the whole
    batch over one bad lookup."""
    match = _FakeMatch(uuid.uuid4(), uuid.uuid4(), final_score=90.0, just_qualified=True)
    db = _db_returning(None, None)  # neither report found

    created = create_notifications_for_matches(db, [match])

    assert created == []
    db.commit.assert_not_called()


def test_no_qualifying_matches_never_commits():
    db = MagicMock()

    created = create_notifications_for_matches(db, [])

    assert created == []
    db.commit.assert_not_called()
