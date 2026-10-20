"""対象の作業領域を読む。charter と設計の承認の確認、記録の読み込み（load_*）、進み具合の判定を行う。"""

from __future__ import annotations

from dataclasses import dataclass

from forge_kit import charter, contracts, design, fsops, layout, trace
from forge_kit.errors import InvalidFileError, KitError, StageError
from forge_kit.layout import Layout, Slot


def load_charter(where: Layout) -> tuple[dict[str, object], charter.Charter]:
    """charter.json を読み、元の値（承認のハッシュの計算に使う）と検証済みのモデルを返す。"""
    data = fsops.read_json(where.charter_path)
    model = charter.parse(data, str(where.charter_path))
    if not isinstance(data, dict):
        raise InvalidFileError(str(where.charter_path), ["全体はオブジェクトにしてください"])
    if model.target.id != where.target:
        raise KitError(f"charter の target.id（{model.target.id}）が --target（{where.target}）と違います")
    return data, model


def approved_charter(where: Layout) -> tuple[charter.Charter, str]:
    """人の承認が有効な charter とそのハッシュ。未承認か、承認の後に変えていれば止める。"""
    data, model = load_charter(where)
    state = charter.approval_state(data, model)
    if state == "unapproved":
        raise StageError("charter が未承認です。/forge-goals で人と内容を確かめ、承認を記録してください")
    if state == "stale":
        raise StageError("charter が承認の後に変更されています。/forge-goals で変更点を人に見せ、承認し直してください")
    return model, charter.digest(data)


def has_skill(where: Layout, model: charter.Charter) -> bool:
    return where.skill_md_path(model.target.skill_name).is_file()


def load_design(where: Layout, model: charter.Charter) -> tuple[object, design.Design]:
    path = where.design_path
    if not path.is_file():
        raise StageError(f"{path} がありません。設計役を起動してください")
    data = fsops.read_json(path)
    return data, design.parse(data, str(path), skill_name=model.target.skill_name)


def load_design_approval(where: Layout) -> contracts.DesignApproval | None:
    path = where.design_approval_path
    return contracts.parse_design_approval(fsops.read_json(path), str(path)) if path.is_file() else None


def design_state(where: Layout, data: object) -> str:
    """設計の承認の状態。approved、unapproved、stale（承認の後に design.json が変わった）のどれか。"""
    approval = load_design_approval(where)
    if approval is None:
        return "unapproved"
    return "approved" if approval.sha256 == design.digest(data) else "stale"


def approved_design(where: Layout, model: charter.Charter) -> tuple[design.Design, str]:
    data, found = load_design(where, model)
    state = design_state(where, data)
    if state != "approved":
        reason = "未承認" if state == "unapproved" else "承認の後に変更されています"
        raise StageError(f"設計が{reason}。design.md を人に見せ、design-approve で承認を記録してください")
    return found, design.digest(data)


def load_bundle_check(where: Layout) -> contracts.BundleCheck | None:
    path = where.bundle_check_path
    return contracts.parse_bundle_check(fsops.read_json(path), str(path)) if path.is_file() else None


def load_installation(where: Layout) -> contracts.Installation | None:
    path = where.install_path
    return contracts.parse_installation(fsops.read_json(path), str(path)) if path.is_file() else None


def load_plan(where: Layout, slot: Slot) -> contracts.Plan:
    path = where.plan_path(slot)
    if not path.is_file():
        raise StageError(f"{slot.name} はまだ準備されていません。先に prepare を実行してください")
    return contracts.parse_plan(fsops.read_json(path), str(path))


def load_fingerprint(where: Layout, slot: Slot) -> dict[str, str]:
    data = fsops.read_json(where.fingerprint_path(slot))
    if not isinstance(data, dict):
        raise InvalidFileError(str(where.fingerprint_path(slot)), ["全体はオブジェクトにしてください"])
    return {str(key): str(value) for key, value in data.items()}


def load_execution(where: Layout, slot: Slot, run_id: str) -> contracts.Execution:
    path = where.exec_path(slot, run_id)
    if not path.is_file():
        raise StageError(f"{slot.name} の {run_id} はまだ実行されていません。先に execute を実行してください")
    return contracts.parse_execution(fsops.read_json(path), str(path))


def load_trace(where: Layout, slot: Slot, run_id: str) -> trace.Trace:
    path = where.stream_path(slot, run_id)
    if not path.is_file():
        raise StageError(f"{slot.name} の {run_id} の実行の記録がありません。先に execute を実行してください")
    return trace.parse(fsops.read_text(path))


def load_facts(where: Layout, slot: Slot, run_id: str) -> contracts.Facts:
    path = where.facts_path(slot, run_id)
    if not path.is_file():
        raise StageError(f"{slot.name} の {run_id} の事実がありません。先に collect を実行してください")
    return contracts.parse_facts(fsops.read_json(path), str(path))


def load_grade(where: Layout, slot: Slot, run_id: str) -> contracts.Grade:
    path = where.grade_path(slot, run_id)
    if not path.is_file():
        raise StageError(f"{run_id} の採点（{path}）がありません")
    keys = tuple(target.key for target in load_facts(where, slot, run_id).grade_targets)
    return contracts.parse_grade(fsops.read_json(path), str(path), run_id=run_id, keys=keys)


def load_scores(where: Layout, slot: Slot) -> contracts.Scores:
    path = where.scores_path(slot)
    if not path.is_file():
        raise StageError(f"{slot.name} はまだ採点されていません。先に score を実行してください")
    return contracts.parse_scores(fsops.read_json(path), str(path))


def load_proposal(where: Layout, model: charter.Charter, round_no: int) -> contracts.Proposal:
    path = where.proposal_path(round_no)
    if not path.is_file():
        raise StageError(f"{round_no} 回目のラウンドの proposal.json がありません。分析役を起動してください")
    metric_ids = tuple(choice.id for choice in model.metrics)
    return contracts.parse_proposal(fsops.read_json(path), str(path), metric_ids=metric_ids)


def load_comparison(where: Layout, round_no: int) -> contracts.Comparison:
    path = where.compare_path(round_no)
    if not path.is_file():
        raise StageError(f"{round_no} 回目の比較がまだありません。先に compare を実行してください")
    return contracts.parse_comparison(fsops.read_json(path), str(path))


def load_decision(where: Layout, round_no: int) -> contracts.Decision | None:
    path = where.decision_path(round_no)
    return contracts.parse_decision(fsops.read_json(path), str(path)) if path.is_file() else None


@dataclass(frozen=True)
class BuildProgress:
    """初版を作る段の進み具合。design_state は設計が無ければ missing。"""

    designer_prompted: bool
    designed: bool
    design_checked: bool
    design_state: str
    builder_prompted: bool
    bundle_checked: bool


def build_progress(where: Layout, model: charter.Charter) -> BuildProgress:
    state = "missing"
    if where.design_path.is_file():
        state = _design_state_or_unapproved(where, model)
    return BuildProgress(
        designer_prompted=where.designer_prompt_path.is_file(),
        designed=where.design_path.is_file(),
        design_checked=where.design_md_path.is_file(),
        design_state=state,
        builder_prompted=where.builder_prompt_path.is_file(),
        bundle_checked=where.bundle_check_path.is_file(),
    )


def _design_state_or_unapproved(where: Layout, model: charter.Charter) -> str:
    try:
        data, _found = load_design(where, model)
    except KitError:
        return "unapproved"
    return design_state(where, data)


@dataclass(frozen=True)
class SlotProgress:
    """1回の評価の進み具合。pending_* は、まだ実行・採点の終わっていない実行。"""

    slot: Slot
    planned: bool
    pending_runs: tuple[contracts.Run, ...]
    collected: bool
    pending_grades: tuple[contracts.Run, ...]
    scored: bool


@dataclass(frozen=True)
class RoundProgress:
    round_no: int
    analyzed: bool
    proposed: bool
    checked: bool
    has_changes: bool
    candidate: SlotProgress
    compared: bool
    decision: contracts.Decision | None


@dataclass(frozen=True)
class Progress:
    """作業領域のファイルから求めた進み具合。current_slot は、今の対象スキルを評価した結果の置き場。"""

    baseline: SlotProgress
    rounds: tuple[RoundProgress, ...]
    current_slot: Slot
    final: SlotProgress
    reported: bool

    @property
    def decided_rounds(self) -> int:
        return sum(1 for item in self.rounds if item.decision is not None)


def slot_progress(where: Layout, model: charter.Charter, slot: Slot) -> SlotProgress:
    if not where.plan_path(slot).is_file():
        return SlotProgress(slot, False, (), False, (), False)
    plan = load_plan(where, slot)
    pending_runs = tuple(run for run in plan.runs if not where.exec_path(slot, run.run_id).is_file())
    collected = all(where.facts_path(slot, run.run_id).is_file() for run in plan.runs)
    pending_grades: tuple[contracts.Run, ...] = ()
    if collected and charter.has_grader_items(model):
        pending_grades = tuple(run for run in plan.runs if not _has_valid_grade(where, slot, run.run_id))
    return SlotProgress(slot, True, pending_runs, collected, pending_grades, where.scores_path(slot).is_file())


def _has_valid_grade(where: Layout, slot: Slot, run_id: str) -> bool:
    try:
        load_grade(where, slot, run_id)
    except KitError:
        return False
    return True


def round_progress(where: Layout, model: charter.Charter, round_no: int) -> RoundProgress:
    checked = where.proposal_md_path(round_no).is_file()
    has_changes = checked and bool(load_proposal(where, model, round_no).changes)
    return RoundProgress(
        round_no=round_no,
        analyzed=where.analyst_prompt_path(round_no).is_file(),
        proposed=where.proposal_path(round_no).is_file(),
        checked=checked,
        has_changes=has_changes,
        candidate=slot_progress(where, model, layout.make_slot("candidate", round_no)),
        compared=where.compare_path(round_no).is_file(),
        decision=load_decision(where, round_no),
    )


def progress(where: Layout, model: charter.Charter) -> Progress:
    rounds = []
    round_no = 1
    while where.analyst_prompt_path(round_no).is_file():
        rounds.append(round_progress(where, model, round_no))
        round_no += 1
    baseline = layout.make_slot("baseline", 1)
    current = baseline
    for item in rounds:
        if item.decision is not None and item.decision.adopted:
            current = item.candidate.slot
    return Progress(
        baseline=slot_progress(where, model, baseline),
        rounds=tuple(rounds),
        current_slot=current,
        final=slot_progress(where, model, layout.make_slot("final", 0)),
        reported=where.report_path.is_file(),
    )
