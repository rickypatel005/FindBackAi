"""
Phase 7 — tests for duplicate detection (SRS FR-16). Same mocked-Session
approach as test_matching_candidates.py / test_search.py, since Report
rows carry a Postgres-only pgvector column.
"""
import uuid
from unittest.mock import MagicMock

from app.models.report import ReportType
from app.services import duplicates


class _FakeReport:
    def __init__(self, *, image_embedding=None, text_embedding=None, user_id=None):
        self.id = uuid.uuid4()
        self.user_id = user_id or uuid.uuid4()
        self.image_embedding = image_embedding
        self.text_embedding = text_embedding


def _db_returning_per_type(lost_rows, found_rows):
    """Matches the two sequential `select(Report).where(type == t)` calls
    find_duplicate_pairs makes — one for LOST, one for FOUND."""
    db = MagicMock()
    responses = []
    for rows in (lost_rows, found_rows):
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = rows
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        responses.append(result_mock)
    db.execute.side_effect = responses
    return db


def test_pair_similarity_zero_without_embeddings():
    a, b = _FakeReport(), _FakeReport()
    assert duplicates._pair_similarity(a, b) == 0.0


def test_pair_similarity_high_for_identical_embeddings():
    vec = [0.1, 0.2, 0.3, 0.4]
    a = _FakeReport(image_embedding=vec, text_embedding=vec)
    b = _FakeReport(image_embedding=vec, text_embedding=vec)
    assert duplicates._pair_similarity(a, b) > 99.0


def test_find_duplicate_pairs_flags_high_similarity_same_type():
    vec = [0.1, 0.2, 0.3, 0.4]
    a = _FakeReport(image_embedding=vec, text_embedding=vec)
    b = _FakeReport(image_embedding=vec, text_embedding=vec)
    db = _db_returning_per_type(lost_rows=[a, b], found_rows=[])

    result = duplicates.find_duplicate_pairs(db)

    assert len(result) == 1
    assert result[0]["type"] == ReportType.LOST.value
    assert result[0]["similarity"] >= duplicates.settings.DUPLICATE_SIMILARITY_THRESHOLD


def test_find_duplicate_pairs_ignores_dissimilar_reports():
    a = _FakeReport(image_embedding=[1.0, 0.0], text_embedding=[1.0, 0.0])
    b = _FakeReport(image_embedding=[0.0, 1.0], text_embedding=[0.0, 1.0])
    db = _db_returning_per_type(lost_rows=[a, b], found_rows=[])

    result = duplicates.find_duplicate_pairs(db)

    assert result == []


def test_find_duplicate_pairs_respects_report_type_filter():
    vec = [0.1, 0.2, 0.3, 0.4]
    a = _FakeReport(image_embedding=vec, text_embedding=vec)
    b = _FakeReport(image_embedding=vec, text_embedding=vec)

    db = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [a, b]
    db.execute.return_value.scalars.return_value = scalars_mock

    result = duplicates.find_duplicate_pairs(db, report_type=ReportType.FOUND)

    assert len(result) == 1
    assert result[0]["type"] == ReportType.FOUND.value
    db.execute.assert_called_once()  # only one type scanned, not both
