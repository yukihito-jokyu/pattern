"""検査の全体：構造の検査（policy）と外部ツールを回し、指摘を1つの一覧にする。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from gha_kit import layout, policy, proc, targets, tools, yamlnode
from gha_kit.findings import Finding
from gha_kit.proc import Runner


def run(root: Path, paths: Sequence[str] = (), online: bool = False, runner: Runner = proc.run) -> list[Finding]:
    """paths を省くと `.github/` の下の全部を検査する。構造の検査は全ファイルを読み、指定のファイルの指摘だけを返す。

    paths を省いたときは、まだ無い `dependabot.yml` への指摘（PROC-03）も返す。
    """
    found = targets.discover(root)
    chosen = targets.select(found, paths)
    docs = {rel: yamlnode.load(root, rel) for rel in found.yaml_files()}
    selected = set(chosen.all_files()) | (set() if paths else {layout.DEPENDABOT})
    findings = [finding for finding in policy.check(root, found, docs) if finding.path in selected]
    findings += tools.yamllint(root, chosen.yaml_files(), runner)
    findings += tools.actionlint(root, chosen.workflows, runner)
    findings += tools.shellcheck(root, chosen.scripts, runner)
    findings += tools.zizmor(root, chosen.yaml_files(), runner, online)
    return sorted(set(findings))
