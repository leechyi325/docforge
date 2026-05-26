FORMAT_OVERRIDE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"anyOf": [{"$ref": "#/$defs/paragraphStyle"}, {"type": "null"}]},
        "body": {"anyOf": [{"$ref": "#/$defs/paragraphStyle"}, {"type": "null"}]},
        "headings": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "heading_1": {"$ref": "#/$defs/paragraphStyle"},
                "heading_2": {"$ref": "#/$defs/paragraphStyle"},
                "heading_3": {"$ref": "#/$defs/paragraphStyle"},
            },
            "required": ["heading_1", "heading_2", "heading_3"],
        },
        "page": {
            "anyOf": [
                {"$ref": "#/$defs/pageSetup"},
                {"type": "null"},
            ]
        },
        "notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "body", "headings", "page", "notes"],
    "$defs": {
        "paragraphStyle": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "font": {"type": ["string", "null"]},
                "size": {"type": ["string", "null"]},
                "bold": {"type": ["boolean", "null"]},
                "align": {"enum": ["left", "center", "right", "justify", None]},
                "first_line_indent": {"type": ["string", "null"]},
                "line_spacing": {"type": ["string", "null"]},
                "space_before": {"type": ["string", "null"]},
                "space_after": {"type": ["string", "null"]},
            },
            "required": [
                "font",
                "size",
                "bold",
                "align",
                "first_line_indent",
                "line_spacing",
                "space_before",
                "space_after",
            ],
        },
        "pageSetup": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "paper": {"type": "string"},
                "margin_top": {"type": "string"},
                "margin_bottom": {"type": "string"},
                "margin_left": {"type": "string"},
                "margin_right": {"type": "string"},
            },
            "required": ["paper", "margin_top", "margin_bottom", "margin_left", "margin_right"],
        },
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
