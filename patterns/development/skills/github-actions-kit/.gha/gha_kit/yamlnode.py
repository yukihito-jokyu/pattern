"""YAML を、行番号と書き方（引用、ブロック）を持つノードとして読む。

PyYAML の compose は値を型に変換する前の文字列を返すので、YAML 1.1 で真偽値になる `on` も
文字列の `on` のまま扱える。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Scalar:
    text: str
    line: int
    style: str  # "" は引用なし。ほかは "'"、'"'、"|"、">"


@dataclass(frozen=True)
class Seq:
    items: tuple[Node, ...]
    line: int


@dataclass(frozen=True)
class Map:
    pairs: tuple[tuple[Scalar, Node], ...]
    line: int

    def get(self, key: str) -> Node | None:
        return next((value for name, value in self.pairs if name.text == key), None)

    def names(self) -> list[str]:
        return [name.text for name, _ in self.pairs]

    def key_line(self, key: str) -> int:
        return next((name.line for name, _ in self.pairs if name.text == key), self.line)


Node = Scalar | Seq | Map


@dataclass(frozen=True)
class Document:
    path: str
    lines: tuple[str, ...]
    root: Node | None
    error: str
    anchor_lines: tuple[int, ...]

    def line_text(self, line: int) -> str:
        return self.lines[line - 1] if 0 < line <= len(self.lines) else ""


def load(root: Path, rel: str) -> Document:
    """ファイルを読む。YAML として壊れていれば error に理由を入れ、root は None にする。"""
    text = (root / rel).read_text(encoding="utf-8")
    lines = tuple(text.splitlines())
    try:
        node = yaml.compose(text, Loader=yaml.SafeLoader)
        events = list(yaml.parse(text, Loader=yaml.SafeLoader))
    except yaml.YAMLError as exc:
        return Document(rel, lines, None, str(exc).splitlines()[0], ())
    anchors = tuple(
        event.start_mark.line + 1
        for event in events
        if isinstance(event, yaml.NodeEvent) and event.anchor is not None and event.start_mark is not None
    )
    return Document(rel, lines, _convert(node) if node is not None else None, "", anchors)


def _convert(node: yaml.Node) -> Node:
    line = node.start_mark.line + 1
    if isinstance(node, yaml.MappingNode):
        return Map(tuple((_key(key), _convert(value)) for key, value in node.value), line)
    if isinstance(node, yaml.SequenceNode):
        return Seq(tuple(_convert(item) for item in node.value), line)
    style = node.style if isinstance(node, yaml.ScalarNode) else None
    return Scalar(str(node.value), line, style or "")


def _key(node: yaml.Node) -> Scalar:
    if isinstance(node, yaml.ScalarNode):
        return Scalar(str(node.value), node.start_mark.line + 1, node.style or "")
    return Scalar("", node.start_mark.line + 1, "")


def as_map(node: Node | None) -> Map | None:
    return node if isinstance(node, Map) else None


def as_seq(node: Node | None) -> Seq | None:
    return node if isinstance(node, Seq) else None


def text_of(node: Node | None) -> str | None:
    return node.text if isinstance(node, Scalar) else None
