"""ファイルの読み書き・コピー・削除、一時ディレクトリ、ハッシュ。ファイルを書き換えるのはこのモジュールだけ（DEP-04）。"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from h2_kit.errors import InvalidFileError, KitError

IGNORED_NAMES = frozenset({"__pycache__", ".DS_Store", ".mypy_cache", ".ruff_cache"})
IGNORED_SUFFIXES = frozenset({".pyc"})


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidFileError(f"{path} は UTF-8 のテキストではありません") from exc
    except OSError as exc:
        raise KitError(f"{path} を読めません: {exc.strerror or exc}") from exc


def read_text_or_none(path: Path) -> str | None:
    """UTF-8 のテキストなら中身を、テキストでないか読めなければ None を返す。"""
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def read_json(path: Path) -> object:
    text = read_text(path)
    try:
        data: object = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidFileError(f"{path} は JSON として読めません（{exc.lineno} 行目: {exc.msg}）") from exc
    return data


def write_text(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise KitError(f"{path} に書けません: {exc.strerror or exc}") from exc


def write_json(path: Path, data: object) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def write_dir(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise KitError(f"{path} を作れません: {exc.strerror or exc}") from exc


def write_temp_dir(prefix: str) -> Path:
    """OS の一時ディレクトリの下に空のディレクトリを作る。消すのは呼び出し側（remove_tree）。"""
    try:
        return Path(tempfile.mkdtemp(prefix=prefix)).resolve()
    except OSError as exc:
        raise KitError(f"一時ディレクトリを作れません: {exc.strerror or exc}") from exc


def copy_tree(source: Path, target: Path, skip: frozenset[str] = frozenset()) -> None:
    """source の中身で target を置き換える。skip の名前のファイルとディレクトリは、どの深さでも写さない。"""
    names = IGNORED_NAMES | skip
    remove_tree(target)
    try:
        shutil.copytree(source, target, ignore=lambda _dir, entries: [e for e in entries if _is_skipped(e, names)])
    except OSError as exc:
        raise KitError(f"{source} を {target} に写せません: {exc}") from exc


def copy_file(source: Path, target: Path) -> None:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    except OSError as exc:
        raise KitError(f"{source} を {target} に写せません: {exc.strerror or exc}") from exc


def remove_tree(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        remove_file(path)


def remove_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise KitError(f"{path} を消せません: {exc.strerror or exc}") from exc


def list_files(root: Path) -> list[str]:
    """root の下のファイルの相対パス（`/` 区切り、並べ替え済み）。root が無ければ空。"""
    if not root.is_dir():
        return []
    found = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_file() and not any(_is_skipped(part, IGNORED_NAMES) for part in relative.parts):
            found.append(relative.as_posix())
    return sorted(found)


def list_dirs(root: Path) -> list[str]:
    """root の直下のディレクトリの名前（並べ替え済み）。"""
    if not root.is_dir():
        return []
    return sorted(path.name for path in root.iterdir() if path.is_dir() and path.name not in IGNORED_NAMES)


def compute_text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_tree_sha256(root: Path) -> str:
    """ディレクトリの中身（相対パスとバイト列）のハッシュ。無ければ空のハッシュ。"""
    digest = hashlib.sha256()
    for relative in list_files(root):
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update((root / relative).read_bytes() + b"\0")
    return digest.hexdigest()


def _is_skipped(name: str, names: frozenset[str]) -> bool:
    return name in names or Path(name).suffix in IGNORED_SUFFIXES
