"""ファイルの読み書き・追記・写しを扱う。書き込みを伴う操作はこのモジュールだけで行う。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from autoflow_kit.errors import KitError


def read_text(path: Path) -> str:
    try:
        with path.open(encoding="utf-8") as stream:
            return stream.read()
    except FileNotFoundError as exc:
        raise KitError(f"{path} がありません") from exc
    except UnicodeDecodeError as exc:
        raise KitError(f"{path} は UTF-8 のテキストではありません") from exc


def read_json(path: Path) -> object:
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise KitError(f"{path} は JSON として読めません（{exc.lineno} 行目: {exc.msg}）") from exc


def read_lines(path: Path) -> tuple[object, ...]:
    """JSON Lines を1行ずつ読む。空の行は飛ばす。"""
    found = []
    for number, line in enumerate(read_text(path).splitlines(), 1):
        if not line.strip():
            continue
        try:
            found.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise KitError(f"{path} の {number} 行目は JSON として読めません（{exc.msg}）") from exc
    return tuple(found)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        stream.write(text)


def write_json(path: Path, data: object) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def append_line(path: Path, line: str) -> None:
    """1行を足す。実行の記録（trail.jsonl）は、このモジュールの追記だけで増やす。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(line.rstrip("\n") + "\n")


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
