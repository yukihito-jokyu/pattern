"""NAM 節の構造の検査：ファイル名、ID、ステップ名、環境変数の名前、ランナーのラベル。"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import PurePosixPath

from gha_kit import layout
from gha_kit.findings import Finding
from gha_kit.walk import Context, action_name, all_steps, env_maps, events, finding, jobs, stem, steps, uses_of
from gha_kit.yamlnode import Document, Map, Node, Scalar, Seq, as_map, text_of

KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ID = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
UPPER = re.compile(r"^[A-Z][A-Z0-9_]*$")
STEP_VERBS = (
    "Attest",
    "Build",
    "Check",
    "Comment",
    "Configure",
    "Create",
    "Delete",
    "Deploy",
    "Download",
    "Generate",
    "Install",
    "Log",
    "Publish",
    "Push",
    "Report",
    "Run",
    "Set",
    "Sync",
    "Update",
    "Upload",
    "Verify",
)
STEP_NAMES = {
    "actions/checkout": "Check out repository",
    "actions/setup-node": "Set up Node.js",
    "actions/setup-python": "Set up Python",
    "actions/setup-go": "Set up Go",
    "actions/setup-java": "Set up Java",
    "astral-sh/setup-uv": "Set up uv",
    layout.REPORT_ACTION: "Report run timings",
}
STEP_PREFIXES = {"actions/upload-artifact": "Upload ", "actions/download-artifact": "Download "}
RUNNERS = ("ubuntu-24.04", "ubuntu-24.04-arm", "macos-26", "windows-2025")
SINGLE = re.compile(r"^\$\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}$")
MATRIX_KEY = re.compile(r"^\$\{\{\s*matrix\.([A-Za-z0-9_-]+)\s*\}\}$")
CONTEXT = re.compile(
    r"^(github\.event\.|github\.|inputs\.|matrix\.|secrets\.|vars\.|env\.|runner\.|"
    r"steps\.[^.]+\.outputs\.|needs\.[^.]+\.outputs\.)"
)
TOKENS = ("github.token", "secrets.GITHUB_TOKEN", "inputs.github-token")


def nam01_files(ctx: Context) -> Iterator[Finding]:
    """NAM-01: ファイル名とディレクトリ名は kebab-case、YAML の拡張子は .yml。"""
    named = [(rel, PurePosixPath(rel).stem) for rel in (*ctx.found.workflows, *ctx.found.scripts)]
    named += [(rel, PurePosixPath(rel).parent.name) for rel in ctx.found.actions]
    for rel, name in named:
        if not KEBAB.match(name):
            yield Finding(rel, 1, "NAM-01", f"{name} を kebab-case（小文字・数字・ハイフン）にする")
    for rel in ctx.found.yaml_files():
        if rel.endswith(".yaml"):
            yield Finding(rel, 1, "NAM-01", "YAML の拡張子は .yml にする")


def nam02_ids(ctx: Context) -> Iterator[Finding]:
    """NAM-02: ID は kebab-case、環境変数と secrets は大文字の snake_case、name はファイル名にそろえる。"""
    for doc, root in ctx.workflows():
        if text_of(root.get("name")) != stem(doc.path):
            yield finding("NAM-02", doc, root.key_line("name"), f"ワークフローの name は {stem(doc.path)} にする")
        yield from _interface_ids(doc, root)
        for key, job in jobs(root):
            yield from _job_ids(doc, key, job)
        for _, env in env_maps(root):
            yield from _upper(doc, _keys(env), "環境変数")
    for doc, root in ctx.actions():
        directory = PurePosixPath(doc.path).parent.name
        if text_of(root.get("name")) != directory:
            yield finding("NAM-02", doc, root.key_line("name"), f"composite アクションの name は {directory} にする")
        yield from _ids(doc, _keys(root.get("inputs")) + _keys(root.get("outputs")), "入力・出力")
        yield from _ids(doc, _step_ids(root), "ステップの ID")
        for step in steps(root):
            yield from _upper(doc, _keys(step.get("env")), "環境変数")


def _job_ids(doc: Document, key: Scalar, job: Map) -> Iterator[Finding]:
    yield from _ids(doc, [key], "ジョブの ID")
    if "name" in job.names():
        yield finding("NAM-02", doc, job.key_line("name"), "ジョブに name を書かない（ID が表示名になる）")
    yield from _ids(doc, _keys(job.get("outputs")), "ジョブの出力")
    yield from _ids(doc, _matrix_keys(job), "matrix のキー")
    environment = job.get("environment")
    name = environment.get("name") if isinstance(environment, Map) else environment
    if isinstance(name, Scalar) and not name.text.startswith("${{"):
        yield from _ids(doc, [name], "environment の名前")
    yield from _ids(doc, _step_ids(job), "ステップの ID")


def _step_ids(container: Map) -> list[Scalar]:
    return [step_id for step in steps(container) if (step_id := _scalar(step.get("id")))]


def _interface_ids(doc: Document, root: Map) -> Iterator[Finding]:
    on = events(root)
    for event in ("workflow_call", "workflow_dispatch"):
        detail = as_map(on.get(event)) if on else None
        if detail is not None:
            yield from _ids(doc, _keys(detail.get("inputs")) + _keys(detail.get("outputs")), "入力・出力")
            yield from _upper(doc, _keys(detail.get("secrets")), "secrets")


def _ids(doc: Document, keys: list[Scalar], what: str) -> Iterator[Finding]:
    for key in keys:
        if not ID.match(key.text):
            yield finding("NAM-02", doc, key.line, f"{what} {key.text} を kebab-case にする")


def _upper(doc: Document, keys: list[Scalar], what: str) -> Iterator[Finding]:
    for key in keys:
        if not UPPER.match(key.text):
            yield finding("NAM-02", doc, key.line, f"{what} {key.text} を大文字の snake_case にする")


def _keys(node: Node | None) -> list[Scalar]:
    return [key for key, _ in node.pairs] if isinstance(node, Map) else []


def _scalar(node: Node | None) -> Scalar | None:
    return node if isinstance(node, Scalar) else None


def _matrix_keys(job: Map) -> list[Scalar]:
    strategy = as_map(job.get("strategy"))
    matrix = as_map(strategy.get("matrix")) if strategy else None
    return [key for key in _keys(matrix) if key.text not in ("include", "exclude")]


def nam04_steps(ctx: Context) -> Iterator[Finding]:
    """NAM-04: 全ステップに英語の name。先頭の動詞は語彙表から。決まったアクションには決まった名前。"""
    for doc, step, _ in all_steps(ctx):
        name = text_of(step.get("name"))
        line = step.key_line("name")
        if not name:
            yield finding("NAM-04", doc, step.line, "ステップに name を書く")
            continue
        if not name.isascii() or name.endswith(".") or name.split(" ", 1)[0] not in STEP_VERBS:
            yield finding(
                "NAM-04", doc, line, f"ステップの name は英語で、先頭を {', '.join(STEP_VERBS)} のどれかにする"
            )
        action = action_name(uses_of(step))
        if action in STEP_NAMES and name != STEP_NAMES[action]:
            yield finding("NAM-04", doc, line, f"{action} のステップの name は {STEP_NAMES[action]} にする")
        if action in STEP_PREFIXES and not name.startswith(STEP_PREFIXES[action]):
            yield finding(
                "NAM-04", doc, line, f"{action} のステップの name は {STEP_PREFIXES[action]}<成果物の名前> にする"
            )


def nam05_env_names(ctx: Context) -> Iterator[Finding]:
    """NAM-05: 式1つを渡す環境変数の名前は、コンテキストを除いた残りを大文字の snake_case にしたもの。"""
    for doc, root in ctx.workflows():
        for _, env in env_maps(root):
            yield from _env_names(doc, env)
    for doc, root in ctx.actions():
        for step in steps(root):
            if (step_env := as_map(step.get("env"))) is not None:
                yield from _env_names(doc, step_env)


def _env_names(doc: Document, env: Map) -> Iterator[Finding]:
    for key, value in env.pairs:
        match = SINGLE.match((text_of(value) or "").strip())
        if not match:
            continue
        expression = match[1]
        expected = "GH_TOKEN" if expression in TOKENS else _upper_name(CONTEXT.sub("", expression, count=1))
        if key.text != expected:
            yield finding("NAM-05", doc, key.line, f"${{{{ {expression} }}}} を渡す環境変数の名前は {expected} にする")


def _upper_name(path: str) -> str:
    return path.replace(".", "_").replace("-", "_").upper()


def nam06_runners(ctx: Context) -> Iterator[Finding]:
    """NAM-06: runs-on は版付きのラベルの表から1つ、または表のラベルだけを持つ matrix のキー。"""
    allowed = ", ".join(RUNNERS)
    for doc, root in ctx.workflows():
        for _, job in jobs(root):
            node = job.get("runs-on")
            if node is None:
                continue
            label = text_of(node)
            if label in RUNNERS or (label is not None and _matrix_runners(job, label)):
                continue
            yield finding("NAM-06", doc, job.key_line("runs-on"), f"runs-on には {allowed} のどれか1つを書く")


def _matrix_runners(job: Map, label: str) -> bool:
    match = MATRIX_KEY.match(label.strip())
    strategy = as_map(job.get("strategy"))
    matrix = as_map(strategy.get("matrix")) if strategy else None
    values = matrix.get(match[1]) if match and matrix else None
    return isinstance(values, Seq) and all(text_of(item) in RUNNERS for item in values.items)
