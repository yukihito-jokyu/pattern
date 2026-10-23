"""検査の対象になるファイルを見つける。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from gha_kit import layout


@dataclass(frozen=True)
class Targets:
    workflows: tuple[str, ...]
    actions: tuple[str, ...]
    dependabot: tuple[str, ...]
    scripts: tuple[str, ...]

    def yaml_files(self) -> tuple[str, ...]:
        return self.workflows + self.actions + self.dependabot

    def all_files(self) -> tuple[str, ...]:
        return self.yaml_files() + self.scripts


def discover(root: Path) -> Targets:
    """`.github/` の下のワークフロー、composite アクション、Dependabot の設定、スクリプトを集める。

    置き場の違反（STR-01）を見つけるため、サブディレクトリも辿る。
    """
    return Targets(
        workflows=_glob(root, layout.WORKFLOWS, ("**/*.yml", "**/*.yaml")),
        actions=_glob(root, layout.ACTIONS, ("**/action.yml", "**/action.yaml")),
        dependabot=_glob(root, ".github", ("dependabot.yml", "dependabot.yaml")),
        scripts=_glob(root, layout.SCRIPTS, ("**/*",)),
    )


def select(targets: Targets, paths: Sequence[str]) -> Targets:
    """指定のパスだけに絞る。指定が無ければ全部。"""
    if not paths:
        return targets
    wanted = {Path(path).as_posix().removeprefix("./") for path in paths}
    return Targets(
        workflows=tuple(p for p in targets.workflows if p in wanted),
        actions=tuple(p for p in targets.actions if p in wanted),
        dependabot=tuple(p for p in targets.dependabot if p in wanted),
        scripts=tuple(p for p in targets.scripts if p in wanted),
    )


def _glob(root: Path, base: str, patterns: Sequence[str]) -> tuple[str, ...]:
    directory = root / base
    if not directory.is_dir():
        return ()
    found = {path.relative_to(root).as_posix() for pattern in patterns for path in directory.glob(pattern)}
    return tuple(sorted(path for path in found if (root / path).is_file()))
