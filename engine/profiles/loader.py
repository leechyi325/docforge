from __future__ import annotations

from pathlib import Path

import yaml

from engine.models import Profile

PROFILE_DIR = Path(__file__).resolve().parent


def load_profile(profile_id: str) -> Profile:
    path = PROFILE_DIR / f"{profile_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_id}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Profile.model_validate(data)


def list_profiles() -> list[Profile]:
    profiles = []
    for path in sorted(PROFILE_DIR.glob("*.yaml")):
        profiles.append(Profile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8"))))
    return profiles
