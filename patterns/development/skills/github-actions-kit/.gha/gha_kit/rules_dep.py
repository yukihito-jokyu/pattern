"""DEP 節の構造の検査：呼び出しの向き、公開面（inputs と outputs）、PR での書き込み、参照の固定。"""

from __future__ import annotations

import re
from collections.abc import Iterator

from gha_kit import layout
from gha_kit.findings import Finding
from gha_kit.walk import Context, all_steps, events, finding, is_ci, is_reusable, jobs, uses_of, writes
from gha_kit.yamlnode import Document, Map, Node, as_map, text_of

LOCAL_REUSABLE = re.compile(r"^\./\.github/workflows/reusable-[a-z0-9-]+\.yml$")
REMOTE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(/[A-Za-z0-9_./-]+)?@[0-9a-f]{40}$")
PIN_COMMENT = re.compile(r"@[0-9a-f]{40} # v\d+\.\d+\.\d+$")
DOCKER = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-f]{64}$")
INPUT_TYPES = {
    "workflow_call": ("boolean", "number", "string"),
    "workflow_dispatch": ("boolean", "choice", "environment", "number", "string"),
}


def dep01_direction(ctx: Context) -> Iterator[Finding]:
    """DEP-01: ジョブの uses は reusable-*.yml か固定した外部の再利用ワークフロー。入れ子にしない。"""
    for doc, root in ctx.workflows():
        for key, job in jobs(root):
            target = text_of(job.get("uses"))
            if target is None:
                continue
            if is_reusable(doc):
                yield finding("DEP-01", doc, job.key_line("uses"), "reusable-*.yml から再利用ワークフローを呼ばない")
            elif not (LOCAL_REUSABLE.match(target) or REMOTE.match(target)):
                yield finding(
                    "DEP-01", doc, key.line, f"ジョブの uses は {layout.WORKFLOWS}/reusable-<名前>.yml にする"
                )
    for doc, step, composite in all_steps(ctx):
        if composite and uses_of(step).startswith("./"):
            yield finding(
                "DEP-01", doc, step.key_line("uses"), "composite アクションから別のローカルのアクションを呼ばない"
            )


def dep02_interface(ctx: Context) -> Iterator[Finding]:
    """DEP-02: inputs・outputs・secrets の定義に description と required（と type・default）を書く。"""
    for doc, root in ctx.workflows():
        on = events(root)
        for event in ("workflow_call", "workflow_dispatch"):
            detail = as_map(on.get(event)) if on else None
            if detail is None:
                continue
            yield from _inputs(doc, as_map(detail.get("inputs")), INPUT_TYPES[event])
            if event == "workflow_call":
                yield from _outputs(doc, as_map(detail.get("outputs")))
                yield from _secrets(doc, as_map(detail.get("secrets")))
    for doc, root in ctx.actions():
        yield from _inputs(doc, as_map(root.get("inputs")), ())
        yield from _outputs(doc, as_map(root.get("outputs")))


def _inputs(doc: Document, inputs: Map | None, types: tuple[str, ...]) -> Iterator[Finding]:
    required = ("description", "required", *(("type",) if types else ()))
    for key, value in inputs.pairs if inputs else ():
        spec = as_map(value) or Map((), key.line)
        names = spec.names()
        missing = [name for name in required if name not in names]
        if missing:
            yield finding("DEP-02", doc, key.line, f"入力 {key.text} に {', '.join(missing)} を書く")
            continue
        kind = text_of(spec.get("type"))
        if types and kind not in types:
            yield finding(
                "DEP-02", doc, spec.key_line("type"), f"入力 {key.text} の type は {', '.join(types)} のどれか"
            )
        if text_of(spec.get("required")) == "false" and "default" not in names:
            yield finding("DEP-02", doc, key.line, f"required: false の入力 {key.text} には default を書く")
        if kind == "choice" and "options" not in names:
            yield finding("DEP-02", doc, key.line, f"choice の入力 {key.text} には options を書く")


def _outputs(doc: Document, outputs: Map | None) -> Iterator[Finding]:
    for key, value in outputs.pairs if outputs else ():
        spec = as_map(value)
        missing = [name for name in ("description", "value") if not spec or name not in spec.names()]
        if missing:
            yield finding("DEP-02", doc, key.line, f"出力 {key.text} に {', '.join(missing)} を書く")


def _secrets(doc: Document, secrets: Map | None) -> Iterator[Finding]:
    for key, value in secrets.pairs if secrets else ():
        spec = as_map(value)
        missing = [name for name in ("description", "required") if not spec or name not in spec.names()]
        if missing:
            yield finding("DEP-02", doc, key.line, f"secret {key.text} に {', '.join(missing)} を書く")


def dep05_side_effects(ctx: Context) -> Iterator[Finding]:
    """DEP-05: ci.yml で書き込み権限を持てるのは report ジョブの pull-requests: write だけ。"""
    for doc, root in ctx.workflows():
        if not is_ci(doc):
            continue
        for key, job in jobs(root):
            allowed = ["pull-requests"] if key.text == "report" else []
            extra = [scope for scope in writes(job) if scope not in allowed]
            if extra:
                yield finding(
                    "DEP-05", doc, key.line, f"ci.yml のジョブ {key.text} に書き込み権限 {', '.join(extra)} を付けない"
                )


def dep06_pinning(ctx: Context) -> Iterator[Finding]:
    """DEP-06: 外部のアクションは 40 桁の SHA と `# vX.Y.Z` のコメントで固定する。"""
    for doc, step, _ in all_steps(ctx):
        yield from _pin(doc, step.get("uses"), step)
    for doc, root in ctx.workflows():
        for _, job in jobs(root):
            target = text_of(job.get("uses"))
            if target and not target.startswith("./"):
                yield from _pin(doc, job.get("uses"), job)


def _pin(doc: Document, node: Node | None, owner: Map) -> Iterator[Finding]:
    target = text_of(node)
    if not target or target.startswith("./"):
        return
    line = owner.key_line("uses")
    if target.startswith("docker://"):
        if not DOCKER.match(target):
            yield finding("DEP-06", doc, line, "docker:// のイメージは @sha256:<digest> で固定する")
        return
    if not REMOTE.match(target):
        yield finding("DEP-06", doc, line, f"{target} を 40 桁のコミット SHA で固定する（gha pin で解決する）")
    elif not PIN_COMMENT.search(doc.line_text(line).rstrip()):
        yield finding("DEP-06", doc, line, "SHA の後ろに ` # vX.Y.Z`（固定したタグ）のコメントを書く")
