from engine.profiles.loader import list_profiles, load_profile


def test_general_profile_matches_default_style():
    profile = load_profile("general")

    assert profile.id == "general"
    assert profile.name == "通用格式文档"
    assert profile.required_fields == ["title", "body"]
    assert profile.title.font == "宋体"
    assert profile.title.size == "二号"
    assert profile.title.bold is True
    assert profile.body.font == "仿宋_GB2312"
    assert profile.body.line_spacing == "29pt"
    assert profile.headings["heading_1"].font == "黑体"
    assert profile.headings["heading_1"].bold is True
    assert profile.headings["heading_2"].font == "楷体_GB2312"
    assert "heading_3" in profile.headings
    assert profile.date_field is None
    assert profile.department_field is None
    assert profile.content_bold is not None



def test_default_profile_loads_with_template_format():
    profile = load_profile("default")

    assert profile.id == "default"
    assert profile.name == "默认文稿模板"
    assert profile.title.font == "宋体"
    assert profile.title.size == "二号"
    assert profile.title.bold is True
    assert profile.title.line_spacing == "29pt"
    assert profile.body.font == "仿宋_GB2312"
    assert profile.body.size == "三号"
    assert profile.body.line_spacing == "29pt"
    assert profile.body.first_line_indent == "2em"
    assert profile.date_field is not None
    assert profile.date_field.font == "楷体_GB2312"
    assert profile.department_field is not None
    assert profile.department_field.font == "楷体_GB2312"
    assert profile.headings["heading_1"].font == "黑体"
    assert profile.headings["heading_1"].bold is True
    assert profile.headings["heading_2"].font == "楷体_GB2312"
    assert profile.headings["heading_2"].bold is True
    assert "heading_3" in profile.headings
    assert profile.headings["heading_3"].font == "仿宋_GB2312"
    assert profile.headings["heading_3"].bold is True
    assert profile.content_bold is not None
    assert profile.content_bold.font == "楷体_GB2312"
    assert profile.page.margin_top == "3.5cm"
    assert profile.page.margin_bottom == "3.5cm"
    assert profile.page.margin_left == "2.8cm"
    assert profile.page.margin_right == "2.8cm"
    assert profile.page.page_number is not None
    assert profile.page.page_number.font == "宋体"
    assert profile.page.page_number.size == "四号"
    assert profile.page.page_number.format == "－ {page} －"


def test_all_profiles_load_including_default():
    ids = {profile.id for profile in list_profiles()}
    assert "default" in ids
    assert ids == {"default", "general"}
