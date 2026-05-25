from __future__ import annotations

import re
from typing import Optional, TypeVar

from pydantic import BaseModel

from engine.models import ParagraphStyle

T = TypeVar("T", bound=BaseModel)

CHINESE_SIZE_TO_PT = {
    "初号": 42.0,
    "小初": 36.0,
    "一号": 26.0,
    "小一": 24.0,
    "二号": 22.0,
    "小二": 18.0,
    "三号": 16.0,
    "小三": 15.0,
    "四号": 14.0,
    "小四": 12.0,
    "五号": 10.5,
    "小五": 9.0,
}


def chinese_size_to_pt(size: str) -> float:
    if size in CHINESE_SIZE_TO_PT:
        return CHINESE_SIZE_TO_PT[size]
    if size.endswith("pt"):
        return float(size[:-2])
    if re.fullmatch(r"\d+(\.\d+)?", size):
        return float(size)
    raise ValueError(f"Unsupported font size: {size}")


def parse_length_to_pt(value: str) -> float:
    if value.endswith("pt"):
        return float(value[:-2])
    if value.endswith("cm"):
        return float(value[:-2]) * 28.3464567
    if value.endswith("mm"):
        return float(value[:-2]) * 2.83464567
    if value.endswith("em"):
        return float(value[:-2]) * 16.0
    raise ValueError(f"Unsupported length: {value}")


def merge_model(base: T, override: Optional[T]) -> T:
    if override is None:
        return base
    data = base.model_dump()
    override_data = override.model_dump(exclude_none=True)
    for key, value in override_data.items():
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            data[key] = {**data[key], **value}
        else:
            data[key] = value
    return type(base).model_validate(data)


def merge_style(base: ParagraphStyle, override: Optional[ParagraphStyle]) -> ParagraphStyle:
    return merge_model(base, override)
