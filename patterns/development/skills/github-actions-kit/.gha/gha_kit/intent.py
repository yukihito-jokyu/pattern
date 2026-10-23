"""既存のワークフローが「何をしているか」を棚卸しし、作り直した後と突き合わせる（PROC-08）。

棚卸しは機械で拾える事実（トリガー、権限、secrets、使うアクション、コマンド、成果物など）だけを並べる。
それぞれの事実が何のためにあるか（意図）は、人とエージェントが表で埋める。
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from gha_kit.yamlnode import Document, Map, Node, Scalar, Seq, as_map, text_of

CATEGORIES = (
    ("trigger", "トリガー"),
    ("input", "入力"),
    ("permission", "権限"),
    ("secret", "secrets"),
    ("var", "vars"),
    ("environment", "environment"),
    ("job", "ジョブ"),
    ("runs-on", "ランナー"),
    ("uses", "使うアクション・再利用ワークフロー"),
    ("run", "コマンド"),
    ("artifact", "成果物"),
    ("output", "出力"),
)
CONTEXT = re.compile(r"\b(secrets|vars)\.([A-Za-z_][A-Za-z0-9_]*)")


def inventory(doc: Document) -> dict[str, set[str]]:
    """カテゴリごとの事実の集合。"""
    items: dict[str, set[str]] = {key: set() for key, _ in CATEGORIES}
    root = as_map(doc.root)
    if root is None:
        return items
    for kind, name in CONTEXT.findall("\n".join(doc.lines)):
        items["secret" if kind == "secrets" else "var"].add(name)
    _triggers(root.get("on"), items)
    _permissions(root.get("permissions"), items)
    for job_id, job in _pairs(root.get("jobs")):
        items["job"].add(job_id)
        _job(job_id, job, items)
    return items


def _pairs(node: Node | None) -> Iterator[tuple[str, Map]]:
    mapping = as_map(node)
    for key, value in mapping.pairs if mapping else ():
        if isinstance(value, Map):
            yield key.text, value


def _triggers(node: Node | None, items: dict[str, set[str]]) -> None:
    if isinstance(node, Scalar):
        items["trigger"].add(node.text)
    if isinstance(node, Seq):
        items["trigger"].update(text_of(item) or "" for item in node.items)
    if not isinstance(node, Map):
        return
    for event, detail in node.pairs:
        items["trigger"].add(event.text)
        for key, value in detail.pairs if isinstance(detail, Map) else ():
            if key.text == "inputs" and isinstance(value, Map):
                items["input"].update(value.names())
            elif key.text != "inputs":
                items["trigger"].add(f"{event.text}.{key.text}={_flat(value)}")


def _permissions(node: Node | None, items: dict[str, set[str]]) -> None:
    if isinstance(node, Scalar):
        items["permission"].add(node.text)
    for scope, level in node.pairs if isinstance(node, Map) else ():
        items["permission"].add(f"{scope.text}: {text_of(level)}")


def _job(job_id: str, job: Map, items: dict[str, set[str]]) -> None:
    _permissions(job.get("permissions"), items)
    environment = job.get("environment")
    name = text_of(environment.get("name")) if isinstance(environment, Map) else text_of(environment)
    if name:
        items["environment"].add(name)
    if job.get("runs-on") is not None:
        items["runs-on"].add(_flat(job.get("runs-on")))
    uses = text_of(job.get("uses"))
    if uses:
        items["uses"].add(_strip_ref(uses))
    outputs = job.get("outputs")
    if isinstance(outputs, Map):
        items["output"].update(f"{job_id}.{output}" for output in outputs.names())
    steps = job.get("steps")
    for step in steps.items if isinstance(steps, Seq) else ():
        if isinstance(step, Map):
            _step(step, items)


def _step(step: Map, items: dict[str, set[str]]) -> None:
    uses = text_of(step.get("uses"))
    inputs = step.get("with")
    if uses:
        items["uses"].add(_strip_ref(uses))
        artifact = text_of(inputs.get("name")) if isinstance(inputs, Map) else None
        if "artifact" in uses and artifact:
            items["artifact"].add(artifact)
    for line in (text_of(step.get("run")) or "").splitlines():
        command = " ".join(line.split())
        if command and not command.startswith("#"):
            items["run"].add(command)


def _strip_ref(uses: str) -> str:
    return uses.split("@", 1)[0]


def _flat(node: Node | None) -> str:
    if isinstance(node, Scalar):
        return node.text
    if isinstance(node, Seq):
        return "[" + ", ".join(_flat(item) for item in node.items) + "]"
    if isinstance(node, Map):
        return "{" + ", ".join(f"{key.text}: {_flat(value)}" for key, value in node.pairs) + "}"
    return ""


def render(doc: Document) -> str:
    """棚卸しの Markdown。意図の列は空にしておき、作り直しの前に埋める。"""
    items = inventory(doc)
    lines = [f"# {doc.path} の棚卸し", "", "| 種類 | 事実 | 意図（埋める） |", "|---|---|---|"]
    for key, title in CATEGORIES:
        lines += [f"| {title} | `{fact}` | |" for fact in sorted(items[key])]
    return "\n".join(lines) + "\n"


def compare(old: Document, new: Document) -> list[tuple[str, str]]:
    """古い方にあって新しい方に無い事実の (種類, 事実)。作り直しで落とした・移した事実の確認に使う。"""
    before, after = inventory(old), inventory(new)
    titles = dict(CATEGORIES)
    return [(titles[key], fact) for key, _ in CATEGORIES for fact in sorted(before[key] - after[key])]
