"""cli.json を決まった形の文字列にする（formatter の本体。TOOL-01）。

字下げは空白2つ。スカラーだけの配列は1行に、オブジェクトを含む配列は1要素1行以上に書く。
キーの順と配列の並びは model.canonical が決める。ここは文字列にするだけである。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

INDENT = "  "
Path = Tuple[Any, ...]


def dumps(value: Any) -> str:
    """value を正規の形の JSON 文字列（末尾の改行つき）にする。"""
    lines, _ = render(value)
    return "\n".join(lines) + "\n"


def render(value: Any) -> Tuple[List[str], Dict[Path, int]]:
    """行の一覧と、各要素（キーの経路）が始まる行番号（1始まり）の対応を返す。"""
    lines: List[str] = []
    index: Dict[Path, int] = {(): 1}
    _emit(value, 0, "", (), lines, index)
    return lines, index


def _scalar(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _emit(value: Any, depth: int, prefix: str, path: Path, lines: List[str], index: Dict[Path, int]) -> None:
    pad = INDENT * depth
    inner = INDENT * (depth + 1)
    if isinstance(value, dict):
        if not value:
            lines.append(prefix + "{}")
            return
        lines.append(prefix + "{")
        keys = list(value)
        for i, key in enumerate(keys):
            index[path + (key,)] = len(lines) + 1
            _emit(value[key], depth + 1, f"{inner}{_scalar(key)}: ", path + (key,), lines, index)
            if i < len(keys) - 1:
                lines[-1] += ","
        lines.append(pad + "}")
        return
    if isinstance(value, list):
        if not value:
            lines.append(prefix + "[]")
            return
        if all(not isinstance(item, (dict, list)) for item in value):
            lines.append(prefix + "[" + ", ".join(_scalar(item) for item in value) + "]")
            for i in range(len(value)):
                index[path + (i,)] = len(lines)
            return
        lines.append(prefix + "[")
        for i, item in enumerate(value):
            index[path + (i,)] = len(lines) + 1
            _emit(item, depth + 1, inner, path + (i,), lines, index)
            if i < len(value) - 1:
                lines[-1] += ","
        lines.append(pad + "]")
        return
    lines.append(prefix + _scalar(value))


def pointer(path: Path) -> str:
    """("commands", 0, "options", 1) → commands[0].options[1]"""
    text = ""
    for part in path:
        text += f"[{part}]" if isinstance(part, int) else (f".{part}" if text else str(part))
    return text or "(root)"
