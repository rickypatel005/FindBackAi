"""
Phase 6 — tests for the rising-edge notification-qualification check used
by find_and_persist_matches (SRS FR-12.1) and for the upsert-by-pair
behavior that replaces the pre-Phase-6 "insert a fresh row every call"
logic (see migrations/004_match_constraints.sql). Uses mocked
Session/Report/Match stand-ins rather than a real Postgres connection,
same pattern as test_matching_candidates.py.
"""
import uuid
from unittest.mock import MagicMock

from app.models.report import ReportType
from app.services import matching


class _FakeReport:
    def __init__(self, *, report_type=ReportType.LOST):
        self.id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.type = report_type
        self.image_embedding = None
        self.text_embedding = None


class _FakeMatch:
    """Duck-typed stand-in for a persisted Match row."""

    def __init__(self, final_score: float):
        self.id = uuid.uuid4()
        self.final_score = final_score
        self.explanation = []
        self.updated_at = None


# --- _should_notify (pure rising-edge logic) ---

def test_new_pair_crossing_threshold_notifies():
    assert matching._should_notify(previous_final_score=None, new_final_score=75.0) is True


def test_new_pair_below_threshold_does_not_notify():
    assert matching._should_notify(previous_final_score=None, new_final_score=40.0) is False


def test_pair_already_qualified_does_not_renotify():
    assert matching._should_notify(previous_final_score=88.0, new_final_score=91.0) is False


def test_pair_dropping_then_recrossing_notifies_again():
    assert matching._should_notify(previous_final_score=40.0, new_final_score=75.0) is True


def test_pair_dropping_below_threshold_does_not_notify():
    assert matching._should_notify(previous_final_score=90.0, new_final_score=50.0) is False


def test_score_exactly_at_threshold_counts_as_qualified():
    threshold = matching.settings.MATCH_NOTIFICATION_THRESHOLD
    assert matching._should_notify(previous_final_score=None, new_final_score=threshold) is True


# --- find_and_persist_matches (upsert contract) ---

def _fixed_scores(final_score: float) -> dict:
    return {
        "image_score": 90.0,
        "text_score": 90.0,
        "category_score": 100.0,
        "color_score": 100.0,
        "brand_score": 0.0,
        "location_score": 100.0,
        "time_score": 100.0,
        "other_score": 0.0,
        "final_score": final_score,
    }


def test_find_and_persist_matches_updates_existing_pair_in_place(monkeypatch):
    """A pair that already has a Match row must be updated, never
    duplicated — the pre-Phase-6 bug this fixes."""
    lost = _FakeReport(report_type=ReportType.LOST)
    found_candidate = _FakeReport(report_type=ReportType.FOUND)
    existing_match = _FakeMatch(final_score=40.0)  # was below threshold before

    monkeypatch.setattr(matching, "get_candidates", lambda db, report, category_filter=None: [found_candidate])
    monkeypatch.setattr(matching, "_find_existing_match", lambda db, lost_id, found_id: existing_match)
    monkeypatch.setattr(matching, "score_pair", lambda l, f: _fixed_scores(91.0))

    db = MagicMock()
    results = matching.find_and_persist_matches(db, lost)

    db.add.assert_not_called()  # updated in place, no new row inserted
    assert existing_match.final_score == 91.0
    assert existing_match.just_qualified is True  # crossed the threshold this run
    assert results == [existing_match]


def test_find_and_persist_matches_does_not_renotify_already_qualified_pair(monkeypatch):
    lost = _FakeReport(report_type=ReportType.LOST)
    found_candidate = _FakeReport(report_type=ReportType.FOUND)
    existing_match = _FakeMatch(final_score=85.0)  # already qualified previously

    monkeypatch.setattr(matching, "get_candidates", lambda db, report, category_filter=None: [found_candidate])
    monkeypatch.setattr(matching, "_find_existing_match", lambda db, lost_id, found_id: existing_match)
    monkeypatch.setattr(matching, "score_pair", lambda l, f: _fixed_scores(88.0))

    db = MagicMock()
    matching.find_and_persist_matches(db, lost)

    assert existing_match.just_qualified is False


def test_find_and_persist_matches_creates_new_row_when_no_existing_pair(monkeypatch):
    lost = _FakeReport(report_type=ReportType.LOST)
    found_candidate = _FakeReport(report_type=ReportType.FOUND)

    monkeypatch.setattr(matching, "get_candidates", lambda db, report, category_filter=None: [found_candidate])
    monkeypatch.setattr(matching, "_find_existing_match", lambda db, lost_id, found_id: None)
    monkeypatch.setattr(matching, "score_pair", lambda l, f: _fixed_scores(30.0))

    db = MagicMock()
    results = matching.find_and_persist_matches(db, lost)

    db.add.assert_called_once()
    assert results[0].just_qualified is False
