"""アクションの参照を、タグの指す完全なコミット SHA に固定する・検証する（DEP-05）。

SHA は記憶で書かず、必ずこのモジュールで `git ls-remote` から解決する。認証は要らない。
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
SPEC = re.compile(r"^(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?P<path>(/[A-Za-z0-9_.-]+)*)(@(?P<tag>[^\s@]+))?$")
USES = re.compile(r"^\s*-?\s*uses:\s*(?P<spec>[^\s@#]+)@(?P<ref>[0-9a-f]{40})\s+#\s+(?P<tag>\S+)\s*$")

ListTags = Callable[[str], str]


@dataclass(frozen=True)
class Pin:
    repo: str
    path: str
    tag: str
    sha: str

    def uses(self) -> str:
        return f"{self.repo}{self.path}@{self.sha} # {self.tag}"


@dataclass(frozen=True)
class Mismatch:
    file: str
    line: int
    spec: str
    message: str


def parse_tags(text: str) -> dict[str, str]:
    """`git ls-remote --tags` の出力を、タグ名 → コミット SHA にする。注釈付きタグは `^{}` の行（指す先）を採る。"""
    tags: dict[str, str] = {}
    peeled: dict[str, str] = {}
    for line in text.splitlines():
        sha, _, ref = line.partition("\t")
        if not ref.startswith("refs/tags/"):
            continue
        name = ref.removeprefix("refs/tags/")
        if name.endswith("^{}"):
            peeled[name.removesuffix("^{}")] = sha
        else:
            tags[name] = sha
    return {name: peeled.get(name, sha) for name, sha in tags.items()}


def latest(tags: Mapping[str, str]) -> str:
    """安定版（vX.Y.Z の形）のうち最も新しいタグ。プレリリースと、メジャーだけの移動タグ（v5）は選ばない。"""
    stable = [(tuple(int(part) for part in match.groups()), name) for name in tags if (match := SEMVER.match(name))]
    if not stable:
        raise LookupError("vX.Y.Z の形のタグが無い")
    return max(stable)[1]


def resolve(spec: str, list_tags: ListTags) -> Pin:
    """`owner/repo[/path][@tag]` を Pin にする。タグを省くと最新の安定版。"""
    match = SPEC.match(spec)
    if match is None:
        raise ValueError(f"{spec!r} は owner/repo[/path][@tag] の形ではない")
    tags = parse_tags(list_tags(match["repo"]))
    tag = match["tag"] or latest(tags)
    if tag not in tags:
        raise LookupError(f"{match['repo']} にタグ {tag} が無い")
    if not SEMVER.match(tag):
        raise ValueError(f"タグ {tag} は vX.Y.Z の形ではない。固定するのは完全な版のタグにする")
    return Pin(match["repo"], match["path"] or "", tag, tags[tag])


def pinned_uses(lines: Iterable[str]) -> list[tuple[int, str, str, str]]:
    """ファイルの `uses: owner/repo@<sha> # <tag>` の行を (行番号, spec, sha, tag) にする。"""
    found = []
    for number, line in enumerate(lines, 1):
        match = USES.match(line)
        if match and not match["spec"].startswith("./"):
            found.append((number, match["spec"], match["ref"], match["tag"]))
    return found


def verify(files: Mapping[str, Iterable[str]], list_tags: ListTags) -> list[Mismatch]:
    """固定した SHA が、コメントのタグの指す SHA と一致するかを確かめる。"""
    cache: dict[str, dict[str, str]] = {}
    mismatches = []
    for file, lines in files.items():
        for number, spec, sha, tag in pinned_uses(lines):
            repo = "/".join(spec.split("/")[:2])
            if repo not in cache:
                cache[repo] = parse_tags(list_tags(repo))
            expected = cache[repo].get(tag)
            if expected is None:
                mismatches.append(Mismatch(file, number, spec, f"{repo} にタグ {tag} が無い"))
            elif expected != sha:
                mismatches.append(Mismatch(file, number, spec, f"{tag} の SHA は {expected}（書かれているのは {sha}）"))
    return mismatches
