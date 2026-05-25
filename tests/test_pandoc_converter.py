from pathlib import Path

import pytest

from engine.converters.pandoc import PandocNotFoundError, convert_markdown_to_docx


def test_convert_markdown_to_docx_reports_missing_pandoc(monkeypatch, tmp_path):
    monkeypatch.setattr("engine.converters.pandoc.shutil.which", lambda name: None)

    with pytest.raises(PandocNotFoundError):
        convert_markdown_to_docx(Path("tests/fixtures/general.md"), tmp_path / "out.docx")
