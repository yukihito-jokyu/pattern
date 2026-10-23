"""pattern-foundation のスクリプトが共有する部品。Python 3.9 以上の標準ライブラリだけを使う。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

MANIFEST_REL = ".foundation/manifest.json"
TODO_MARKER = "TODO(" + "pattern-foundation)"  # このファイル自体が --final の検査に引っかからないよう分割する

# 走査・コピーで常に除外するディレクトリ（ビルド成果物、キャッシュ、VCS）。
# 名前だけの要素はどの深さでも、"/" で始まる要素はルートからのパスに一致するものだけを除外する
# （build・dist などの汎用名は、src/commands/build/ のようなソースと区別するためルート直下に限る）。
DEFAULT_SKIP_DIRS = [
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", ".nox", ".nyc_output", ".next", ".nuxt", ".svelte-kit",
    ".turbo", ".parcel-cache", ".cache", ".vite", ".gradle", ".DS_Store",
    "/dist", "/build", "/coverage", "/target",
]
# コピーせずシンボリックリンクで共有する依存ディレクトリ
DEFAULT_LINK_DIRS = ["node_modules", ".venv", "venv", ".terraform"]


def fail(message: str, code: int = 1) -> None:
    print(f"ERROR {message}", file=sys.stderr)
    sys.exit(code)


def find_root(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / MANIFEST_REL).is_file():
            return candidate
    return None


def resolve_root(arg: str | None) -> Path:
    if arg:
        root = Path(arg).resolve()
        if not (root / MANIFEST_REL).is_file():
            fail(f"{root / MANIFEST_REL} がありません")
        return root
    root = find_root(Path.cwd())
    if root is None:
        fail(f"{MANIFEST_REL} が見つかりません。--root を指定してください")
    return root


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} の JSON が不正です: {exc}")
    except FileNotFoundError:
        fail(f"{path} がありません")
    return {}


def load_manifest(root: Path) -> dict:
    return load_json(root / MANIFEST_REL)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def glob_to_regex(pattern: str) -> re.Pattern:
    """`**`、`*`、`?`、`{a,b}` に対応する glob を、ルートからの相対パス全体に一致する正規表現にする。"""
    out = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if pattern.startswith("**/", i):
                out.append("(?:.*/)?")
                i += 3
                continue
            if pattern.startswith("**", i):
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "{":
            end = pattern.find("}", i)
            if end == -1:
                out.append(re.escape(c))
            else:
                alternatives = pattern[i + 1:end].split(",")
                out.append("(?:" + "|".join(re.escape(a) for a in alternatives) + ")")
                i = end + 1
                continue
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def matches_any(rel_path: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        if glob_to_regex(pattern).match(rel_path):
            return pattern
    return None


def copy_settings(manifest: dict) -> tuple[list[str], list[str]]:
    copy = manifest.get("copy", {})
    skip = sorted(set(DEFAULT_SKIP_DIRS) | set(copy.get("skip_dirs", [])))
    link = sorted(set(DEFAULT_LINK_DIRS) | set(copy.get("link_dirs", [])))
    return skip, link


def split_skip(entries: list[str]) -> tuple[set[str], list[str]]:
    """除外の指定を、どの深さでも一致させる名前と、ルートからのパスに分ける。"""
    names = {e for e in entries if not e.startswith("/")}
    rels = [e.strip("/") for e in entries if e.startswith("/")]
    return names, rels


def under(rel: str, prefixes: list[str]) -> bool:
    return any(rel == p or rel.startswith(p + "/") for p in prefixes)


def iter_files(root: Path, skip_dirs: list[str], link_dirs: list[str], extra_skip_rel: list[str] | None = None):
    """ルート以下のファイルを、相対パス（POSIX 形式）の昇順で返す。シンボリックリンクは辿らない。"""
    skip_names, skip_rels = split_skip(list(skip_dirs) + list(link_dirs))
    extra = skip_rels + [p.strip("/") for p in (extra_skip_rel or [])]
    results = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        kept = []
        for d in dirnames:
            rel = f"{rel_dir}/{d}" if rel_dir else d
            if d in skip_names or under(rel, extra):
                continue
            if (Path(dirpath) / d).is_symlink():
                continue
            kept.append(d)
        dirnames[:] = sorted(kept)
        for f in filenames:
            if f in skip_names or under(f"{rel_dir}/{f}" if rel_dir else f, extra):
                continue
            full = Path(dirpath) / f
            if full.is_symlink():
                continue
            results.append(f"{rel_dir}/{f}" if rel_dir else f)
    return sorted(results)


def is_text(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            chunk = fh.read(8192)
    except OSError:
        return False
    if b"\0" in chunk:
        return False
    try:
        chunk.decode("utf-8")
    except UnicodeDecodeError as exc:
        # 8KB の境界で多バイト文字が切れた場合だけは許す
        return exc.start >= len(chunk) - 3
    return True


def read_text(path: Path) -> str | None:
    if not is_text(path):
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def copy_project(src: Path, dst: Path, skip_dirs: list[str], link_dirs: list[str],
                 exclude_rel: list[str] | None = None) -> None:
    """依存ディレクトリはシンボリックリンクにし、ビルド成果物とキャッシュと exclude_rel のパスは除いてコピーする。"""
    if dst.exists():
        fail(f"{dst} は既にあります")
    skip_names, skip_rels = split_skip(skip_dirs)
    skip_rels += [p.strip("/") for p in (exclude_rel or [])]
    link_names = set(link_dirs)
    linked: list[tuple[Path, Path]] = []

    def ignore(directory: str, names: list[str]) -> list[str]:
        ignored = []
        rel_dir = Path(directory).relative_to(src).as_posix()
        for name in names:
            rel = name if rel_dir == "." else f"{rel_dir}/{name}"
            if name in skip_names or under(rel, skip_rels):
                ignored.append(name)
            elif name in link_names:
                ignored.append(name)
                source = Path(directory) / name
                target = dst / source.relative_to(src)
                linked.append((source, target))
        return ignored

    shutil.copytree(src, dst, symlinks=True, ignore=ignore)
    for source, target in linked:
        if not target.exists():
            target.symlink_to(source.resolve(), target_is_directory=source.is_dir())


def git_snapshot(directory: Path, message: str = "base") -> bool:
    """git があれば、ディレクトリを新しいリポジトリにして基準のコミットを作る。"""
    if shutil.which("git") is None:
        return False
    git = ["git", "-c", "user.name=pattern-foundation", "-c", "user.email=pattern-foundation@localhost",
           "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "--allow-empty", "-m", message]):
        result = subprocess.run(git + args, cwd=directory, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"WARN git {' '.join(args)} に失敗しました: {result.stderr.strip()}", file=sys.stderr)
            return False
    return True


def apply_file_change(root: Path, change: dict) -> tuple[Path, bytes | None]:
    """probe・seed のファイル変更を1件適用し、元に戻すための情報（パスと元の内容）を返す。"""
    rel = change.get("path", "")
    mode = change.get("mode", "create")
    content = change.get("content", "")
    target = (root / rel).resolve()
    if root.resolve() not in target.parents:
        raise ValueError(f"{rel} は基盤の外を指しています")
    original = target.read_bytes() if target.exists() else None
    if mode == "create":
        if original is not None:
            raise ValueError(f"{rel} は既にあります（mode=create）")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    elif mode == "replace":
        if original is None:
            raise ValueError(f"{rel} がありません（mode=replace）")
        target.write_text(content, encoding="utf-8")
    elif mode == "append":
        if original is None:
            raise ValueError(f"{rel} がありません（mode=append）")
        with target.open("a", encoding="utf-8") as fh:
            fh.write(content)
    else:
        raise ValueError(f"mode {mode} は create / replace / append のどれかにしてください")
    return target, original


def revert_file_change(target: Path, original: bytes | None) -> None:
    if original is None:
        if target.exists():
            target.unlink()
    else:
        target.write_bytes(original)


def run_shell(command: str, cwd: Path, timeout: int) -> tuple[int, str]:
    env = dict(os.environ)
    env.setdefault("CI", "1")
    try:
        result = subprocess.run(command, cwd=cwd, shell=True, capture_output=True, text=True,
                                timeout=timeout, env=env)
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        return 124, out + f"\n[timeout] {timeout} 秒で打ち切りました"


def tail(text: str, lines: int = 20) -> str:
    return "\n".join(text.rstrip().splitlines()[-lines:])
