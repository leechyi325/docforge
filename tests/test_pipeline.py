import shutil

import pytest
from docx import Document

from engine.pipeline import UnsupportedInputError, format_document
from engine.profiles.loader import load_profile


def test_format_document_accepts_docx_input(tmp_path):
    source = tmp_path / "source.docx"
    output = tmp_path / "formatted.docx"
    doc = Document()
    doc.add_paragraph("测试标题")
    doc.add_paragraph("正文段落")
    doc.save(source)

    result = format_document(source, output, load_profile("general"))

    assert result.output_path == output
    assert output.exists()
    formatted = Document(output)
    assert formatted.paragraphs[0].runs[0].font.name == "方正小标宋"
    assert formatted.paragraphs[1].runs[0].font.name == "仿宋"
    assert isinstance(result.issues, list)


def test_format_document_rejects_doc_input(tmp_path):
    source = tmp_path / "legacy.doc"
    output = tmp_path / "formatted.docx"
    source.write_bytes(b"not a real doc file")

    with pytest.raises(UnsupportedInputError, match="Markdown and .docx"):
        format_document(source, output, load_profile("general"))


def test_format_document_requires_docx_output(tmp_path):
    source = tmp_path / "source.docx"
    output = tmp_path / "formatted.pdf"
    doc = Document()
    doc.add_paragraph("测试标题")
    doc.save(source)

    with pytest.raises(ValueError, match="Output path must end with .docx"):
        format_document(source, output, load_profile("general"))


def test_format_document_reports_missing_input(tmp_path):
    source = tmp_path / "missing.docx"
    output = tmp_path / "formatted.docx"

    with pytest.raises(FileNotFoundError, match="Input file does not exist"):
        format_document(source, output, load_profile("general"))


def test_format_document_requires_new_output_path(tmp_path):
    source = tmp_path / "source.docx"
    doc = Document()
    doc.add_paragraph("测试标题")
    doc.save(source)

    with pytest.raises(ValueError, match="Output path must be different"):
        format_document(source, source, load_profile("general"))


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc is required for markdown conversion")
def test_format_document_accepts_markdown_input(tmp_path):
    source = tmp_path / "source.md"
    output = tmp_path / "formatted.docx"
    source.write_text("# 测试标题\n\n正文段落\n", encoding="utf-8")

    result = format_document(source, output, load_profile("general"))

    assert result.output_path == output
    assert output.exists()
    assert Document(output).paragraphs[0].text.strip() == "测试标题"
