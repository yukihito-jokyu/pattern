"""JSON から読んだ値を型付きで取り出し、見つけた問題を一覧に集める。問題の場所は JSON のパスで示す。"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Iterable
from typing import Any


def at(where: str, key: str) -> str:
    return f"{where}.{key}" if where else key


def to_data(model: Any) -> dict[str, Any]:
    """frozen の dataclass を、JSON の値だけの dict にする（タプルはリスト）。キーはフィールド名と同じ（NAM-03）。"""
    data: dict[str, Any] = _plain(dataclasses.asdict(model))
    return data


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def as_object(value: object, where: str, problems: list[str]) -> dict[str, object]:
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return value
    problems.append(f"{where or '全体'} はオブジェクトにしてください")
    return {}


def unknown_keys(data: dict[str, object], allowed: Iterable[str], where: str, problems: list[str]) -> None:
    extra = sorted(set(data) - set(allowed))
    if extra:
        problems.append(f"{where or '全体'} に知らないキーがあります: {', '.join(extra)}")


def text(data: dict[str, object], key: str, where: str, problems: list[str], *, pattern: str = "") -> str:
    """文字列。pattern が空なら空文字も許し、空でなければ正規表現に全体が一致することを求める。"""
    value = data.get(key)
    if not isinstance(value, str):
        problems.append(f"{at(where, key)} は文字列にしてください")
        return ""
    if pattern and not re.fullmatch(pattern, value):
        problems.append(f"{at(where, key)} の形が違います（今: {value!r}、形: {pattern}）")
    return value


def filled(data: dict[str, object], key: str, where: str, problems: list[str]) -> str:
    value = text(data, key, where, problems)
    if isinstance(data.get(key), str) and not value.strip():
        problems.append(f"{at(where, key)} が空です")
    return value


def integer(data: dict[str, object], key: str, where: str, problems: list[str], *, bounds: tuple[int, int]) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        problems.append(f"{at(where, key)} は整数にしてください")
        return bounds[0]
    if not bounds[0] <= value <= bounds[1]:
        problems.append(f"{at(where, key)} は {bounds[0]} 以上 {bounds[1]} 以下にしてください（今: {value}）")
    return value


def boolean(data: dict[str, object], key: str, where: str, problems: list[str]) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        problems.append(f"{at(where, key)} は true か false にしてください")
        return False
    return value


def choice(data: dict[str, object], key: str, choices: Iterable[str], where: str, problems: list[str]) -> str:
    options = tuple(choices)
    value = text(data, key, where, problems)
    if isinstance(data.get(key), str) and value not in options:
        problems.append(f"{at(where, key)} は {', '.join(options)} のどれかにしてください（今: {value!r}）")
    return value


def texts(data: dict[str, object], key: str, where: str, problems: list[str]) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        problems.append(f"{at(where, key)} は文字列の配列にしてください")
        return ()
    for index, item in enumerate(value):
        if not item.strip():
            problems.append(f"{at(where, key)}[{index}] が空です")
    return tuple(value)


def objects(data: dict[str, object], key: str, where: str, problems: list[str]) -> list[tuple[str, dict[str, object]]]:
    """オブジェクトの配列。各要素を、その JSON のパスと組にして返す。"""
    value = data.get(key)
    if not isinstance(value, list):
        problems.append(f"{at(where, key)} は配列にしてください")
        return []
    found = []
    for index, item in enumerate(value):
        path = f"{at(where, key)}[{index}]"
        found.append((path, as_object(item, path, problems)))
    return found


def duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    repeated: list[str] = []
    for value in values:
        if value in seen and value not in repeated:
            repeated.append(value)
        seen.add(value)
    return repeated
