"""保守的更新の検査：基準の版より指摘が増えていないかを、ファイルとルールIDの組ごとの件数で比べる（PROC-07）。

基準の版の `.github/` を一時ディレクトリに写し、今の `.gha/` の設定で同じ検査を回す。
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from gha_kit import checks, gitref, layout, proc
from gha_kit.findings import Finding, counts


@dataclass(frozen=True)
class Increase:
    path: str
    rule: str
    before: int
    after: int
    findings: tuple[Finding, ...]


def compare(root: Path, ref: str, paths: Sequence[str] = (), runner: proc.Runner = proc.run) -> list[Increase]:
    with tempfile.TemporaryDirectory(prefix="gha-ratchet-") as tmp:
        base = Path(tmp)
        for rel in gitref.tracked(root, ref, ".github"):
            text = gitref.show(root, ref, rel)
            if text is not None:
                (base / rel).parent.mkdir(parents=True, exist_ok=True)
                (base / rel).write_text(text, encoding="utf-8")
        shutil.copytree(root / layout.CONFIG_DIR, base / layout.CONFIG_DIR, dirs_exist_ok=True)
        existing = [path for path in paths if (base / path).is_file()]
        before = counts(checks.run(base, existing, runner=runner)) if existing or not paths else counts([])
    current = checks.run(root, paths, runner=runner)
    after = counts(current)
    return [
        Increase(
            path, rule, before[(path, rule)], number, tuple(f for f in current if (f.path, f.rule) == (path, rule))
        )
        for (path, rule), number in sorted(after.items())
        if number > before[(path, rule)]
    ]
