"""外部ツールの規則名と、この基盤のルールIDの対応表。表に無い規則は、ツールごとの既定のルールIDにする。

ルールIDは docs/design/rules.md（配布先では .claude/skills/gha-workflow/references/rules.md）で引く。
"""

from __future__ import annotations

DEFAULTS = {"yamllint": "TOOL-01", "actionlint": "TEST-01", "shellcheck": "TEST-01", "zizmor": "OPS-05"}
RULES = {
    "actionlint:credentials": "OPS-02",
    "actionlint:deprecated-commands": "STATE-01",
    "actionlint:job-needs": "PROC-02",
    "actionlint:permissions": "OPS-06",
    "actionlint:runner-label": "NAM-06",
    "actionlint:workflow-call": "PROC-02",
    "zizmor:cache-poisoning": "STATE-02",
    "zizmor:dependabot-cooldown": "PROC-03",
    "zizmor:dependabot-execution": "PROC-03",
    "zizmor:excessive-permissions": "OPS-06",
    "zizmor:forbidden-uses": "DEP-04",
    "zizmor:github-env": "STATE-01",
    "zizmor:overprovisioned-secrets": "OPS-02",
    "zizmor:secrets-inherit": "OPS-02",
    "zizmor:template-injection": "ERR-02",
    "zizmor:unpinned-images": "DEP-06",
    "zizmor:unreadable": "TEST-01",
    "zizmor:unpinned-uses": "DEP-06",
    "zizmor:unredacted-secrets": "OPS-02",
}
UNTRUSTED = "potentially untrusted"


def rule_for(tool: str, kind: str, message: str) -> str:
    if tool == "actionlint" and kind == "expression" and UNTRUSTED in message:
        return "ERR-02"
    return RULES.get(f"{tool}:{kind}", DEFAULTS[tool])
