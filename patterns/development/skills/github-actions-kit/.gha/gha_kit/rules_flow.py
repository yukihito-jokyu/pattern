"""ERR・STATE・ASYNC 節の構造の検査：シェル、式の埋め込み、データの受け渡し、成果物、concurrency、時間の上限。"""

from __future__ import annotations

import re
from collections.abc import Iterator

from gha_kit.findings import Finding
from gha_kit.walk import Context, action_name, all_steps, finding, is_ci, is_reusable, jobs, stem, steps, uses_of
from gha_kit.yamlnode import Document, Map, as_map, text_of

CI_GROUP = "${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}"
CI_CANCEL = "${{ github.event_name == 'pull_request' }}"
OTHER_GROUP = "${{ github.workflow }}"
TIMEOUT = "10"
REPORT_TIMEOUT = "5"
TRAILING_COMMENT = re.compile(r"\s#\s*\S")
SWALLOWED = re.compile(r"\|\|\s*(?:true|:)(?![\w-])|(?<![\w-])set\s+\+e(?![\w-])")
NO_CACHE = {
    "astral-sh/setup-uv": ("enable-cache", "false"),
    "actions/setup-go": ("cache", "false"),
    "actions/setup-node": ("package-manager-cache", "false"),
}
NO_CACHE_KEY = {"actions/setup-node": "cache", "actions/setup-python": "cache"}


def err01_shell(ctx: Context) -> Iterator[Finding]:
    """ERR-01: defaults.run.shell: bash、composite の run には shell: bash。失敗を握りつぶさない。"""
    for doc, root in ctx.workflows():
        defaults = as_map(root.get("defaults"))
        run = as_map(defaults.get("run")) if defaults else None
        if text_of(run.get("shell") if run else None) != "bash":
            yield finding("ERR-01", doc, root.key_line("defaults"), "ワークフローに defaults.run.shell: bash を書く")
        for _, job in jobs(root):
            for key in ("defaults", "continue-on-error"):
                if key in job.names():
                    yield finding("ERR-01", doc, job.key_line(key), f"ジョブに {key} を書かない")
    for doc, step, composite in all_steps(ctx):
        yield from _step_errors(doc, step, composite)


def _step_errors(doc: Document, step: Map, composite: bool) -> Iterator[Finding]:
    if "continue-on-error" in step.names():
        yield finding("ERR-01", doc, step.key_line("continue-on-error"), "ステップに continue-on-error を書かない")
    if SWALLOWED.search(text_of(step.get("run")) or ""):
        yield finding("ERR-01", doc, step.key_line("run"), "run で失敗を握りつぶさない（|| true、|| :、set +e）")
    shell = text_of(step.get("shell"))
    if composite and "run" in step.names() and shell != "bash":
        yield finding("ERR-01", doc, step.line, "composite アクションの run のステップには shell: bash を書く")
    if not composite and shell is not None:
        yield finding(
            "ERR-01", doc, step.key_line("shell"), "ワークフローのステップに shell を書かない（defaults に従う）"
        )


def err02_expressions(ctx: Context) -> Iterator[Finding]:
    """ERR-02: run と github-script の script に ${{ を書かない。値は env で渡す。"""
    for doc, step, _ in all_steps(ctx):
        body = text_of(step.get("run"))
        line = step.key_line("run")
        if action_name(uses_of(step)) == "actions/github-script":
            with_ = as_map(step.get("with"))
            body = text_of(with_.get("script")) if with_ else None
            line = with_.key_line("script") if with_ else step.line
        if body and "${{" in body:
            yield finding("ERR-02", doc, line, '本文に ${{ }} を書かない。値は env に入れて "$NAME" で読む')


def state01_env_file(ctx: Context) -> Iterator[Finding]:
    """STATE-01: $GITHUB_ENV に書かない。ステップの間は $GITHUB_OUTPUT、ジョブの間は outputs で渡す。"""
    for doc, step, _ in all_steps(ctx):
        if "GITHUB_ENV" in (text_of(step.get("run")) or ""):
            yield finding(
                "STATE-01", doc, step.key_line("run"), "$GITHUB_ENV に書かない。$GITHUB_OUTPUT と outputs で渡す"
            )


def state02_artifacts(ctx: Context) -> Iterator[Finding]:
    """STATE-02: 成果物には retention-days と if-no-files-found: error。リリースとデプロイではキャッシュを切る。"""
    for doc, step, _ in all_steps(ctx):
        if action_name(uses_of(step)) == "actions/upload-artifact":
            with_ = as_map(step.get("with"))
            if with_ is None or "retention-days" not in with_.names():
                yield finding("STATE-02", doc, step.line, "upload-artifact に retention-days を書く")
            if text_of(with_.get("if-no-files-found") if with_ else None) != "error":
                yield finding("STATE-02", doc, step.line, "upload-artifact に if-no-files-found: error を書く")
    for doc, root in ctx.workflows():
        if stem(doc.path) == "release" or stem(doc.path).startswith("deploy-"):
            for _, job in jobs(root):
                for step in steps(job):
                    yield from _no_cache(doc, step)


def _no_cache(doc: Document, step: Map) -> Iterator[Finding]:
    action = action_name(uses_of(step))
    with_ = as_map(step.get("with"))
    if action == "actions/cache":
        yield finding("STATE-02", doc, step.line, "リリースとデプロイのワークフローでは actions/cache を使わない")
    if action in NO_CACHE:
        key, value = NO_CACHE[action]
        if text_of(with_.get(key) if with_ else None) != value:
            yield finding("STATE-02", doc, step.line, f"リリースとデプロイでは {action} に {key}: {value} を書く")
    if action in NO_CACHE_KEY and with_ is not None and NO_CACHE_KEY[action] in with_.names():
        yield finding("STATE-02", doc, with_.key_line("cache"), f"リリースとデプロイでは {action} に cache を書かない")


def async01_concurrency(ctx: Context) -> Iterator[Finding]:
    """ASYNC-01: concurrency はワークフローの種類ごとに決まった値。ジョブには書かない。"""
    for doc, root in ctx.workflows():
        for _, job in jobs(root):
            if "concurrency" in job.names():
                yield finding("ASYNC-01", doc, job.key_line("concurrency"), "ジョブに concurrency を書かない")
        line = root.key_line("concurrency")
        if is_reusable(doc):
            if "concurrency" in root.names():
                yield finding("ASYNC-01", doc, line, "reusable-*.yml に concurrency を書かない（呼ぶ側に従う）")
            continue
        group, cancel = (CI_GROUP, CI_CANCEL) if is_ci(doc) else (OTHER_GROUP, "false")
        concurrency = as_map(root.get("concurrency"))
        actual = (
            (text_of(concurrency.get("group")), text_of(concurrency.get("cancel-in-progress"))) if concurrency else None
        )
        if actual != (group, cancel):
            yield finding("ASYNC-01", doc, line, f"concurrency は group: {group}、cancel-in-progress: {cancel} にする")


def async02_timeout(ctx: Context) -> Iterator[Finding]:
    """ASYNC-02: runs-on を持つジョブに timeout-minutes。report は 5、ほかは 10。違う値なら行末に理由。"""
    for doc, root in ctx.workflows():
        for key, job in jobs(root):
            if "runs-on" not in job.names():
                continue
            value = text_of(job.get("timeout-minutes"))
            line = job.key_line("timeout-minutes")
            report = is_ci(doc) and key.text == "report"
            if value is None:
                yield finding("ASYNC-02", doc, key.line, "runs-on を持つジョブに timeout-minutes を書く")
            elif report and value != REPORT_TIMEOUT:
                yield finding("ASYNC-02", doc, line, f"report ジョブの timeout-minutes は {REPORT_TIMEOUT} にする")
            elif not report and value != TIMEOUT and not TRAILING_COMMENT.search(doc.line_text(line)):
                yield finding(
                    "ASYNC-02", doc, line, f"timeout-minutes を {TIMEOUT} 以外にするなら、行末に # 理由 を書く"
                )
    for doc, step, _ in all_steps(ctx):
        if "timeout-minutes" in step.names():
            yield finding("ASYNC-02", doc, step.key_line("timeout-minutes"), "ステップに timeout-minutes を書かない")
