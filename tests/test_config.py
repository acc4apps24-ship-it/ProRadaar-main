from pathlib import Path

from proradaar.config import load_sources


def test_load_sources_reads_grouped_yaml(tmp_path: Path):
    config_path = tmp_path / "sources.yaml"
    config_path.write_text(
        """
sources:
  - name: Lenny's Newsletter
    url: https://www.lennysnewsletter.com/feed
    group: influencers
    priority: 10
    tags: [growth, product]
  - name: Notion Releases
    url: https://www.notion.com/releases/rss.xml
    group: company_changelogs
""",
        encoding="utf-8",
    )

    sources = load_sources(config_path)

    assert len(sources) == 2
    assert sources[0].name == "Lenny's Newsletter"
    assert sources[0].group == "influencers"
    assert sources[0].priority == 10
    assert sources[0].tags == ["growth", "product"]
    assert sources[1].priority == 0
    assert sources[1].tags == []


def test_load_sources_rejects_missing_required_fields(tmp_path: Path):
    config_path = tmp_path / "sources.yaml"
    config_path.write_text(
        """
sources:
  - name: Broken Source
    group: influencers
""",
        encoding="utf-8",
    )

    try:
        load_sources(config_path)
    except ValueError as exc:
        assert "url" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing url")


def test_load_sources_rejects_invalid_required_field_type(tmp_path: Path):
    config_path = tmp_path / "sources.yaml"
    config_path.write_text(
        """
sources:
  - name: 123
    url: https://example.com/feed
    group: influencers
""",
        encoding="utf-8",
    )

    try:
        load_sources(config_path)
    except ValueError as exc:
        assert "name" in str(exc)
        assert "non-empty string" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid name")


def test_load_sources_rejects_bool_priority(tmp_path: Path):
    config_path = tmp_path / "sources.yaml"
    config_path.write_text(
        """
sources:
  - name: Broken Source
    url: https://example.com/feed
    group: influencers
    priority: true
""",
        encoding="utf-8",
    )

    try:
        load_sources(config_path)
    except ValueError as exc:
        assert "priority must be an integer" in str(exc)
    else:
        raise AssertionError("Expected ValueError for bool priority")


def test_load_sources_rejects_string_priority(tmp_path: Path):
    config_path = tmp_path / "sources.yaml"
    config_path.write_text(
        """
sources:
  - name: Broken Source
    url: https://example.com/feed
    group: influencers
    priority: "10"
""",
        encoding="utf-8",
    )

    try:
        load_sources(config_path)
    except ValueError as exc:
        assert "priority must be an integer" in str(exc)
    else:
        raise AssertionError("Expected ValueError for string priority")
