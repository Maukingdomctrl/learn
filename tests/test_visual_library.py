from learn.teaching_engine.visual_library import VISUAL_LIBRARY, list_visuals
from learn.teaching_web import visual_library


def test_visual_library_has_topics_sources_authors_licenses_and_image_urls():
    assert len(VISUAL_LIBRARY) >= 8
    assert len({visual.id for visual in VISUAL_LIBRARY}) == len(VISUAL_LIBRARY)
    for visual in VISUAL_LIBRARY:
        assert visual.topic
        assert visual.source_url.startswith("https://commons.wikimedia.org/wiki/File:")
        assert visual.image_url.startswith("https://commons.wikimedia.org/wiki/Special:FilePath/")
        assert visual.author
        assert visual.license_name
        assert visual.license_url.startswith("https://")


def test_visual_library_filters_indian_and_uk_comparison_topics():
    india = list_visuals("Indian Studies")
    uk = list_visuals("UK comparison")

    assert india
    assert uk
    assert all(visual.region == "Indian Studies" for visual in india)
    assert all(visual.region == "UK comparison" for visual in uk)
    assert len(list_visuals("all")) == len(VISUAL_LIBRARY)


def test_library_page_renders_source_and_license_attribution():
    page = visual_library().body.decode("utf-8")

    assert "Lion Capital of Ashoka" in page
    assert "Gandhi during the Salt March" in page
    assert "Watt&#39;s double steam engine" in page or "Watt's double steam engine" in page
    assert "CC BY-SA 4.0" in page
    assert "does not copy or store them" in page


def test_library_page_filters_to_one_region():
    india = visual_library("Indian Studies").body.decode("utf-8")
    uk = visual_library("UK comparison").body.decode("utf-8")

    assert "Lion Capital of Ashoka" in india
    assert "Watt&#39;s double steam engine" not in india
    assert "Watt&#39;s double steam engine" in uk or "Watt's double steam engine" in uk
    assert "Lion Capital of Ashoka" not in uk
