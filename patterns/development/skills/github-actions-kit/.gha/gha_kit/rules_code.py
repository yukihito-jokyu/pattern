"""CODE 節の構造の検査：キーの順と YAML の形、matrix、ファイルの1行目。"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence

from gha_kit.findings import Finding
from gha_kit.walk import Context, all_steps, events, finding, is_expression, is_reusable, jobs, scalar_lines
from gha_kit.yamlnode import Document, Map, Node, Scalar, Seq, as_map, text_of

WORKFLOW_KEYS = ("name", "run-name", "on", "permissions", "concurrency", "defaults", "env", "jobs")
EVENT_KEYS = ("pull_request", "merge_group", "push", "schedule", "workflow_dispatch", "workflow_call")
JOB_KEYS = (
    "needs",
    "if",
    "uses",
    "runs-on",
    "timeout-minutes",
    "environment",
    "permissions",
    "strategy",
    "with",
    "secrets",
    "container",
    "services",
    "env",
    "outputs",
    "steps",
)
STEP_KEYS = ("name", "id", "if", "uses", "with", "working-directory", "shell", "env", "run")
ACTION_KEYS = ("name", "description", "inputs", "outputs", "runs")
INPUT_KEYS = ("description", "required", "type", "default", "options")
OUTPUT_KEYS = ("description", "value")
SORTED_MAPS = ("env", "with", "permissions")
LIST_KEYS = ("branches", "branches-ignore", "tags", "tags-ignore", "paths", "paths-ignore")
HEADER = re.compile(r"^# \S")
HEADER_FILE_NAME = re.compile(r"[\w.-]+\.(?:ya?ml|md|py|sh|json|toml|lock|txt)(?![A-Za-z0-9])")
REUSABLE_HEADER = "# 呼ばれると、"
TRIGGER_HEADER = "で、"


def code01_shape(ctx: Context) -> Iterator[Finding]:
    """CODE-01: キーの順、if の ${{ }}、列の書き方、アルファベット順、run の書き方。"""
    for doc, root in ctx.workflows():
        yield from _order(doc, root, WORKFLOW_KEYS, "ワークフロー")
        on = events(root)
        if on is not None:
            yield from _order(doc, on, (*EVENT_KEYS, *sorted(set(on.names()) - set(EVENT_KEYS))), "on: のイベント")
            yield from _event_lists(doc, on)
            for event in ("workflow_call", "workflow_dispatch"):
                yield from _definitions(doc, as_map(on.get(event)))
        yield from _sorted_maps(doc, root)
        for _, job in jobs(root):
            yield from _order(doc, job, JOB_KEYS, "ジョブ")
            yield from _condition(doc, job)
            yield from _needs(doc, job)
            yield from _sorted_maps(doc, job)
    for doc, root in ctx.actions():
        yield from _order(doc, root, ACTION_KEYS, "composite アクション")
        yield from _definitions(doc, root)
    for doc, step, _ in all_steps(ctx):
        yield from _order(doc, step, STEP_KEYS, "ステップ")
        yield from _condition(doc, step)
        yield from _sorted_maps(doc, step)
        yield from _run_style(doc, step)


def _order(doc: Document, node: Map, order: Sequence[str], what: str) -> Iterator[Finding]:
    present = [name for name in node.names() if name in order]
    expected = sorted(present, key=order.index)
    if present != expected:
        yield finding("CODE-01", doc, node.line, f"{what}のキーは {', '.join(expected)} の順に書く")


def _event_lists(doc: Document, on: Map) -> Iterator[Finding]:
    for _, detail in on.pairs:
        if isinstance(detail, Map):
            for key, value in detail.pairs:
                if key.text in LIST_KEYS and not isinstance(value, Seq):
                    yield finding("CODE-01", doc, key.line, f"{key.text} は1件でもブロックの列（- 値）で書く")


def _definitions(doc: Document, owner: Map | None) -> Iterator[Finding]:
    if owner is None:
        return
    for section, order in (("inputs", INPUT_KEYS), ("outputs", OUTPUT_KEYS), ("secrets", INPUT_KEYS)):
        definitions = as_map(owner.get(section))
        for key, value in definitions.pairs if definitions else ():
            if isinstance(value, Map):
                yield from _order(doc, value, order, f"{section} の {key.text} ")


def _condition(doc: Document, node: Map) -> Iterator[Finding]:
    condition = node.get("if")
    if condition is not None and not is_expression(text_of(condition)):
        yield finding("CODE-01", doc, node.key_line("if"), "if: の値は全体を ${{ }} で囲む")


def _needs(doc: Document, job: Map) -> Iterator[Finding]:
    needs = job.get("needs")
    if needs is None:
        return
    if not isinstance(needs, Seq):
        yield finding("CODE-01", doc, job.key_line("needs"), "needs は1件でもブロックの列（- ジョブ）で書く")
        return
    names = [text_of(item) or "" for item in needs.items]
    if names != sorted(names):
        yield finding("CODE-01", doc, job.key_line("needs"), "needs の要素はアルファベット順に書く")


def _sorted_maps(doc: Document, owner: Map) -> Iterator[Finding]:
    for section in SORTED_MAPS:
        mapping = as_map(owner.get(section))
        names = mapping.names() if mapping else []
        if names != sorted(names):
            yield finding("CODE-01", doc, owner.key_line(section), f"{section} のキーはアルファベット順に書く")


def _run_style(doc: Document, step: Map) -> Iterator[Finding]:
    run = step.get("run")
    if not isinstance(run, Scalar):
        return
    lines = scalar_lines(run)
    if lines == 1 and run.style in ("|", ">"):
        yield finding("CODE-01", doc, step.key_line("run"), "1行の run はブロック（|）にせず1行で書く")
    if lines > 1 and run.style != "|":
        yield finding("CODE-01", doc, step.key_line("run"), "2行以上の run は | のブロックで書く")


def code02_matrix(ctx: Context) -> Iterator[Finding]:
    """CODE-02: matrix には fail-fast: false。各キーの値は2つ以上の列。"""
    for doc, root in ctx.workflows():
        for _, job in jobs(root):
            strategy = as_map(job.get("strategy"))
            matrix = strategy.get("matrix") if strategy else None
            if strategy is None or matrix is None:
                continue
            if text_of(strategy.get("fail-fast")) != "false":
                yield finding("CODE-02", doc, strategy.line, "matrix を書くジョブには strategy.fail-fast: false を書く")
            yield from _matrix_values(doc, matrix)


def _matrix_values(doc: Document, matrix: Node) -> Iterator[Finding]:
    if not isinstance(matrix, Map):
        return
    for key, value in matrix.pairs:
        if key.text in ("include", "exclude") or is_expression(text_of(value)):
            continue
        if not isinstance(value, Seq) or len(value.items) < 2:
            yield finding(
                "CODE-02", doc, key.line, f"matrix の {key.text} は値を2つ以上の列で書く（1つなら matrix にしない）"
            )


def code03_header(ctx: Context) -> Iterator[Finding]:
    """CODE-03: ファイルの1行目は `# <目的を1文>`。ワークフローは表の形にし、どのファイルにも名前を書かない。"""
    workflows = {doc.path: is_reusable(doc) for doc, _ in ctx.workflows()}
    for doc in ctx.yaml_docs():
        line = doc.line_text(1)
        if not HEADER.match(line):
            yield finding("CODE-03", doc, 1, "1行目に `# <このファイルの目的を1文>` を書く")
            continue
        if HEADER_FILE_NAME.search(line):
            yield finding("CODE-03", doc, 1, "1行目にファイル名（呼び出し元など）を書かず、成果だけを書く")
        if workflows.get(doc.path) and not line.startswith(REUSABLE_HEADER):
            yield finding("CODE-03", doc, 1, f"再利用ワークフローの1行目は `{REUSABLE_HEADER}<成果>` にする")
        elif workflows.get(doc.path) is False and TRIGGER_HEADER not in line:
            yield finding("CODE-03", doc, 1, f"ワークフローの1行目は `# <トリガー>{TRIGGER_HEADER}<成果>` にする")
