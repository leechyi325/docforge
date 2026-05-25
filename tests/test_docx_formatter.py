from docx import Document

from engine.formatter.docx_formatter import apply_profile_formatting
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
    assert formatted.paragraphs[0].runs[0].font.name == "方正小标宋"
    assert formatted.paragraphs[1].runs[0].font.name == "仿宋"
