from engine.models import (
    FixAction,
    Issue,
    Location,
    PageNumbering,
    PageSetup,
    ParagraphStyle,
    Profile,
)


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


def test_page_numbering_model():
    pn = PageNumbering(
        font="宋体",
        size="四号",
        format="－ {page} －",
        odd_align="right",
        even_align="left",
    )
    assert pn.font == "宋体"
    assert pn.format == "－ {page} －"
    assert pn.odd_align == "right"


def test_page_setup_with_page_number():
    ps = PageSetup(
        paper="A4",
        margin_top="3.5cm",
        margin_bottom="3.5cm",
        margin_left="2.8cm",
        margin_right="2.8cm",
        page_number=PageNumbering(font="宋体", size="四号"),
    )
    assert ps.page_number is not None
    assert ps.page_number.font == "宋体"


def test_profile_with_extended_fields():
    profile = Profile(
        id="default",
        name="默认文稿模板",
        title={"font": "宋体", "size": "二号", "bold": True, "align": "center", "line_spacing": "29pt"},
        body={"font": "仿宋_GB2312", "size": "三号", "align": "justify", "line_spacing": "29pt", "first_line_indent": "2em"},
        date_field={"font": "楷体_GB2312", "size": "三号", "bold": True, "align": "center", "line_spacing": "29pt"},
        department_field={"font": "楷体_GB2312", "size": "三号", "bold": True, "align": "center", "line_spacing": "29pt"},
        content_bold={"font": "楷体_GB2312", "size": "三号", "bold": True},
    )
    assert profile.date_field.font == "楷体_GB2312"
    assert profile.department_field.font == "楷体_GB2312"
    assert profile.content_bold.font == "楷体_GB2312"
