from __future__ import annotations

from collections import Counter

from engine.structure.models import RecognizedStructure, StructureInput, StructureSummary

_KEY_PARAGRAPH_ROLES = {
    "title",
    "date",
    "department",
    "heading_1",
    "heading_2",
    "heading_3",
    "table_caption",
}
_CONFIDENCE_THRESHOLD = 0.6


class StructureValidationError(ValueError):
    pass


def validate_recognized_structure(
    recognized: RecognizedStructure,
    structure_input: StructureInput,
) -> RecognizedStructure:
    paragraph_indexes = {paragraph.index for paragraph in structure_input.paragraphs}
    table_indexes = {table.index for table in structure_input.tables}

    seen_paragraph_indexes: set[int] = set()
    for paragraph in recognized.paragraphs:
        if paragraph.index in seen_paragraph_indexes:
            raise StructureValidationError(f"duplicate paragraph index {paragraph.index}")
        seen_paragraph_indexes.add(paragraph.index)
        if paragraph.index not in paragraph_indexes:
            raise StructureValidationError(f"unknown paragraph index {paragraph.index}")
        if paragraph.role in _KEY_PARAGRAPH_ROLES and paragraph.confidence < _CONFIDENCE_THRESHOLD:
            raise StructureValidationError(
                f"low confidence for paragraph index {paragraph.index} role {paragraph.role}"
            )

    seen_table_indexes: set[int] = set()
    for table in recognized.tables:
        if table.index in seen_table_indexes:
            raise StructureValidationError(f"duplicate table index {table.index}")
        seen_table_indexes.add(table.index)
        if table.index not in table_indexes:
            raise StructureValidationError(f"unknown table index {table.index}")
        if table.role != "unknown" and table.confidence < _CONFIDENCE_THRESHOLD:
            raise StructureValidationError(f"low confidence for table index {table.index} role {table.role}")

    return recognized


def summarize_structure(recognized: RecognizedStructure) -> StructureSummary:
    counts = Counter(str(paragraph.role) for paragraph in recognized.paragraphs)
    if recognized.tables:
        counts["table"] = len(recognized.tables)
    return StructureSummary(counts=dict(counts))
