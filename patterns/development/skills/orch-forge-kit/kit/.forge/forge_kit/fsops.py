"""ファイルの書き込み・コピー・削除と、ディレクトリの指紋を扱う。書き込みを伴う操作はこのモジュールだけで行う。"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Iterable
from pathlib import Path

from forge_kit.errors import KitError

# コピーで常に除く名前（どの深さでも一致）。"/" で始まるものはルート直下だけに一致する
DEFAULT_SKIP = (
    ".git",
    ".hg",
    ".svn",
    ".forge",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".turbo",
    ".parcel-cache",
    ".cache",
    ".vite",
    ".gradle",
    ".DS_Store",
    "/dist",
    "/build",
    "/coverage",
    "/target",
)
# コピーせず、元のディレクトリへのシンボリックリンクにする依存ディレクトリ
DEFAULT_LINK = ("node_modules", ".venv", "venv", ".terraform")
TEXT_LIMIT = 1_000_000


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise KitError(f"{path} がありません") from exc
    except UnicodeDecodeError as exc:
        raise KitError(f"{path} は UTF-8 のテキストではありません") from exc


def read_json(path: Path) -> object:
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise KitError(f"{path} は JSON として読めません（{exc.lineno} 行目: {exc.msg}）") from exc


def read_optional_text(path: Path) -> str | None:
    """テキストとして読めればその中身、無いか読めなければ None。"""
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


def remove_tree(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def copy_tree(source: Path, destination: Path) -> None:
    """ディレクトリを丸ごと写す。写し先が既にあれば消してから写す。"""
    remove_tree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, symlinks=True, ignore=shutil.ignore_patterns("__pycache__"))


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _split(entries: Iterable[str]) -> tuple[set[str], set[str]]:
    names = {entry for entry in entries if not entry.startswith("/")}
    roots = {entry.strip("/") for entry in entries if entry.startswith("/")}
    return names, roots


def copy_repo(source: Path, destination: Path, skip: Iterable[str], link: Iterable[str]) -> None:
    """リポジトリを写す。skip の名前は除き、link の名前は元へのシンボリックリンクにする。"""
    skip_names, skip_roots = _split([*DEFAULT_SKIP, *skip])
    link_names = set(DEFAULT_LINK) | set(link)
    linked: list[tuple[Path, Path]] = []

    def ignore(directory: str, names: list[str]) -> list[str]:
        relative = Path(directory).relative_to(source).as_posix()
        ignored = []
        for name in names:
            at_root = relative == "."
            if name in skip_names or (at_root and name in skip_roots):
                ignored.append(name)
            elif name in link_names:
                ignored.append(name)
                original = Path(directory) / name
                linked.append((original, destination / original.relative_to(source)))
        return ignored

    if destination.exists():
        raise KitError(f"{destination} は既にあります。評価用のコピーを消してから prepare をやり直してください")
    shutil.copytree(source, destination, symlinks=True, ignore=ignore)
    for original, copied in linked:
        copied.symlink_to(original.resolve(), target_is_directory=original.is_dir())


def list_files(root: Path, skip: Iterable[str], link: Iterable[str]) -> list[str]:
    """ルート以下のファイルの相対パスを昇順で返す。skip・link の名前とシンボリックリンクは辿らない。"""
    skip_names, skip_roots = _split([*DEFAULT_SKIP, *skip, *DEFAULT_LINK, *link])
    found: list[str] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        relative = Path(directory).relative_to(root).as_posix()
        at_root = relative == "."
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in skip_names
            and not (at_root and name in skip_roots)
            and not (Path(directory) / name).is_symlink()
        )
        for name in filenames:
            full = Path(directory) / name
            if name in skip_names or full.is_symlink():
                continue
            found.append(name if at_root else f"{relative}/{name}")
    return sorted(found)


def fingerprint(root: Path, skip: Iterable[str], link: Iterable[str]) -> dict[str, str]:
    """ファイルごとの大きさと更新時刻。評価の前後で比べ、元のリポジトリが書き換えられていないかを確かめる。"""
    marks = {}
    for relative in list_files(root, skip, link):
        stat = (root / relative).stat()
        marks[relative] = f"{stat.st_size}:{stat.st_mtime_ns}"
    return marks
