"""
Phase 4 addition — verifies matching.py's location component now goes
through embeddings.normalize_location (metadata normalization) instead of
a raw string-equality check. Exercises the scoring helper directly so it
doesn't need Postgres/pgvector (see conftest.py's note on why Report/Match
aren't covered by the sqlite suite).
"""
from app.services.matching import _location_score


def test_location_score_exact_match():
    assert _location_score("Library", "Library") == 100.0


def test_location_score_matches_via_alias_normalization():
    assert _location_score("Bldg 3 Cafeteria", "Building 3 Cafe") == 100.0


def test_location_score_case_and_punctuation_insensitive():
    assert _location_score("Main St.", "main st") == 100.0


def test_location_score_no_match():
    assert _location_score("Library", "Gym") == 0.0


def test_location_score_missing_value_scores_zero():
    assert _location_score(None, "Library") == 0.0
    assert _location_score("", "Library") == 0.0
