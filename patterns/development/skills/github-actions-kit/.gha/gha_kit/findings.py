"""検査の指摘の型と、出力の形（`<ルールID> <パス>:<行> <説明>`）。"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    rule: str
    message: str

    def render(self) -> str:
        return f"{self.rule} {self.path}:{self.line} {self.message}"


def counts(findings: Iterable[Finding]) -> Counter[tuple[str, str]]:
    """ファイルとルールIDの組ごとの件数（ラチェットで、変更の前後を比べるのに使う）。"""
    return Counter((finding.path, finding.rule) for finding in findings)
