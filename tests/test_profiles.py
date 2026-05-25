from engine.profiles.loader import list_profiles, load_profile


def test_general_profile_is_default_and_lightweight():
    profile = load_profile("general")

    assert profile.id == "general"
    assert profile.name == "通用格式文档"
    assert profile.required_fields == []
    assert profile.title.size == "二号"
    assert profile.body.font == "仿宋"
    assert profile.headings["heading_1"].font == "黑体"


def test_all_first_batch_profiles_load():
    ids = {profile.id for profile in list_profiles()}

    assert ids == {"official", "meeting_minutes", "briefing", "speech", "general"}
