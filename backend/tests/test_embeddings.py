"""
Phase 4 — text embeddings service tests. Deliberately avoid requiring
sentence-transformers to be installed: `_try_load_model()` degrades to the
documented fallback path (zero-vector embedding) whenever the package or
its weights aren't available, so these tests exercise that fallback path
directly rather than mocking the model — same approach as test_vision.py.
"""
from app.services import embeddings


def test_build_report_text_joins_present_fields():
    text = embeddings.build_report_text("Blue backpack", "Left on the 4th floor.", "Has a broken zipper")
    assert text == "Blue backpack. Left on the 4th floor.. Has a broken zipper"


def test_build_report_text_skips_missing_features():
    text = embeddings.build_report_text("Blue backpack", "Left on the 4th floor.", None)
    assert "None" not in text
    assert text == "Blue backpack. Left on the 4th floor."


def test_embed_text_returns_correct_dimension():
    embedding = embeddings.embed_text("A navy blue backpack with a broken zipper")
    assert len(embedding) == embeddings.TEXT_EMBEDDING_DIM
    assert all(isinstance(v, float) for v in embedding)


def test_embed_text_empty_string_returns_zero_vector():
    embedding = embeddings.embed_text("")
    assert embedding == [0.0] * embeddings.TEXT_EMBEDDING_DIM


def test_embed_report_text_matches_embed_text_of_joined_string():
    a = embeddings.embed_report_text("Blue backpack", "Left on campus", "torn strap")
    b = embeddings.embed_text("Blue backpack. Left on campus. torn strap")
    assert a == b


def test_normalize_location_expands_abbreviations_and_lowercases():
    assert embeddings.normalize_location("Bldg 3, Rm 201") == "building 3 rm 201"


def test_normalize_location_handles_multiword_alias():
    assert embeddings.normalize_location("Main Car Park") == "main parking lot"


def test_normalize_location_empty_input():
    assert embeddings.normalize_location(None) == ""
    assert embeddings.normalize_location("   ") == ""


def test_normalize_location_matches_across_phrasing():
    a = embeddings.normalize_location("Bldg 3 Cafeteria")
    b = embeddings.normalize_location("Building 3 Cafe")
    assert a == b
