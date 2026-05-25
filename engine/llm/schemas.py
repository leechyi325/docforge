FORMAT_OVERRIDE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"$ref": "#/$defs/paragraphStyle"},
        "body": {"$ref": "#/$defs/paragraphStyle"},
        "headings": {
            "type": "object",
            "additionalProperties": {"$ref": "#/$defs/paragraphStyle"},
        },
        "page": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "paper": {"type": "string"},
                "margin_top": {"type": "string"},
                "margin_bottom": {"type": "string"},
                "margin_left": {"type": "string"},
                "margin_right": {"type": "string"},
            },
        },
        "notes": {"type": "array", "items": {"type": "string"}},
    },
    "$defs": {
        "paragraphStyle": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "font": {"type": "string"},
                "size": {"type": "string"},
                "bold": {"type": "boolean"},
                "align": {"enum": ["left", "center", "right", "justify"]},
                "first_line_indent": {"type": "string"},
                "line_spacing": {"type": "string"},
                "space_before": {"type": "string"},
                "space_after": {"type": "string"},
            },
        }
    },
}

DOCUMENT_STRUCTURE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "document_type": {"type": "string"},
        "title": {"type": ["string", "null"]},
        "headings": {"type": "array", "items": {"type": "string"}},
        "required_fields_present": {
            "type": "object",
            "additionalProperties": {"type": "boolean"},
        },
    },
    "required": ["document_type", "title", "headings", "required_fields_present"],
}

ISSUE_LIST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "severity": {"enum": ["info", "warning", "error"]},
                    "message": {"type": "string"},
                    "location": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "type": {"enum": ["document", "paragraph", "section"]},
                            "index": {"type": ["integer", "null"]},
                            "key": {"type": ["string", "null"]},
                        },
                        "required": ["type", "index", "key"],
                    },
                    "fix_action": {
                        "type": ["object", "null"],
                        "additionalProperties": False,
                        "properties": {
                            "type": {
                                "enum": [
                                    "set_paragraph_format",
                                    "apply_heading_style",
                                    "set_page_setup",
                                    "set_section_format",
                                ]
                            },
                            "target": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "type": {"enum": ["document", "paragraph", "section"]},
                                    "index": {"type": ["integer", "null"]},
                                    "key": {"type": ["string", "null"]},
                                },
                                "required": ["type", "index", "key"],
                            },
                            "properties": {"type": "object"},
                        },
                        "required": ["type", "target", "properties"],
                    },
                },
                "required": ["id", "severity", "message", "location", "fix_action"],
            },
        }
    },
    "required": ["issues"],
}
