import pytest

from engine.structure.models import (
    ParagraphCandidate,
    RecognizedParagraph,
    RecognizedStructure,
    RecognizedTable,
    StructureInput,
    TableCandidate,
)
from engine.structure.validate import StructureValidationError, summarize_structure, validate_recognized_structure


def _input() -> StructureInput:
    return StructureInput(
        source_path="source.docx",
        paragraphs=[
            ParagraphCandidate(index=0, text="标题", char_count=2),
            ParagraphCandidate(index=1, text="一、总体要求", char_count=6),
            ParagraphCandidate(index=2, text="正文", char_count=2),
        ],
        tables=[TableCandidate(index=0, rows=2, columns=2, sample_cells=[["序号", "事项"]])],
    )


def test_validate_recognized_structure_accepts_valid_indexes_and_confidence():
    recognized = RecognizedStructure(
        paragraphs=[
            RecognizedParagraph(index=0, role="title", confidence=0.9, reason="centered first paragraph"),
            RecognizedParagraph(index=1, role="heading_1", confidence=0.8, reason="Chinese heading marker"),
            RecognizedParagraph(index=2, role="body", confidence=0.5, reason="body text"),
        ],
        tables=[RecognizedTable(index=0, role="data_table", confidence=0.8, reason="regular data table")],
    )

    result = validate_recognized_structure(recognized, _input())

    assert result is recognized


def test_validate_recognized_structure_rejects_unknown_paragraph_index():
    recognized = RecognizedStructure(
        paragraphs=[RecognizedParagraph(index=9, role="title", confidence=0.9, reason="bad index")],
        tables=[],
    )

    with pytest.raises(StructureValidationError, match="paragraph index 9"):
        validate_recognized_structure(recognized, _input())


def test_validate_recognized_structure_rejects_duplicate_paragraph_index():
    recognized = RecognizedStructure(
        paragraphs=[
            RecognizedParagraph(index=0, role="title", confidence=0.9, reason="first role"),
            RecognizedParagraph(index=0, role="body", confidence=0.9, reason="second role"),
        ],
        tables=[],
    )

    with pytest.raises(StructureValidationError, match="duplicate paragraph index 0"):
        validate_recognized_structure(recognized, _input())


def test_validate_recognized_structure_rejects_low_confidence_key_role():
    recognized = RecognizedStructure(
        paragraphs=[RecognizedParagraph(index=0, role="title", confidence=0.4, reason="uncertain")],
        tables=[],
    )

    with pytest.raises(StructureValidationError, match="low confidence"):
        validate_recognized_structure(recognized, _input())


def test_validate_recognized_structure_rejects_unknown_table_index():
    recognized = RecognizedStructure(
        paragraphs=[],
        tables=[RecognizedTable(index=3, role="data_table", confidence=0.8, reason="bad table")],
    )

    with pytest.raises(StructureValidationError, match="table index 3"):
        validate_recognized_structure(recognized, _input())


def test_validate_recognized_structure_rejects_duplicate_table_index():
    recognized = RecognizedStructure(
        paragraphs=[],
        tables=[
            RecognizedTable(index=0, role="data_table", confidence=0.8, reason="first role"),
            RecognizedTable(index=0, role="schedule_table", confidence=0.8, reason="second role"),
        ],
    )

    with pytest.raises(StructureValidationError, match="duplicate table index 0"):
        validate_recognized_structure(recognized, _input())


def test_summarize_structure_counts_roles_and_tables():
    recognized = RecognizedStructure(
        paragraphs=[
            RecognizedParagraph(index=0, role="title", confidence=0.9, reason="title"),
            RecognizedParagraph(index=1, role="heading_1", confidence=0.8, reason="h1"),
            RecognizedParagraph(index=2, role="unknown", confidence=0.3, reason="unknown"),
        ],
        tables=[RecognizedTable(index=0, role="data_table", confidence=0.8, reason="table")],
    )

    summary = summarize_structure(recognized)

    assert summary.counts["title"] == 1
    assert summary.counts["heading_1"] == 1
    assert summary.counts["unknown"] == 1
    assert summary.counts["table"] == 1
