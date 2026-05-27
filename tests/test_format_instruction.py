from engine.llm.client import create_llm_client, parse_format_instruction_locally
from engine.llm.settings import LlmSettings


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


def test_local_parser_is_available_through_client_factory():
    client = create_llm_client(LlmSettings(provider="local"))

    override = client.parse_format_instruction("正文仿宋三号，行距固定28磅")

    assert override.body.font == "仿宋"
    assert override.body.line_spacing == "28pt"


def test_local_parser_handles_heading_2():
    override = parse_format_instruction_locally(
        "标题宋体二号居中，正文仿宋三号，行距29磅，二级标题楷体三号"
    )
    assert override.headings["heading_2"].font == "楷体"


def test_local_parser_handles_heading_3():
    override = parse_format_instruction_locally(
        "标题宋体二号居中，正文仿宋三号，行距29磅，一级标题黑体三号，二级标题楷体三号，三级标题仿宋三号加粗"
    )
    assert override.headings["heading_1"].font == "黑体"
    assert override.headings["heading_2"].font == "楷体"
    assert override.headings["heading_3"].font == "仿宋"
