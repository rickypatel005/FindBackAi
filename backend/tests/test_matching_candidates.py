"""
Phase 5 — tests for the pgvector candidate-narrowing helpers added to
matching.py (SRS FR-07.2). These use a mocked `Session` rather than a real
Postgres connection (see conftest.py's note on why Report/Match aren't
covered by the sqlite suite) — the goal here is to verify the "degrade,
never crash" contract: no usable embedding, or any DB-level failure,
falls back to `None` (caller then does the full hard-filtered scan)
instead of propagating an exception.
"""
import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from app.models.report import Report, ReportType
from app.services import matching


class _FakeReport:
    """Duck-typed stand-in for a Report row — only the attributes
    `_vector_prefilter_candidates`/`get_candidates` actually read."""

    def __init__(self, *, image_embedding=None, text_embedding=None, report_type=ReportType.LOST):
        self.id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.type = report_type
        self.image_embedding = image_embedding
        self.text_embedding = text_embedding


# --- _has_usable_embedding ---

def test_has_usable_embedding_none_is_false():
    assert matching._has_usable_embedding(None) is False


def test_has_usable_embedding_zero_vector_is_false():
    assert matching._has_usable_embedding([0.0, 0.0, 0.0]) is False


def test_has_usable_embedding_real_vector_is_true():
    assert matching._has_usable_embedding([0.1, 0.0, 0.3]) is True


# --- _vector_prefilter_candidates ---

def test_prefilter_returns_none_without_any_embedding():
    db = MagicMock()
    report = _FakeReport()
    base_stmt = select(Report)

    result = matching._vector_prefilter_candidates(db, report, base_stmt)

    assert result is None
    db.execute.assert_not_called()


def test_prefilter_falls_back_gracefully_on_db_error():
    """Simulates the sqlite/no-pgvector case: cosine_distance ordering
    isn't supported, so the DB call raises. Must return None and roll
    back rather than bubble the exception up."""
    db = MagicMock()
    db.execute.side_effect = Exception("no such function: cosine_distance")
    report = _FakeReport(image_embedding=[0.1, 0.2, 0.3])
    base_stmt = select(Report)

    result = matching._vector_prefilter_candidates(db, report, base_stmt)

    assert result is None
    db.rollback.assert_called_once()


def test_prefilter_returns_narrowed_list_on_success():
    db = MagicMock()
    fake_rows = [_FakeReport(report_type=ReportType.FOUND) for _ in range(3)]
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = fake_rows
    db.execute.return_value.scalars.return_value = scalars_mock

    report = _FakeReport(image_embedding=[0.1, 0.2, 0.3])
    base_stmt = select(Report)

    result = matching._vector_prefilter_candidates(db, report, base_stmt)

    assert result == fake_rows


# --- get_candidates (public entrypoint) ---

def test_get_candidates_falls_back_to_full_scan_when_prefilter_fails(monkeypatch):
    monkeypatch.setattr(matching.settings, "ENABLE_VECTOR_PREFILTER", True)

    db = MagicMock()
    fallback_rows = [_FakeReport(report_type=ReportType.FOUND)]
    fallback_scalars = MagicMock()
    fallback_scalars.all.return_value = fallback_rows
    fallback_result = MagicMock()
    fallback_result.scalars.return_value = fallback_scalars

    # First call (prefilter attempt) raises; second call (fallback scan) succeeds.
    db.execute.side_effect = [Exception("no pgvector"), fallback_result]

    report = _FakeReport(image_embedding=[0.1, 0.2, 0.3])
    result = matching.get_candidates(db, report)

    assert result == fallback_rows
    assert db.execute.call_count == 2


def test_get_candidates_skips_prefilter_when_disabled(monkeypatch):
    monkeypatch.setattr(matching.settings, "ENABLE_VECTOR_PREFILTER", False)

    db = MagicMock()
    rows = [_FakeReport(report_type=ReportType.FOUND)]
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = rows
    db.execute.return_value.scalars.return_value = scalars_mock

    report = _FakeReport(image_embedding=[0.1, 0.2, 0.3])
    result = matching.get_candidates(db, report)

    assert result == rows
    db.execute.assert_called_once()  # no prefilter attempt at all
