from engine.llm.schemas import FORMAT_OVERRIDE_SCHEMA, ISSUE_LIST_SCHEMA


def test_format_override_schema_requires_object():
    assert FORMAT_OVERRIDE_SCHEMA["type"] == "object"
    assert "properties" in FORMAT_OVERRIDE_SCHEMA
    assert "body" in FORMAT_OVERRIDE_SCHEMA["properties"]


def test_issue_list_schema_contains_fix_action():
    issue = ISSUE_LIST_SCHEMA["properties"]["issues"]["items"]
    assert "fix_action" in issue["properties"]
