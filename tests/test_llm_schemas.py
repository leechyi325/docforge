import json

from engine.llm.base import parse_format_override_json
from engine.llm.schemas import FORMAT_OVERRIDE_SCHEMA, ISSUE_LIST_SCHEMA


def test_format_override_schema_requires_object():
    assert FORMAT_OVERRIDE_SCHEMA["type"] == "object"
    assert "properties" in FORMAT_OVERRIDE_SCHEMA
    assert "body" in FORMAT_OVERRIDE_SCHEMA["properties"]


def test_format_override_schema_is_strict_output_compatible():
    assert FORMAT_OVERRIDE_SCHEMA["required"] == ["title", "body", "headings", "page", "notes"]
    paragraph_style = FORMAT_OVERRIDE_SCHEMA["$defs"]["paragraphStyle"]
    assert set(paragraph_style["required"]) == set(paragraph_style["properties"])
    assert paragraph_style["properties"]["font"]["type"] == ["string", "null"]
    assert None in paragraph_style["properties"]["align"]["enum"]
    headings = FORMAT_OVERRIDE_SCHEMA["properties"]["headings"]
    assert headings["additionalProperties"] is False
    assert headings["required"] == ["heading_1", "heading_2", "heading_3"]


def test_strict_format_override_payload_validates_to_model():
    empty_style = {
        "font": None,
        "size": None,
        "bold": None,
        "align": None,
        "first_line_indent": None,
        "line_spacing": None,
        "space_before": None,
        "space_after": None,
    }
    raw = json.dumps(
        {
            "title": empty_style,
            "body": {**empty_style, "font": "仿宋", "size": "三号"},
            "headings": {
                "heading_1": empty_style,
                "heading_2": empty_style,
                "heading_3": empty_style,
            },
            "page": None,
            "notes": [],
        },
        ensure_ascii=False,
    )

    override = parse_format_override_json(raw)

    assert override.body.font == "仿宋"
    assert override.body.size == "三号"
    assert override.page is None


def test_issue_list_schema_contains_fix_action():
    issue = ISSUE_LIST_SCHEMA["properties"]["issues"]["items"]
    assert "fix_action" in issue["properties"]
