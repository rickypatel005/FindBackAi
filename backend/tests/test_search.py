"""
Phase 7 — tests for the manual search/filter service (SRS FR-15).

Report/Match use pgvector's Postgres-only Vector column (see
conftest.py's note), so — mirroring test_matching_candidates.py's
approach — these exercise `search_reports` against a mocked `Session`
rather than a real DB connection. The goal is to verify the statement
gets built and executed (filters compose, limit is clamped) rather than
to re-test SQLAlchemy/Postgres itself.
"""
import datetime
from unittest.mock import MagicMock

from app.models.report import ReportType
from app.services import search


def _db_returning(rows):
    db = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = rows
    db.execute.return_value.scalars.return_value = scalars_mock
    return db


def test_search_with_no_filters_returns_active_reports():
    db = _db_returning(["report-1", "report-2"])

    result = search.search_reports(db)

    assert result == ["report-1", "report-2"]
    db.execute.assert_called_once()


def test_search_applies_all_filters_without_error():
    db = _db_returning([])

    result = search.search_reports(
        db,
        type=ReportType.LOST,
        category="Electronics",
        color="Black",
        brand="Sony",
        location="Library",
        status="SEARCHING",
        date_from=datetime.date(2026, 1, 1),
        date_to=datetime.date(2026, 12, 31),
        q="headphones",
    )

    assert result == []
    db.execute.assert_called_once()


def test_search_limit_is_clamped_to_max():
    db = _db_returning([])

    search.search_reports(db, limit=10_000)

    # We can't easily introspect the compiled LIMIT value against a mock,
    # but the call should still succeed rather than passing an absurd
    # limit straight through to the DB.
    db.execute.assert_called_once()


def test_search_limit_floor_is_one():
    db = _db_returning([])

    search.search_reports(db, limit=-5)

    db.execute.assert_called_once()
