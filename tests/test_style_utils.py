from engine.models import ParagraphStyle
from engine.style_utils import chinese_size_to_pt, merge_style


def test_chinese_size_to_pt_maps_common_sizes():
    assert chinese_size_to_pt("二号") == 22.0
    assert chinese_size_to_pt("三号") == 16.0
    assert chinese_size_to_pt("小三") == 15.0
    assert chinese_size_to_pt("四号") == 14.0


def test_merge_style_ignores_none_values():
    base = ParagraphStyle(font="仿宋", size="三号", align="left", line_spacing="28pt")
    override = ParagraphStyle(font=None, size="二号", align="center", line_spacing=None)

    merged = merge_style(base, override)

    assert merged.font == "仿宋"
    assert merged.size == "二号"
    assert merged.align == "center"
    assert merged.line_spacing == "28pt"
