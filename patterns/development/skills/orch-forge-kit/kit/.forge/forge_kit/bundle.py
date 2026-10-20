"""バンドル（対象スキルの SKILL.md・references/ と、<スキル名>-<役> のサブエージェント）の決まりと写しを扱う。

バンドルの置き場（バンドルのルート）は、skills/<スキル名>/ と agents/ を持つディレクトリである。
対象のリポジトリの .claude/、下書き（build/draft/）、候補（rounds/<N>/proposed/）が同じ形を持つ。
決まりは RULES の表だけに書き、forge-build/references/bundle-rules.md はこの表から生成する（STR-06）。
"""

from __future__ import annotations

import difflib
import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from forge_kit import fsops, layout
from forge_kit.errors import KitError

AGENT_TOOLS = ("Read", "Write", "Edit", "Glob", "Grep", "Bash")
# macOS・Linux では、Bash のあるセッションにこの2つが無い（Bash の find・grep で探す）
SEARCH_TOOLS = ("Glob", "Grep")
SEARCH_WORD = re.compile(r"\b(?:Glob|Grep)\b")
AGENT_KEYS = ("name", "description", "tools", "model", "effort", "maxTurns", "omitClaudeMd", "color")
SECTIONS = ("## 役割", "## 手順", "## 人に確かめること", "## 報告", "## してはいけないこと")
STEPS_HEADING = "## 手順"
CHECKPOINTS_HEADING = "## 人に確かめること"
REPORT_HEADING = "## 報告"
DEFAULT_MARK = "既定:"
NOTHING = "- なし"
TODO_MARK = "TODO(forge)"
SKILL_MAX_LINES = 500
DESCRIPTION_MAX_CHARS = 1536
AGENTS_BOUNDS = (1, 6)
STEPS_BOUNDS = (2, 12)
LEAK_MIN_CHARS = 20
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
FIELD = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")
STEP_LINE = re.compile(r"^[0-9]+\.\s+(.+)$")
LINK = re.compile(r"\]\(([^)#]+)\)")
ROLE_PATTERN = r"[a-z0-9]+(?:-[a-z0-9]+)*"
ROLE = re.compile(f"^{ROLE_PATTERN}$")


@dataclass(frozen=True)
class Agent:
    """バンドルのサブエージェントの定義。role はファイル名の <スキル名>- の後ろ。"""

    role: str
    file: str
    fields: Mapping[str, str]
    text: str

    @property
    def tools(self) -> tuple[str, ...]:
        return tuple(tool.strip() for tool in self.fields.get("tools", "").split(",") if tool.strip())


@dataclass(frozen=True)
class Context:
    """決まりの検査に渡す材料。roles は承認した設計の役と道具（構築のときだけ）、fragments は評価課題の文。"""

    root: Path
    skill_name: str
    skill_text: str
    fields: Mapping[str, str]
    skill_files: tuple[str, ...]
    agents: tuple[Agent, ...]
    roles: Mapping[str, tuple[str, ...]] | None
    fragments: frozenset[str]

    @property
    def body(self) -> str:
        return FRONTMATTER.sub("", self.skill_text, count=1)


@dataclass(frozen=True)
class Rule:
    id: str
    text: str
    check: Callable[[Context], list[str]]


def frontmatter(text: str) -> dict[str, str]:
    """frontmatter の1行の項目だけを読む（複数行の値は先頭行だけ）。"""
    found = FRONTMATTER.match(text)
    if found is None:
        return {}
    fields = {}
    for line in found.group(1).splitlines():
        match = FIELD.match(line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip("\"'")
    return fields


def section(text: str, heading: str) -> str:
    """`## ` の見出しの節の本文（次の `## ` まで）。節が無ければ空。"""
    lines = text.splitlines()
    if heading not in lines:
        return ""
    start = lines.index(heading) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end]).strip()


def steps(skill_text: str) -> tuple[str, ...]:
    """`## 手順` の番号付きの一覧の項目（字下げの無い行だけ）。採点役が手順ごとに判定する。"""
    found = (STEP_LINE.match(line) for line in section(skill_text, STEPS_HEADING).splitlines())
    return tuple(match.group(1).strip() for match in found if match)


def skill_dir(root: Path, skill_name: str) -> Path:
    return root / layout.SKILLS_DIR / skill_name


def agent_paths(root: Path, skill_name: str) -> tuple[Path, ...]:
    directory = root / layout.AGENTS_DIR
    if not directory.is_dir():
        return ()
    return tuple(sorted(directory.glob(f"{skill_name}-*{layout.AGENT_SUFFIX}")))


def files(root: Path, skill_name: str) -> tuple[str, ...]:
    """バンドルのファイルの、バンドルのルートからの相対パス。"""
    found = []
    directory = skill_dir(root, skill_name)
    if directory.is_dir():
        found += [f"{layout.SKILLS_DIR}/{skill_name}/{name}" for name in fsops.list_files(directory, (), ())]
    found += [f"{layout.AGENTS_DIR}/{path.name}" for path in agent_paths(root, skill_name)]
    return tuple(found)


def has_bundle(root: Path, skill_name: str) -> bool:
    return (skill_dir(root, skill_name) / layout.SKILL_FILE).is_file()


def copy(source: Path, destination: Path, skill_name: str) -> None:
    """destination のバンドルを、source のバンドルで置き換える（消えたサブエージェントの定義も消す）。"""
    if not has_bundle(source, skill_name):
        raise KitError(f"{skill_dir(source, skill_name)}/{layout.SKILL_FILE} がありません")
    fsops.remove_tree(skill_dir(destination, skill_name))
    for path in agent_paths(destination, skill_name):
        fsops.remove_tree(path)
    fsops.copy_tree(skill_dir(source, skill_name), skill_dir(destination, skill_name))
    for path in agent_paths(source, skill_name):
        fsops.copy_file(path, destination / layout.AGENTS_DIR / path.name)


def place(where: layout.Layout, skill_name: str, source: Path) -> None:
    """対象のリポジトリの .claude/ のバンドルを置き換える。呼ぶのは install と decide --adopt だけ（OPS-04）。"""
    copy(source, where.claude_dir, skill_name)


def strip_kit(claude_dir: Path) -> None:
    """評価用のコピーから、この道具のスキルとサブエージェント（forge-*）を除く。実行役に見せないため。"""
    for path in sorted((claude_dir / layout.SKILLS_DIR).glob(f"{layout.KIT_PREFIX}*")):
        fsops.remove_tree(path)
    for path in sorted((claude_dir / layout.AGENTS_DIR).glob(f"{layout.KIT_PREFIX}*")):
        fsops.remove_tree(path)


def digest(root: Path, skill_name: str) -> str:
    """バンドルのファイルの名前と中身のハッシュ。検査の後に下書きが変わっていないかを確かめる。"""
    hasher = hashlib.sha256()
    for relative in files(root, skill_name):
        hasher.update(relative.encode("utf-8") + b"\0")
        hasher.update(fsops.read_text(root / relative).encode("utf-8") + b"\0")
    return hasher.hexdigest()


def text_of(root: Path, skill_name: str) -> str:
    return "\n".join(fsops.read_optional_text(root / relative) or "" for relative in files(root, skill_name))


def diff(before: Path, after: Path, skill_name: str) -> str:
    """2つのバンドルの unified diff。"""
    paths = sorted(set(files(before, skill_name)) | set(files(after, skill_name)))
    lines: list[str] = []
    for relative in paths:
        old = fsops.read_optional_text(before / relative)
        new = fsops.read_optional_text(after / relative)
        if old == new:
            continue
        lines += difflib.unified_diff(
            (old or "").splitlines(keepends=True),
            (new or "").splitlines(keepends=True),
            f"a/{relative}" if old is not None else "/dev/null",
            f"b/{relative}" if new is not None else "/dev/null",
        )
    return "".join(lines)


def _agents(root: Path, skill_name: str) -> tuple[Agent, ...]:
    found = []
    for path in agent_paths(root, skill_name):
        text = fsops.read_text(path)
        role = path.stem[len(skill_name) + 1 :]
        found.append(Agent(role, f"{layout.AGENTS_DIR}/{path.name}", frontmatter(text), text))
    return tuple(found)


def context(
    root: Path,
    skill_name: str,
    *,
    roles: Mapping[str, tuple[str, ...]] | None = None,
    fragments: frozenset[str] = frozenset(),
) -> Context:
    skill_md = skill_dir(root, skill_name) / layout.SKILL_FILE
    text = fsops.read_optional_text(skill_md) or ""
    directory = skill_dir(root, skill_name)
    skill_files = tuple(fsops.list_files(directory, (), ())) if directory.is_dir() else ()
    agents = _agents(root, skill_name)
    return Context(root, skill_name, text, frontmatter(text), skill_files, agents, roles, fragments)


def _skill_place(ctx: Context) -> list[str]:
    if not ctx.skill_text:
        return [f"{layout.SKILLS_DIR}/{ctx.skill_name}/{layout.SKILL_FILE} がありません"]
    if ctx.fields.get("name") != ctx.skill_name:
        return [f"SKILL.md の frontmatter の name を {ctx.skill_name} にしてください（今: {ctx.fields.get('name')}）"]
    return []


def _description(ctx: Context) -> list[str]:
    description = ctx.fields.get("description", "")
    if not description:
        return ["SKILL.md の frontmatter に description を1行で書いてください"]
    total = len(description) + len(ctx.fields.get("when_to_use", ""))
    if total > DESCRIPTION_MAX_CHARS:
        return [f"description と when_to_use の合計を {DESCRIPTION_MAX_CHARS} 文字以内にしてください（今: {total}）"]
    return []


def _invocation(ctx: Context) -> list[str]:
    problems = []
    if ctx.fields.get("disable-model-invocation") != "true":
        problems.append("SKILL.md の frontmatter に disable-model-invocation: true を書いてください")
    if "context" in ctx.fields:
        problems.append("SKILL.md の frontmatter に context を書かないでください（メインのセッションで動かす）")
    return problems


def _size_and_references(ctx: Context) -> list[str]:
    problems = []
    lines = len(ctx.skill_text.splitlines())
    if lines > SKILL_MAX_LINES:
        problems.append(
            f"SKILL.md が {lines} 行あります。{SKILL_MAX_LINES} 行以内にし、詳細は references/ に分けてください"
        )
    linked = set(LINK.findall(ctx.skill_text))
    for relative in ctx.skill_files:
        if relative == layout.SKILL_FILE:
            continue
        parts = relative.split("/")
        if len(parts) != 2 or parts[0] != layout.REFERENCES_DIR:
            problems.append(f"{relative} は references/<ファイル> の1階層に置いてください")
        elif relative not in linked:
            problems.append(f"{relative} を SKILL.md から参照してください（[…]({relative}) の形）")
    for target in sorted(linked):
        if target.startswith(layout.REFERENCES_DIR + "/") and target not in ctx.skill_files:
            problems.append(f"SKILL.md が参照する {target} がありません")
    return problems


def _sections(ctx: Context) -> list[str]:
    lines = ctx.skill_text.splitlines()
    found = [line for line in lines if line in SECTIONS]
    if found != list(SECTIONS):
        return [
            f"SKILL.md の節を {'、'.join(SECTIONS)} の順に1つずつ置いてください（今: {'、'.join(found) or 'なし'}）"
        ]
    problems = []
    count = len(steps(ctx.skill_text))
    if not STEPS_BOUNDS[0] <= count <= STEPS_BOUNDS[1]:
        problems.append(
            f"{STEPS_HEADING} の番号付きの項目を {STEPS_BOUNDS[0]}〜{STEPS_BOUNDS[1]} 個にしてください（今: {count}）"
        )
    gates = [line for line in section(ctx.skill_text, CHECKPOINTS_HEADING).splitlines() if line.startswith("- ")]
    if not gates:
        problems.append(f"{CHECKPOINTS_HEADING} に `- ` の項目を書いてください。無ければ `{NOTHING}` と書きます")
    for line in gates:
        if line != NOTHING and DEFAULT_MARK not in line:
            problems.append(
                f"{CHECKPOINTS_HEADING} の項目に、人が答えられないときの `{DEFAULT_MARK}` を書いてください: {line}"
            )
    return problems


def _agent_names(ctx: Context) -> list[str]:
    problems = []
    if not AGENTS_BOUNDS[0] <= len(ctx.agents) <= AGENTS_BOUNDS[1]:
        problems.append(
            f"{layout.AGENTS_DIR}/{ctx.skill_name}-<役>.md を {AGENTS_BOUNDS[0]}〜{AGENTS_BOUNDS[1]} 個置いてください"
            f"（今: {len(ctx.agents)}）"
        )
    for agent in ctx.agents:
        expected = f"{ctx.skill_name}-{agent.role}"
        if not ROLE.match(agent.role):
            problems.append(f"{agent.file} の役の名前は kebab-case にしてください")
        if agent.fields.get("name") != expected:
            problems.append(f"{agent.file} の frontmatter の name を {expected} にしてください")
    return problems


def _agent_keys(ctx: Context) -> list[str]:
    problems = []
    for agent in ctx.agents:
        extra = sorted(set(agent.fields) - set(AGENT_KEYS))
        if extra:
            problems.append(f"{agent.file} の frontmatter に書けないキーがあります: {', '.join(extra)}")
        problems += [
            f"{agent.file} の frontmatter に {key} を書いてください"
            for key in ("description", "tools")
            if not agent.fields.get(key)
        ]
    return problems


def _agent_tools(ctx: Context) -> list[str]:
    problems = []
    for agent in ctx.agents:
        extra = [tool for tool in agent.tools if tool not in AGENT_TOOLS]
        if extra:
            problems.append(
                f"{agent.file} の tools は {', '.join(AGENT_TOOLS)} から選んでください（不可: {', '.join(extra)}）"
            )
    return problems


def has_hidden_search(tools: Sequence[str]) -> bool:
    """Bash と一緒に Glob・Grep を持つか。macOS・Linux では、そのとき Glob・Grep が使えない。"""
    return "Bash" in tools and any(tool in SEARCH_TOOLS for tool in tools)


def _search_tools(ctx: Context) -> list[str]:
    problems = []
    for relative in ctx.skill_files:
        text = fsops.read_optional_text(skill_dir(ctx.root, ctx.skill_name) / relative) or ""
        if SEARCH_WORD.search(text):
            name = f"{layout.SKILLS_DIR}/{ctx.skill_name}/{relative}"
            problems.append(f"{name} に Glob・Grep を書かず、Bash の find・grep で探すと書いてください")
    for agent in ctx.agents:
        if "Bash" in agent.tools and SEARCH_WORD.search(agent.text):
            problems.append(f"{agent.file} は Bash を持つので、tools と本文に Glob・Grep を書かないでください")
    return problems


def _mentions(ctx: Context) -> list[str]:
    names = {f"{ctx.skill_name}-{agent.role}" for agent in ctx.agents}
    pattern = re.compile(r"(?<![a-z0-9-])" + re.escape(ctx.skill_name) + r"-[a-z0-9]+(?:-[a-z0-9]+)*")
    mentioned = set(pattern.findall(ctx.body))
    problems = [f"SKILL.md に {name} の起動を書いてください" for name in sorted(names - mentioned)]
    problems += [f"SKILL.md の {name} はバンドルにありません" for name in sorted(mentioned - names)]
    return problems


def _no_todo(ctx: Context) -> list[str]:
    texts = [(f"{layout.SKILLS_DIR}/{ctx.skill_name}/{layout.SKILL_FILE}", ctx.skill_text)]
    texts += [(agent.file, agent.text) for agent in ctx.agents]
    return [f"{name} に {TODO_MARK} が残っています" for name, text in texts if TODO_MARK in text]


def _design_match(ctx: Context) -> list[str]:
    if ctx.roles is None:
        return []
    found = {agent.role: tuple(sorted(agent.tools)) for agent in ctx.agents}
    expected = {role: tuple(sorted(tools)) for role, tools in ctx.roles.items()}
    problems = [f"設計の役 {role} のサブエージェントがありません" for role in sorted(set(expected) - set(found))]
    problems += [f"設計に無い役 {role} のサブエージェントがあります" for role in sorted(set(found) - set(expected))]
    for role in sorted(set(found) & set(expected)):
        if found[role] != expected[role]:
            problems.append(f"役 {role} の tools を設計と同じ {', '.join(expected[role])} にしてください")
    return problems


def _no_leak(ctx: Context) -> list[str]:
    texts = [(f"{layout.SKILLS_DIR}/{ctx.skill_name}/{layout.SKILL_FILE}", ctx.skill_text)]
    texts += [(agent.file, agent.text) for agent in ctx.agents]
    for relative in ctx.skill_files:
        if relative != layout.SKILL_FILE:
            path = skill_dir(ctx.root, ctx.skill_name) / relative
            texts.append((f"{layout.SKILLS_DIR}/{ctx.skill_name}/{relative}", fsops.read_optional_text(path) or ""))
    return [
        f"{name} に評価課題の文がそのまま入っています（過剰適合）: {fragment[:60]}"
        for name, text in texts
        for fragment in sorted(ctx.fragments)
        if fragment in text
    ]


RULES: tuple[Rule, ...] = (
    Rule(
        "B01",
        "スキルは `skills/<スキル名>/SKILL.md` に置き、frontmatter の `name` をスキル名と同じにする。",
        _skill_place,
    ),
    Rule(
        "B02",
        "frontmatter に `description` を1行で書き、"
        f"`description` と `when_to_use` の合計を {DESCRIPTION_MAX_CHARS} 文字以内にする。",
        _description,
    ),
    Rule(
        "B03",
        "frontmatter に `disable-model-invocation: true` を書き、`context` を書かない"
        "（人が `/<スキル名>` で呼び、メインのセッションで動かす）。",
        _invocation,
    ),
    Rule(
        "B04",
        f"SKILL.md は {SKILL_MAX_LINES} 行以内にする。"
        "SKILL.md 以外のファイルは `references/<ファイル>` の1階層に置き、"
        "全部を SKILL.md から `[…](references/<ファイル>)` で参照する。",
        _size_and_references,
    ),
    Rule(
        "B05",
        f"SKILL.md に {'、'.join(f'`{s}`' for s in SECTIONS)} をこの順に置く。"
        f"`{STEPS_HEADING}` は番号付きの一覧で {STEPS_BOUNDS[0]}〜{STEPS_BOUNDS[1]} 項目にする。"
        f"`{CHECKPOINTS_HEADING}` の各項目（`- ` の行）に、人が答えられないときの答えを `{DEFAULT_MARK}` で書く。"
        f"無ければ `{NOTHING}` と書く。",
        _sections,
    ),
    Rule(
        "B06",
        f"サブエージェントは `agents/<スキル名>-<役>.md` に {AGENTS_BOUNDS[0]}〜{AGENTS_BOUNDS[1]} 個置く。"
        "役は kebab-case にし、frontmatter の `name` を `<スキル名>-<役>` にする。",
        _agent_names,
    ),
    Rule(
        "B07",
        f"サブエージェントの frontmatter のキーは {', '.join(f'`{k}`' for k in AGENT_KEYS)} だけにし、"
        "`description` と `tools` を必ず書く（`permissionMode` で権限を広げない）。",
        _agent_keys,
    ),
    Rule(
        "B08",
        f"サブエージェントの `tools` は {', '.join(f'`{t}`' for t in AGENT_TOOLS)} の中から列挙する"
        "（`Agent` を入れないので、サブエージェントはさらにサブエージェントを起動しない）。",
        _agent_tools,
    ),
    Rule(
        "B09",
        "SKILL.md の本文に、全サブエージェントの名前（`<スキル名>-<役>`）を書き、"
        "バンドルに無い `<スキル名>-` の名前を書かない。",
        _mentions,
    ),
    Rule("B10", f"`{TODO_MARK}` を残さない。", _no_todo),
    Rule(
        "B11",
        "構築のときは、サブエージェントの役と `tools` を、承認した設計（design.json の roles）と同じにする。",
        _design_match,
    ),
    Rule(
        "B12",
        f"評価課題の文（課題文と受け入れ条件の、{LEAK_MIN_CHARS} 字以上の行）をそのまま写さない。",
        _no_leak,
    ),
    Rule(
        "B13",
        "スキルのファイルに `Glob`・`Grep` を書かず、ファイルは Bash の `find`・`grep` で探すと書く。"
        "`Bash` を持つサブエージェントの `tools` と本文にも `Glob`・`Grep` を書かない"
        "（macOS・Linux では、Bash のあるセッションに Glob・Grep が無い）。",
        _search_tools,
    ),
)


def check(
    root: Path,
    skill_name: str,
    *,
    roles: Mapping[str, tuple[str, ...]] | None = None,
    fragments: frozenset[str] = frozenset(),
) -> list[str]:
    """バンドルが RULES を満たすかを検査し、`<id> <問題>` の一覧を返す。"""
    ctx = context(root, skill_name, roles=roles, fragments=fragments)
    if not ctx.skill_text:
        return [f"{RULES[0].id} {problem}" for problem in RULES[0].check(ctx)]
    return [f"{rule.id} {problem}" for rule in RULES for problem in rule.check(ctx)]
