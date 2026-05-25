import json

from docx import Document

from engine.cli import main


def test_cli_diagnose_outputs_json(tmp_path, capsys):
    input_docx = tmp_path / "input.docx"
    doc = Document()
    doc.add_paragraph("标题")
    doc.add_paragraph("正文")
    doc.save(input_docx)

    exit_code = main(["diagnose", "--input", str(input_docx), "--profile", "general"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert "issues" in payload
