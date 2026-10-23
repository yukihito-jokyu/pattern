"""STR 節の構造の検査：置き場、ファイルとトリガーの対応、スクリプトの切り出し、environment。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import PurePosixPath

from gha_kit import layout
from gha_kit.findings import Finding
from gha_kit.walk import Context, events, finding, is_ci, is_reusable, jobs, scalar_lines, steps, writes
from gha_kit.yamlnode import Document, Map, Node, Scalar, Seq, as_map, text_of

RUN_LINES = 10
PR_EVENTS = ("pull_request", "merge_group")
FORBIDDEN_EVENTS = {"pull_request_target": "OPS-05", "workflow_run": "DEP-03", "repository_dispatch": "DEP-03"}
# STR-02 の表の目的ごとに書いてよいトリガー。PR のトリガーと workflow_call の置き場は別に検査する
LISTED_EVENTS = {
    "ci": ("push",),
    "release": ("push",),
    "deploy": ("push", "workflow_dispatch"),
    "reusable": (),
    "other": ("schedule", "workflow_dispatch"),
}
ENVIRONMENT_SCOPES = ("contents", "deployments", "id-token", "packages", "pages")


def str01_layout(ctx: Context) -> Iterator[Finding]:
    """STR-01: ワークフローは .github/workflows の直下、composite は .github/actions/<名前>/action.yml。"""
    for rel in ctx.found.workflows:
        parts = PurePosixPath(rel).parts
        if len(parts) != 3:
            yield Finding(rel, 1, "STR-01", f"ワークフローは {layout.WORKFLOWS}/ の直下に置く")
    for rel in ctx.found.actions:
        path = PurePosixPath(rel)
        if len(path.parts) != 4:
            yield Finding(rel, 1, "STR-01", f"composite アクションは {layout.ACTIONS}/<名前>/action.yml に置く")
        if path.name != "action.yml":
            yield Finding(rel, 1, "STR-01", "composite アクションのファイル名は action.yml にする")
    for rel in ctx.found.scripts:
        if len(PurePosixPath(rel).parts) != 3:
            yield Finding(rel, 1, "STR-01", f"スクリプトは {layout.SCRIPTS}/ の直下に置く")


def str02_triggers(ctx: Context) -> Iterator[Finding]:
    """STR-02: トリガーとファイルの対応（PR は ci.yml だけ、workflow_call は reusable-*.yml だけ、ほか）。"""
    for doc, root in ctx.workflows():
        on = events(root)
        if on is None:
            yield finding("STR-02", doc, root.key_line("on"), "on: はイベント名をキーにした対応表で書く")
            continue
        names = on.names()
        for event in names:
            line = on.key_line(event)
            if event in FORBIDDEN_EVENTS:
                yield finding(FORBIDDEN_EVENTS[event], doc, line, f"トリガー {event} は使わない")
            if event in PR_EVENTS and not is_ci(doc):
                yield finding(
                    "STR-02", doc, line, f"{event} を持てるのは ci.yml だけ。PR の検証は ci.yml のジョブにする"
                )
        if is_reusable(doc) and names != ["workflow_call"]:
            yield finding("STR-02", doc, on.line, "reusable-*.yml のトリガーは workflow_call だけにする")
        if "workflow_call" in names and not is_reusable(doc):
            yield finding(
                "STR-02", doc, on.key_line("workflow_call"), "workflow_call は reusable-<名前>.yml にだけ書く"
            )
        if "schedule" in names and "workflow_dispatch" not in names:
            yield finding(
                "STR-02", doc, on.key_line("schedule"), "schedule のワークフローには workflow_dispatch も書く"
            )
        yield from _unlisted_triggers(doc, on)
        if is_ci(doc):
            yield from _ci_triggers(doc, on)


def _unlisted_triggers(doc: Document, on: Map) -> Iterator[Finding]:
    purpose = _purpose(doc)
    for event in on.names():
        if event in (*FORBIDDEN_EVENTS, *PR_EVENTS, "workflow_call") or event in LISTED_EVENTS[purpose]:
            continue
        yield finding(
            "STR-02", doc, on.key_line(event), f"トリガー {event} は STR-02 の表の {purpose} の行に無い。表の目的を選ぶ"
        )


def _purpose(doc: Document) -> str:
    name = PurePosixPath(doc.path).name
    if is_ci(doc):
        return "ci"
    if is_reusable(doc):
        return "reusable"
    if name == "release.yml":
        return "release"
    return "deploy" if name.startswith("deploy-") else "other"


def _ci_triggers(doc: Document, on: Map) -> Iterator[Finding]:
    if "pull_request" not in on.names():
        yield finding("STR-02", doc, on.line, "ci.yml には pull_request を書く")
    elif not _is_null(on.get("pull_request")):
        yield finding(
            "STR-02", doc, on.key_line("pull_request"), "ci.yml の pull_request に絞り込み（paths など）を書かない"
        )
    push = as_map(on.get("push"))
    branches = _scalars(push.get("branches")) if push else []
    if push is None or push.names() != ["branches"] or len(branches) != 1:
        yield finding("STR-02", doc, on.key_line("push"), "ci.yml の push は branches に既定のブランチ1つだけを書く")


def _is_null(node: Node | None) -> bool:
    return node is None or (isinstance(node, Scalar) and node.text in ("", "null", "~"))


def _scalars(node: Node | None) -> list[Scalar]:
    return [item for item in node.items if isinstance(item, Scalar)] if isinstance(node, Seq) else []


def str03_anchors(ctx: Context) -> Iterator[Finding]:
    """STR-03: YAML のアンカーとエイリアスで共有しない。共有は composite か再利用ワークフローにする。"""
    for doc in ctx.yaml_docs():
        for line in doc.anchor_lines:
            yield finding(
                "STR-03", doc, line, "アンカー（&名前）で共有しない。composite アクションか再利用ワークフローにする"
            )


def str04_scripts(ctx: Context) -> Iterator[Finding]:
    """STR-04: run の本文は 10 行まで。超えるなら .github/scripts/ に切り出す。"""
    for doc, root in ctx.workflows():
        for _, job in jobs(root):
            for step in steps(job):
                if scalar_lines(step.get("run")) > RUN_LINES:
                    yield finding(
                        "STR-04", doc, step.key_line("run"), f"run が {RUN_LINES} 行を超えた。スクリプトに切り出す"
                    )
    for doc, root in ctx.actions():
        for step in steps(root):
            if scalar_lines(step.get("run")) > RUN_LINES:
                yield finding(
                    "STR-04", doc, step.key_line("run"), f"run が {RUN_LINES} 行を超えた。スクリプトに切り出す"
                )


def str05_environment(ctx: Context) -> Iterator[Finding]:
    """STR-05: デプロイ・公開の書き込み権限を持つジョブには environment を付ける。"""
    for doc, root in ctx.workflows():
        for key, job in jobs(root):
            scopes = [scope for scope in writes(job) if scope in ENVIRONMENT_SCOPES]
            if scopes and job.get("environment") is None:
                yield finding(
                    "STR-05", doc, key.line, f"{', '.join(scopes)} の書き込みを持つジョブには environment を付ける"
                )
            environment = job.get("environment")
            name = text_of(environment.get("name")) if isinstance(environment, Map) else text_of(environment)
            if environment is not None and not name:
                yield finding("STR-05", doc, job.key_line("environment"), "environment には名前を書く")
