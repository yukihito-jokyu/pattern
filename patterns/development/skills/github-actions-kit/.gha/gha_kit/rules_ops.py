"""OPS・PROC・TOOL 節の構造の検査：report、secrets、版の引用、schedule、permissions、Dependabot、抑止。"""

from __future__ import annotations

import re
from collections.abc import Iterator

from gha_kit import layout
from gha_kit.findings import Finding
from gha_kit.walk import Context, action_name, all_steps, events, finding, is_ci, jobs, steps, uses_of
from gha_kit.yamlnode import Document, Map, Node, Scalar, Seq, as_map, as_seq, text_of

REPORT = "report"
REPORT_IF = "${{ !cancelled() }}"
REPORT_RUNNER = "ubuntu-24.04"
REPORT_PERMISSIONS = [("actions", "read"), ("contents", "read"), ("pull-requests", "write")]
REPORT_CHECKOUT = [("persist-credentials", "false"), ("sparse-checkout", ".github/actions/run-report")]
REPORT_NEEDS = "${{ toJSON(needs) }}"
NUMERIC = re.compile(r"^\d+(\.\d+)*$")
MINUTE = re.compile(r"^([1-9]|[1-5][0-9])$")
TIMEZONE = re.compile(r"^[A-Za-z_]+(/[A-Za-z0-9_+-]+)+$|^UTC$")
DEPENDABOT_DIRECTORIES = ["/", "/.github/actions/*"]
SUPPRESSIONS = re.compile(
    r"#\s*zizmor:\s*ignore|#\s*yamllint\s+disable|#\s*shellcheck\s+disable|#\s*noqa|#\s*ruff:|#\s*type:\s*ignore"
    r"|#\s*mypy:|#\s*pragma:\s*no\s*cover|#\s*fmt:\s*(off|skip)|unittest\.skip|skipTest\("
)


def ops01_report(ctx: Context) -> Iterator[Finding]:
    """OPS-01: ci.yml の最後のジョブは決まった形の report。run-report はそこだけで使う。"""
    for doc, root in ctx.workflows():
        job_ids = [key.text for key, _ in jobs(root)]
        if not is_ci(doc):
            for key, job in jobs(root):
                if key.text == REPORT or any(uses_of(step) == layout.REPORT_ACTION for step in steps(job)):
                    yield finding("OPS-01", doc, key.line, "report ジョブと run-report は ci.yml だけに置く")
            continue
        if not job_ids or job_ids[-1] != REPORT:
            yield finding("OPS-01", doc, root.key_line("jobs"), "ci.yml の最後のジョブを report にする")
            continue
        all_jobs = as_map(root.get("jobs"))
        report = as_map(all_jobs.get(REPORT)) if all_jobs else None
        if report is not None:
            yield from _report(doc, report, sorted(job_ids[:-1]))
    for doc, step, composite in all_steps(ctx):
        if composite and uses_of(step) == layout.REPORT_ACTION:
            yield finding("OPS-01", doc, step.line, "run-report は ci.yml の report ジョブだけで使う")


def _report(doc: Document, job: Map, others: list[str]) -> Iterator[Finding]:
    expected = {"if": REPORT_IF, "runs-on": REPORT_RUNNER, "timeout-minutes": "5"}
    for key, value in expected.items():
        if text_of(job.get(key)) != value:
            yield finding("OPS-01", doc, job.key_line(key), f"report ジョブの {key} は {value} にする")
    needs = as_seq(job.get("needs"))
    if ([text_of(item) for item in needs.items] if needs else []) != others:
        yield finding(
            "PROC-02", doc, job.key_line("needs"), f"report の needs を ci.yml のほかの全ジョブ {others} にする"
        )
    if _pairs(job.get("permissions")) != REPORT_PERMISSIONS:
        yield finding(
            "OPS-01",
            doc,
            job.key_line("permissions"),
            "report の permissions は actions: read、contents: read、pull-requests: write",
        )
    report_steps = list(steps(job))
    shape = [action_name(uses_of(step)) for step in report_steps]
    if shape != ["actions/checkout", layout.REPORT_ACTION]:
        yield finding(
            "OPS-01", doc, job.key_line("steps"), "report のステップは actions/checkout と run-report の2つにする"
        )
        return
    if _pairs(report_steps[0].get("with")) != REPORT_CHECKOUT:
        yield finding(
            "OPS-01",
            doc,
            report_steps[0].line,
            "report の checkout は persist-credentials と sparse-checkout だけを書く",
        )
    if _pairs(report_steps[1].get("with")) != [("needs", REPORT_NEEDS)]:
        yield finding("OPS-01", doc, report_steps[1].line, f"run-report の with は needs: {REPORT_NEEDS} だけにする")


def _pairs(node: Node | None) -> list[tuple[str, str | None]]:
    return [(key.text, text_of(value)) for key, value in node.pairs] if isinstance(node, Map) else []


def ops02_secrets(ctx: Context) -> Iterator[Finding]:
    """OPS-02: secrets はステップの env か with だけ。ワークフローとジョブの env に置かず、inherit しない。"""
    for doc, root in ctx.workflows():
        yield from _secret_env(doc, root, "ワークフロー")
        for key, job in jobs(root):
            yield from _secret_env(doc, job, "ジョブ")
            if text_of(job.get("secrets")) == "inherit":
                yield finding(
                    "OPS-02", doc, job.key_line("secrets"), f"ジョブ {key.text} に secrets: inherit を書かない"
                )


def _secret_env(doc: Document, owner: Map, what: str) -> Iterator[Finding]:
    env = as_map(owner.get("env"))
    for key, value in env.pairs if env else ():
        if "secrets." in (text_of(value) or ""):
            yield finding("OPS-02", doc, key.line, f"{what}の env に secrets を置かない。使うステップの env に書く")


def ops03_versions(ctx: Context) -> Iterator[Finding]:
    """OPS-03: -version で終わる with の値と matrix の値のうち、数字と . だけのものは二重引用符で囲む。"""
    for doc, step, _ in all_steps(ctx):
        with_ = as_map(step.get("with"))
        for key, value in with_.pairs if with_ else ():
            if key.text.endswith("-version"):
                yield from _quoted(doc, value)
    for doc, root in ctx.workflows():
        for _, job in jobs(root):
            strategy = as_map(job.get("strategy"))
            matrix = as_map(strategy.get("matrix")) if strategy else None
            for _, value in matrix.pairs if matrix else ():
                yield from _quoted(doc, value)


def _quoted(doc: Document, node: Node) -> Iterator[Finding]:
    if isinstance(node, Scalar):
        if node.style != '"' and NUMERIC.match(node.text):
            yield finding("OPS-03", doc, node.line, f'版の数値 {node.text} は "{node.text}" と二重引用符で囲む')
    elif isinstance(node, Seq):
        for item in node.items:
            yield from _quoted(doc, item)
    else:
        for _, value in node.pairs:
            yield from _quoted(doc, value)


def ops04_schedule(ctx: Context) -> Iterator[Finding]:
    """OPS-04: schedule の各要素に cron と timezone。cron の分は 1〜59 の数字1つ。"""
    for doc, root in ctx.workflows():
        on = events(root)
        schedule = as_seq(on.get("schedule")) if on else None
        for item in schedule.items if schedule else ():
            entry = as_map(item)
            cron = text_of(entry.get("cron")) if entry else None
            zone = text_of(entry.get("timezone")) if entry else None
            line = item.line
            if not cron or not MINUTE.match(cron.split()[0]):
                yield finding("OPS-04", doc, line, "cron の分は 1〜59 の数字1つにする（毎時0分を避ける）")
            if not zone or not TIMEZONE.match(zone):
                yield finding("OPS-04", doc, line, "schedule の要素に timezone（IANA の名前。既定は Asia/Tokyo）を書く")


def ops06_permissions(ctx: Context) -> Iterator[Finding]:
    """OPS-06: ワークフローの permissions は {}。全ジョブに permissions を書き、値は read か write。"""
    for doc, root in ctx.workflows():
        permissions = root.get("permissions")
        if not isinstance(permissions, Map) or permissions.pairs:
            yield finding("OPS-06", doc, root.key_line("permissions"), "ワークフローの先頭に permissions: {} を書く")
        for key, job in jobs(root):
            job_permissions = job.get("permissions")
            if not isinstance(job_permissions, Map):
                yield finding("OPS-06", doc, key.line, f"ジョブ {key.text} に permissions をスコープごとに書く")
                continue
            for scope, value in job_permissions.pairs:
                if text_of(value) not in ("read", "write"):
                    yield finding(
                        "OPS-06", doc, scope.line, f"{scope.text} の値は read か write にする（要らないなら書かない）"
                    )


def proc03_dependabot(ctx: Context) -> Iterator[Finding]:
    """PROC-03: dependabot.yml に github-actions の項目を決まった形で置く。"""
    if not ctx.found.workflows and not ctx.found.actions:
        return
    doc = ctx.docs.get(layout.DEPENDABOT)
    if doc is None:
        yield Finding(
            layout.DEPENDABOT,
            1,
            "PROC-03",
            "dependabot.yml に github-actions の項目を置く（見本は references/examples）",
        )
        return
    root = as_map(doc.root)
    updates = as_seq(root.get("updates")) if root else None
    entries = [entry for entry in (as_map(item) for item in updates.items) if entry] if updates else []
    actions = [entry for entry in entries if text_of(entry.get("package-ecosystem")) == "github-actions"]
    if len(actions) != 1:
        yield finding("PROC-03", doc, 1, "package-ecosystem: github-actions の項目を1つ置く")
        return
    yield from _dependabot_entry(doc, actions[0])


def _dependabot_entry(doc: Document, entry: Map) -> Iterator[Finding]:
    directories = as_seq(entry.get("directories"))
    if ([text_of(item) for item in directories.items] if directories else []) != DEPENDABOT_DIRECTORIES:
        yield finding("PROC-03", doc, entry.line, f"directories は {DEPENDABOT_DIRECTORIES} にする")
    schedule = as_map(entry.get("schedule"))
    if text_of(schedule.get("interval") if schedule else None) != "weekly":
        yield finding("PROC-03", doc, entry.key_line("schedule"), "schedule.interval は weekly にする")
    cooldown = as_map(entry.get("cooldown"))
    if text_of(cooldown.get("default-days") if cooldown else None) != "7":
        yield finding("PROC-03", doc, entry.key_line("cooldown"), "cooldown.default-days は 7 にする")
    groups = as_map(entry.get("groups"))
    patterns = [_pairs_of_patterns(value) for _, value in groups.pairs] if groups else []
    if patterns != [["*"]]:
        yield finding("PROC-03", doc, entry.key_line("groups"), 'groups には patterns が ["*"] のグループを1つだけ書く')


def _pairs_of_patterns(node: Node) -> list[str | None]:
    group = as_map(node)
    patterns = as_seq(group.get("patterns")) if group else None
    return [text_of(item) for item in patterns.items] if patterns else []


def tool03_suppressions(ctx: Context) -> Iterator[Finding]:
    """TOOL-03: 抑止コメントで検査を黙らせない。"""
    sources = [(doc.path, doc.lines) for doc in ctx.yaml_docs()] + list(ctx.scripts.items())
    for path, lines in sources:
        for number, text in enumerate(lines, 1):
            if SUPPRESSIONS.search(text):
                yield Finding(path, number, "TOOL-03", "抑止コメントを書かない。指摘の原因を直す")
