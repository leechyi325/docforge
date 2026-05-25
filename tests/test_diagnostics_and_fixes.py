from docx import Document

from engine.diagnostics.diagnose import diagnose_docx
from engine.fixer.apply_fixes import apply_fixes
from engine.profiles.loader import load_profile


def test_diagnose_and_fix_body_font(tmp_path):
    source = tmp_path / "bad.docx"
    fixed = tmp_path / "fixed.docx"

    doc = Document()
    doc.add_paragraph("测试标题")
    doc.add_paragraph("正文段落")
    doc.save(source)

    profile = load_profile("general")
    issues = diagnose_docx(source, profile)

    assert any(issue.fix_action for issue in issues)

    apply_fixes(source, fixed, issues)
    remaining = diagnose_docx(fixed, profile)

    assert len([issue for issue in remaining if issue.severity == "error"]) == 0
