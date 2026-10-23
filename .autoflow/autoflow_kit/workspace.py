"""ファイルを読んで検証し、モデルを返す（load_*）。承認済みのプロファイルと、実行の一覧も求める。

外から来る JSON は、ここを通してから使う（ERR-02）。
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Callable, TypeVar

from autoflow_kit import contracts, fsops, layout, policy, proc, profile, shape, trail
from autoflow_kit.errors import InvalidFileError, StageError
from autoflow_kit.layout import Layout

Model = TypeVar("Model")


def _load(path: Path, parse: Callable[[object, list[str]], Model]) -> Model:
    problems: list[str] = []
    model = parse(fsops.read_json(path), problems)
    if problems:
        raise InvalidFileError(str(path), problems)
    return model


def load_profile_file(path: Path) -> profile.Profile:
    return _load(path, profile.parse)


def approved_profile(where: Layout) -> profile.Profile:
    """リポジトリ共通の記録を読み、同じ設定の H0 承認を次のタスクへ引き継ぐ。"""
    if not where.profile_path.is_file():
        raise StageError(f"{where.relative(where.profile_path)} がありません。/autoflow-setup で作り、承認を得る")
    settings = load_profile_file(where.profile_path)
    digest = profile.digest(fsops.read_text(where.profile_path))
    path = where.approval_path(proc.git_common_dir(where.root), digest)
    if not path.is_file() and where.legacy_approval_path.is_file():
        # 旧記録は承認済みの内容に一致するときだけ移す。原文・記録者・日時は変えない。
        legacy = _load(where.legacy_approval_path, profile.parse_approval)
        if legacy.sha256 == digest:
            fsops.write_json(path, shape.to_data(legacy))
    if not path.is_file():
        raise StageError(
            "現在の profile.json に対応する承認記録がありません。/autoflow-setup で設定を確認し、人の承認を得る（H0）"
        )
    approval = _load(path, profile.parse_approval)
    if digest != approval.sha256:
        raise StageError("承認記録と profile.json が一致しません。/autoflow-setup で記録を確認する")
    return settings


def load_profile(where: Layout, run_id: str) -> profile.Profile:
    """実行の開始時に写したプロファイル。実行の中の段はこれだけを読む（OPS-02）。"""
    return load_profile_file(where.snapshot_profile_path(run_id))


def load_trail(where: Layout, run_id: str) -> tuple[trail.Event, ...]:
    path = where.trail_path(run_id)
    if not path.is_file():
        raise StageError(f"実行 {run_id} の記録がありません。start で始める")
    problems: list[str] = []
    events = trail.parse_events(fsops.read_lines(path), problems)
    if problems:
        raise InvalidFileError(str(path), problems)
    return events


def load_plan(where: Layout, run_id: str, plan_no: int) -> contracts.Plan:
    def parse(value: object, problems: list[str]) -> contracts.Plan:
        plan = contracts.parse_plan(value, (kind.name for kind in policy.KINDS), problems)
        return plan if problems else _checked(plan, problems)

    return _load(where.plan_path(run_id, plan_no), parse)


def _checked(plan: contracts.Plan, problems: list[str]) -> contracts.Plan:
    problems += policy.check_plan(plan)
    return plan


def load_flow(where: Layout, run_id: str, plan_no: int) -> policy.Flow:
    return _load(where.flow_path(run_id, plan_no), policy.parse_flow)


def load_report(where: Layout, run_id: str, attempt: int) -> contracts.BuildReport:
    return _load(where.report_path(run_id, attempt), contracts.parse_report)


def load_findings(where: Layout, run_id: str, round_no: int, lens: str) -> tuple[contracts.Finding, ...]:
    return _load(
        where.findings_path(run_id, round_no, lens),
        lambda value, problems: contracts.parse_findings(value, policy.REVIEW.categories, problems),
    )


def load_candidates(where: Layout, run_id: str, round_no: int) -> tuple[contracts.Candidate, ...]:
    return _load(
        where.candidates_path(run_id, round_no),
        lambda value, problems: contracts.parse_candidates(value, policy.REVIEW.categories, problems),
    )


def load_votes(where: Layout, run_id: str, round_no: int, voter: int, ids: Iterable[str]) -> tuple[contracts.Vote, ...]:
    expected = tuple(ids)
    return _load(
        where.votes_path(run_id, round_no, voter),
        lambda value, problems: contracts.parse_votes(value, expected, policy.REVIEW.tags, problems),
    )


def load_result(where: Layout, run_id: str, round_no: int) -> contracts.ReviewResult:
    return _load(
        where.result_path(run_id, round_no),
        lambda value, problems: contracts.parse_result(value, policy.REVIEW.categories, problems),
    )


def load_judgment(where: Layout, run_id: str, risk_no: int) -> contracts.RiskJudgment:
    return _load(
        where.judgment_path(run_id, risk_no),
        lambda value, problems: contracts.parse_judgment(value, (tier.name for tier in policy.TIERS), problems),
    )


def load_evidence(where: Layout, run_id: str, seq: int) -> contracts.Evidence:
    return _load(where.evidence_path(run_id, seq), contracts.parse_evidence)


def runs(where: Layout) -> tuple[str, ...]:
    """記録のある実行の id を古い順に並べる。"""
    if not where.runs_dir.is_dir():
        return ()
    found = [path.name for path in where.runs_dir.iterdir() if layout.RUN_ID.match(path.name)]
    return tuple(sorted(name for name in found if where.trail_path(name).is_file()))


def latest_run(where: Layout) -> str:
    found = runs(where)
    if not found:
        raise StageError("実行がありません。/autoflow で依頼から始める")
    return found[-1]


def load_scripts(path: Path) -> tuple[str, ...]:
    """package.json の scripts の名前（setup が検査コマンドを検出するのに使う）。"""

    def parse(value: object, problems: list[str]) -> tuple[str, ...]:
        data = shape.as_object(value, "", problems)
        return tuple(shape.as_object(data.get("scripts", {}), "scripts", problems))

    return _load(path, parse)


def load_settings(path: Path) -> dict[str, object]:
    """Claude Code の設定のファイル。無ければ空のオブジェクト。"""
    if not path.is_file():
        return {}
    return _load(path, lambda value, problems: shape.as_object(value, "", problems))
