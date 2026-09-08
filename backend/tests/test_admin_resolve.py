"""
Phase 7 — tests for the admin "resolve match" status-advancement helper
(SRS FR-17.2, FR-14.1). Uses a lightweight fake report + a mocked Session
(transition_status only calls db.commit()/db.refresh(), both no-ops on a
MagicMock) rather than a real Postgres connection — same rationale as
test_matching_candidates.py.
"""
from unittest.mock import MagicMock

from app.api.routes.admin import _advance_to_terminal
from app.models.report import ReportStatus, ReportType


class _FakeReport:
    def __init__(self, report_type: ReportType, status_value: str):
        self.type = report_type
        self.status = status_value


def test_advance_lost_from_searching_reaches_recovered():
    db = MagicMock()
    report = _FakeReport(ReportType.LOST, ReportStatus.SEARCHING.value)

    result = _advance_to_terminal(db, report)

    assert result.status == ReportStatus.RECOVERED.value


def test_advance_lost_from_match_found_reaches_recovered():
    db = MagicMock()
    report = _FakeReport(ReportType.LOST, ReportStatus.MATCH_FOUND.value)

    result = _advance_to_terminal(db, report)

    assert result.status == ReportStatus.RECOVERED.value


def test_advance_found_from_unclaimed_reaches_returned():
    db = MagicMock()
    report = _FakeReport(ReportType.FOUND, ReportStatus.UNCLAIMED.value)

    result = _advance_to_terminal(db, report)

    assert result.status == ReportStatus.RETURNED.value


def test_advance_is_noop_when_already_closed():
    db = MagicMock()
    report = _FakeReport(ReportType.LOST, ReportStatus.CLOSED.value)

    result = _advance_to_terminal(db, report)

    assert result.status == ReportStatus.CLOSED.value
    db.commit.assert_not_called()


def test_advance_is_noop_when_already_terminal():
    db = MagicMock()
    report = _FakeReport(ReportType.FOUND, ReportStatus.RETURNED.value)

    result = _advance_to_terminal(db, report)

    assert result.status == ReportStatus.RETURNED.value
    db.commit.assert_not_called()
