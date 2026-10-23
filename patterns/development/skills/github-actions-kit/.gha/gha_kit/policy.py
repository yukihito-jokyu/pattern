"""構造の検査。ルールごとの検査関数を RULES の表に並べて回す。

検査関数は `rules_<節>.py` に1ルール1関数で置き、ここの表に足す（ルールを足す手順は architecture.md の6章）。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from pathlib import Path

from gha_kit import rules_code, rules_dep, rules_flow, rules_nam, rules_ops, rules_str
from gha_kit.findings import Finding
from gha_kit.targets import Targets
from gha_kit.walk import Context
from gha_kit.yamlnode import Document

Check = Callable[[Context], Iterator[Finding]]
RULES: tuple[Check, ...] = (
    rules_str.str01_layout,
    rules_str.str02_triggers,
    rules_str.str03_anchors,
    rules_str.str04_scripts,
    rules_str.str05_environment,
    rules_dep.dep01_direction,
    rules_dep.dep02_interface,
    rules_dep.dep05_side_effects,
    rules_dep.dep06_pinning,
    rules_nam.nam01_files,
    rules_nam.nam02_ids,
    rules_nam.nam04_steps,
    rules_nam.nam05_env_names,
    rules_nam.nam06_runners,
    rules_code.code01_shape,
    rules_code.code02_matrix,
    rules_code.code03_header,
    rules_flow.err01_shell,
    rules_flow.err02_expressions,
    rules_flow.state01_env_file,
    rules_flow.state02_artifacts,
    rules_flow.async01_concurrency,
    rules_flow.async02_timeout,
    rules_ops.ops01_report,
    rules_ops.ops02_secrets,
    rules_ops.ops03_versions,
    rules_ops.ops04_schedule,
    rules_ops.ops06_permissions,
    rules_ops.proc03_dependabot,
    rules_ops.tool03_suppressions,
)


def check(root: Path, found: Targets, docs: Mapping[str, Document]) -> list[Finding]:
    """全部のルールを回す。YAML として読めないファイルは TOOL-01 として返し、ほかの検査では飛ばす。"""
    scripts = {
        rel: tuple((root / rel).read_text(encoding="utf-8", errors="replace").splitlines()) for rel in found.scripts
    }
    ctx = Context(found, docs, scripts)
    findings = [
        Finding(doc.path, 1, "TOOL-01", f"YAML として読めない: {doc.error}") for doc in docs.values() if doc.error
    ]
    for rule in RULES:
        findings.extend(rule(ctx))
    return findings
