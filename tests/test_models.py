from engine.models import FixAction, Issue, Location, ParagraphStyle


def test_issue_requires_fix_action_shape():
    issue = Issue(
        id="issue_001",
        severity="warning",
        message="正文行距不符合要求",
        location=Location(type="paragraph", index=3),
        fix_action=FixAction(
            type="set_paragraph_format",
            target=Location(type="paragraph", index=3),
            properties=ParagraphStyle(font="仿宋", size="三号", line_spacing="28pt"),
        ),
    )

    assert issue.fix_action.properties.font == "仿宋"
    assert issue.location.index == 3
