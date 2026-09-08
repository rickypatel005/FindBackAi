from app.services import quality


def test_short_description_is_flagged_weak():
    result = quality.check_description("Blue bag")
    assert result["is_weak"] is True
    assert any("short" in s.lower() for s in result["suggestions"])


def test_description_with_distinguishing_detail_and_length_is_not_flagged_for_that_reason():
    text = "A navy blue backpack with a small tear near the zipper and a keychain attached."
    result = quality.check_description(text)
    assert not any("unique marks" in s.lower() for s in result["suggestions"])


def test_description_without_distinguishing_keywords_is_flagged():
    text = "This is a fairly long description of a backpack that has no unique details at all really."
    result = quality.check_description(text)
    assert any("unique marks" in s.lower() for s in result["suggestions"])


def test_check_title_flags_vague_titles():
    assert quality.check_title("Item") != []
    assert quality.check_title("") != []
    assert quality.check_title("Blue Jansport backpack") == []


def test_check_report_quality_combines_title_and_description():
    result = quality.check_report_quality("item", "short")
    assert result["is_weak"] is True
    assert len(result["suggestions"]) >= 2


def test_check_report_quality_good_input_is_not_weak():
    result = quality.check_report_quality(
        "Navy Jansport backpack",
        "A navy blue Jansport backpack with a small tear near the front zipper and a red keychain.",
    )
    assert result["is_weak"] is False
    assert result["suggestions"] == []
