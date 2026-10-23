"""ファイルの読み書き・コピー・削除とハッシュを扱う。書き込みを伴う操作はこのモジュールだけで行う。"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections.abc import Iterable
from pathlib import Path

from tune_kit.errors import KitError

# リポジトリを写すときに常に除く名前（どの深さでも一致）。"/" で始まるものはルート直下だけに一致する
DEFAULT_SKIP = (
    ".git",
    ".hg",
    ".svn",
    ".tune",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    ".gradle",
    ".DS_Store",
    "node_modules",
    ".venv",
    "venv",
    ".terraform",
    "/dist",
    "/build",
    "/coverage",
    "/target",
)
TEXT_LIMIT = 1_000_000


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise KitError(f"{path} を読めません（{exc.strerror or exc}）") from exc
    except UnicodeDecodeError as exc:
        raise KitError(f"{path} は UTF-8 のテキストではありません") from exc


def read_json(path: Path) -> object:
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise KitError(f"{path} は JSON として読めません（{exc.lineno} 行目: {exc.msg}）") from exc


def read_json_problems(path: Path) -> tuple[object, list[str]]:
    """JSON を読む。無いか読めなければ、例外ではなく問題の文を返す（status が問題を表示するため）。"""
    if not path.is_file():
        return None, [f"{path.name} がありません"]
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except UnicodeDecodeError:
        return None, [f"{path.name} は UTF-8 のテキストではありません"]
    except json.JSONDecodeError as exc:
        return None, [f"{path.name} は JSON として読めません（{exc.lineno} 行目: {exc.msg}）"]


def read_optional_text(path: Path) -> str | None:
    """テキストとして読めればその中身、無いか大きすぎるか読めなければ None。"""
    if not path.is_file() or path.stat().st_size > TEXT_LIMIT:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: object) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def write_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def remove_tree(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def copy_tree(source: Path, destination: Path) -> None:
    """ディレクトリを丸ごと写す。写し先が既にあれば消してから写す。"""
    remove_tree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, symlinks=True)


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def copy_tree_over(source: Path, destination: Path) -> None:
    """ディレクトリの中身を写し先に重ねる。同じ名前のファイルは置き換える。"""
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, symlinks=True, dirs_exist_ok=True)


def _build_skip(entries: Iterable[str]) -> tuple[set[str], set[str]]:
    names = {entry for entry in entries if not entry.startswith("/")}
    roots = {entry.strip("/") for entry in entries if entry.startswith("/")}
    return names, roots


def copy_repo(source: Path, destination: Path) -> None:
    """リポジトリを写す。DEFAULT_SKIP の名前とシンボリックリンクのディレクトリは写さない。"""
    names, roots = _build_skip(DEFAULT_SKIP)

    def ignore(directory: str, entries: list[str]) -> list[str]:
        at_root = Path(directory).resolve() == source.resolve()
        return [name for name in entries if name in names or (at_root and name in roots)]

    if destination.exists():
        raise KitError(f"{destination} は既にあります。作業場所を消してから eval-prepare をやり直してください")
    shutil.copytree(source, destination, symlinks=True, ignore=ignore)


def list_files(root: Path) -> list[str]:
    """ルート以下のファイルの相対パスを昇順で返す。.git とシンボリックリンクは辿らない。"""
    found: list[str] = []
    if not root.is_dir():
        return found
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        relative = Path(directory).relative_to(root).as_posix()
        dirnames[:] = sorted(name for name in dirnames if name != ".git" and not (Path(directory) / name).is_symlink())
        for name in filenames:
            if (Path(directory) / name).is_symlink():
                continue
            found.append(name if relative == "." else f"{relative}/{name}")
    return sorted(found)


def compute_file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_tree_sha(root: Path) -> str:
    """ディレクトリの中のファイルの相対パスと中身から作るハッシュ。ディレクトリが無ければ空のハッシュ。"""
    digest = hashlib.sha256()
    for relative in list_files(root):
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(compute_file_sha(root / relative).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def compute_data_sha(data: object) -> str:
    """JSON にできる値のハッシュ。キーの順に左右されない。"""
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()
