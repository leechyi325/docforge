from __future__ import annotations

import sys
from pathlib import Path

import yaml

from engine.models import Profile


def _get_profile_dir() -> Path:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / "engine" / "profiles"
    return Path(__file__).resolve().parent


PROFILE_DIR = _get_profile_dir()


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
