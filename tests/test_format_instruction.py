from engine.llm.client import parse_format_instruction_locally


def test_local_format_instruction_parser_handles_common_request():
    override = parse_format_instruction_locally(
        "标题用方正小标宋二号居中，正文仿宋三号，行距固定28磅，一级标题黑体三号。"
    )

    assert override.title.font == "方正小标宋"
    assert override.title.size == "二号"
    assert override.title.align == "center"
    assert override.body.font == "仿宋"
    assert override.body.size == "三号"
    assert override.body.line_spacing == "28pt"
    assert override.headings["heading_1"].font == "黑体"
