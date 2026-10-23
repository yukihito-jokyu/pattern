"""構造の検査が共有する、ワークフローと composite アクションの辿り方。"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath

from gha_kit.findings import Finding
from gha_kit.targets import Targets
from gha_kit.yamlnode import Document, Map, Node, Scalar, Seq, as_map, text_of

EXPRESSION = re.compile(r"^\$\{\{.*\}\}$", re.S)


@dataclass(frozen=True)
class Context:
    found: Targets
    docs: Mapping[str, Document]
    scripts: Mapping[str, tuple[str, ...]]

    def workflows(self) -> Iterator[tuple[Document, Map]]:
        yield from self._maps(self.found.workflows)

    def actions(self) -> Iterator[tuple[Document, Map]]:
        yield from self._maps(self.found.actions)

    def yaml_docs(self) -> Iterator[Document]:
        for rel in self.found.yaml_files():
            if rel in self.docs:
                yield self.docs[rel]

    def _maps(self, paths: tuple[str, ...]) -> Iterator[tuple[Document, Map]]:
        for rel in paths:
            doc = self.docs.get(rel)
            root = as_map(doc.root) if doc else None
            if doc is not None and root is not None:
                yield doc, root


def finding(rule: str, doc: Document, line: int, message: str) -> Finding:
    return Finding(doc.path, line, rule, message)


def stem(path: str) -> str:
    return PurePosixPath(path).stem


def is_ci(doc: Document) -> bool:
    return PurePosixPath(doc.path).name == "ci.yml"


def is_reusable(doc: Document) -> bool:
    return stem(doc.path).startswith("reusable-")


def events(root: Map) -> Map | None:
    return as_map(root.get("on"))


def jobs(root: Map) -> Iterator[tuple[Scalar, Map]]:
    mapping = as_map(root.get("jobs"))
    for key, value in mapping.pairs if mapping else ():
        if isinstance(value, Map):
            yield key, value


def steps(container: Map) -> Iterator[Map]:
    """ジョブの steps、または composite アクションの runs.steps の各ステップ。"""
    node = container.get("steps")
    if node is None:
        runs = as_map(container.get("runs"))
        node = runs.get("steps") if runs else None
    for item in node.items if isinstance(node, Seq) else ():
        if isinstance(item, Map):
            yield item


def all_steps(ctx: Context) -> Iterator[tuple[Document, Map, bool]]:
    """(文書, ステップ, composite アクションか) の組。"""
    for doc, root in ctx.workflows():
        for _, job in jobs(root):
            for step in steps(job):
                yield doc, step, False
    for doc, root in ctx.actions():
        for step in steps(root):
            yield doc, step, True


def env_maps(root: Map) -> Iterator[tuple[str, Map]]:
    """ワークフロー・ジョブ・ステップの env と、そのレベル名（workflow、job、step）。"""
    if isinstance(env := root.get("env"), Map):
        yield "workflow", env
    for _, job in jobs(root):
        if isinstance(env := job.get("env"), Map):
            yield "job", env
        for step in steps(job):
            if isinstance(env := step.get("env"), Map):
                yield "step", env


def uses_of(step: Map) -> str:
    return text_of(step.get("uses")) or ""


def action_name(uses: str) -> str:
    """`owner/repo/path@ref` から `owner/repo/path` を取り出す。"""
    return uses.split("@", 1)[0]


def scalar_lines(node: Node | None) -> int:
    text = text_of(node)
    return len(text.rstrip("\n").splitlines()) if text else 0


def is_expression(text: str | None) -> bool:
    return bool(text and EXPRESSION.match(text.strip()))


def permission_map(job: Map) -> Map | None:
    return as_map(job.get("permissions"))


def writes(job: Map) -> list[str]:
    perms = permission_map(job)
    return [key.text for key, value in perms.pairs if text_of(value) == "write"] if perms else []
