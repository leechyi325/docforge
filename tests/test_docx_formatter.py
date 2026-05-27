from docx import Document

from engine.formatter.docx_formatter import apply_profile_formatting
from engine.models import ParagraphStyle, Profile, PageSetup
from engine.profiles.loader import load_profile


def test_apply_profile_formatting_sets_title_and_body(tmp_path):
    source = tmp_path / "source.docx"
    output = tmp_path / "formatted.docx"

    doc = Document()
    doc.add_paragraph("测试标题")
    doc.add_paragraph("这是正文段落。")
    doc.save(source)

    apply_profile_formatting(source, output, load_profile("general"))

    formatted = Document(output)
    assert formatted.paragraphs[0].alignment == 1
    assert formatted.paragraphs[0].runs[0].font.name == "宋体"
    assert formatted.paragraphs[1].runs[0].font.name == "仿宋_GB2312"


def test_heading_3_detection_and_formatting(tmp_path):
    source = tmp_path / "source.docx"
    output = tmp_path / "output.docx"
    doc = Document()
    doc.add_paragraph("标题")
    doc.add_paragraph("一、一级标题")
    doc.add_paragraph("（一）二级标题")
    doc.add_paragraph("1. 三级标题")
    doc.add_paragraph("正文内容")
    doc.save(source)

    profile = Profile(
        id="test",
        name="test",
        title=ParagraphStyle(font="宋体", size="二号", bold=True, align="center"),
        body=ParagraphStyle(font="仿宋_GB2312", size="三号", align="justify", first_line_indent="2em", line_spacing="29pt"),
        headings={
            "heading_1": ParagraphStyle(font="黑体", size="三号", bold=True, line_spacing="29pt"),
            "heading_2": ParagraphStyle(font="楷体_GB2312", size="三号", bold=True, line_spacing="29pt"),
            "heading_3": ParagraphStyle(font="仿宋_GB2312", size="三号", bold=True, line_spacing="29pt"),
        },
    )

    apply_profile_formatting(source, output, profile)

    result = Document(output)
    h3 = result.paragraphs[3]
    assert h3.runs[0].font.name == "仿宋_GB2312"
    assert h3.runs[0].font.bold is True


def test_date_and_department_field_formatting(tmp_path):
    source = tmp_path / "source.docx"
    output = tmp_path / "output.docx"
    doc = Document()
    doc.add_paragraph("文稿标题")
    doc.add_paragraph("2026年5月27日")
    doc.add_paragraph("某某部门")
    doc.add_paragraph("正文内容")
    doc.save(source)

    profile = Profile(
        id="test",
        name="test",
        title=ParagraphStyle(font="宋体", size="二号", bold=True, align="center"),
        body=ParagraphStyle(font="仿宋_GB2312", size="三号", align="justify"),
        date_field=ParagraphStyle(font="楷体_GB2312", size="三号", bold=True, align="center"),
        department_field=ParagraphStyle(font="楷体_GB2312", size="三号", bold=True, align="center"),
    )

    apply_profile_formatting(source, output, profile)

    result = Document(output)
    assert result.paragraphs[1].runs[0].font.name == "楷体_GB2312"
    assert result.paragraphs[1].runs[0].font.bold is True
    assert result.paragraphs[1].alignment == 1  # CENTER
    assert result.paragraphs[2].runs[0].font.name == "楷体_GB2312"
    assert result.paragraphs[2].runs[0].font.bold is True
    assert result.paragraphs[2].alignment == 1  # CENTER
