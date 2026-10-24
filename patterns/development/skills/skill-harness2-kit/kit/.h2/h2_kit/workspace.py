"""作業場所のファイルを読み、検証済みの型と進み具合を返す。書き込みはしない（STATE-01、ERR-02）。"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from h2_kit import fsops, layout, profile, skilltree
from h2_kit.errors import InvalidFileError, StageError


@dataclass(frozen=True)
class Task:
    """1つのタスク。prompt は task.md の中身、材料は workspace/ にある。"""

    task_id: str
    prompt: str
    directory: Path


@dataclass(frozen=True)
class Approval:
    """approve が書く承認の記録。ハッシュは承認した時点の profile.json と tasks/ のもの。"""

    round: int
    profile_sha256: str
    tasks_sha256: str
    skill_fingerprint: str
    task_order: tuple[str, ...]
    approved_on: str


@dataclass(frozen=True)
class Approved:
    """承認と照らし合わせたプロファイルとタスク。tasks は流す順。"""

    round: int
    profile: profile.Profile
    tasks: tuple[Task, ...]
    skill_fingerprint: str


@dataclass(frozen=True)
class RunRecord:
    """1回の実行の完了の記録（run.json）。最後に書くので、あれば実行は終わっている。"""

    label: str
    fingerprint: str
    ok: bool
    delivered: bool
    skill_invoked: bool
    cost_usd: float
    num_turns: int
    subtype: str
    permission_denials: int
    mark_version: int


@dataclass(frozen=True)
class SessionRecord:
    """1回の編集・選択・振り返りのセッションの記録（session.json）。key が同じなら結果を使い回す。"""

    key: str
    ok: bool
    cost_usd: float
    error: str


@dataclass(frozen=True)
class Summary:
    """1つのタスク・モードの完了の記録（summary.json）。台帳が恒等式に合ったときだけ書く。"""

    task_id: str
    mode: str
    k: int
    chosen_label: str
    chosen_id: str
    why: str
    fallback: bool
    error: str
    chosen_fingerprint: str
    finals: tuple[str, ...]
    delivered: tuple[str, ...]
    kept_base: tuple[str, ...]
    fell_back: tuple[str, ...]
    rollouts: tuple[str, ...]
    sessions: tuple[str, ...]
    diversity: float
    lesson: bool
    cost_usd: float


@dataclass(frozen=True)
class Adoption:
    """adopt が adopted.json に足す1件。"""

    round: int
    task_id: str
    mode: str
    label: str
    fingerprint: str
    adopted_on: str


@dataclass(frozen=True)
class Check:
    """事後の検査の1つ（checks.json）。command の {task_dir} と {reply_file} は judge が置き換える。"""

    name: str
    command: str
    timeout_sec: int


@dataclass(frozen=True)
class Progress:
    """承認したラウンドの進み具合。pending は終わっていない「タスク/モード」を流す順に並べたもの。"""

    round: int
    total: int
    finished: int
    pending: tuple[str, ...]


def load_profile(where: layout.Layout) -> profile.Profile:
    found, problems = profile.parse_profile(fsops.read_json(where.profile_path))
    if found is None:
        raise InvalidFileError(f"{where.profile_path} に問題があります: " + "、".join(problems))
    return found


def load_skill(where: layout.Layout, model: profile.Profile) -> tuple[skilltree.SkillTree, list[str]]:
    """対象スキルの木と、編集面の外のファイル。"""
    directory = where.skill_dir(model.skill)
    if not (directory / layout.SKILL_FILE).is_file():
        raise InvalidFileError(
            f"{directory} に {layout.SKILL_FILE} がありません（profile.json の skill を確かめてください）"
        )
    return skilltree.read_tree(directory)


def load_tasks(where: layout.Layout) -> list[Task]:
    """tasks/ の下の、task.md のあるディレクトリを名前の順に読む。"""
    found: list[Task] = []
    for name in fsops.list_dirs(where.tasks_dir):
        layout.require_name("タスク", name)
        text = fsops.read_text_or_none(where.task_file(name))
        if text is None or not text.strip():
            raise InvalidFileError(f"{where.task_file(name)} が無いか空です")
        found.append(Task(name, text, where.task_dir(name)))
    return found


def compute_task_order(task_ids: Sequence[str], seed: int | None, domain: str) -> list[str]:
    """流す順。種が無ければ名前の順、あれば harness2 と同じく `<種>:<領域>` でシャッフルする。"""
    ordered = sorted(task_ids)
    if seed is not None:
        random.Random(f"{seed}:{domain}").shuffle(ordered)
    return ordered


def compute_profile_sha256(where: layout.Layout) -> str:
    return fsops.compute_text_sha256(fsops.read_text(where.profile_path))


def compute_tasks_sha256(where: layout.Layout) -> str:
    return fsops.compute_tree_sha256(where.tasks_dir)


def load_approval(where: layout.Layout) -> Approval | None:
    if not where.approval_path.is_file():
        return None
    data = fsops.read_json(where.approval_path)
    problems: list[str] = []
    mapping = _require_mapping(data, where.approval_path)
    approval = Approval(
        round=_read_int(mapping.get("round"), "round", problems),
        profile_sha256=_read_str(mapping.get("profile_sha256"), "profile_sha256", problems),
        tasks_sha256=_read_str(mapping.get("tasks_sha256"), "tasks_sha256", problems),
        skill_fingerprint=_read_str(mapping.get("skill_fingerprint"), "skill_fingerprint", problems),
        task_order=_read_strs(mapping.get("task_order"), "task_order", problems),
        approved_on=_read_str(mapping.get("approved_on"), "approved_on", problems),
    )
    _require_no_problems(where.approval_path, problems)
    return approval


def load_approved(where: layout.Layout) -> Approved:
    """承認と、今の profile.json・tasks/ が一致することを確かめる。一致しなければ StageError を投げる。"""
    approval = load_approval(where)
    if approval is None:
        raise StageError("承認がありません。check の plan.md を人に見せてから approve を実行してください")
    if compute_profile_sha256(where) != approval.profile_sha256:
        raise StageError("承認の後に profile.json が変わりました。check を見せ直してから approve を実行してください")
    if compute_tasks_sha256(where) != approval.tasks_sha256:
        raise StageError("承認の後に tasks/ が変わりました。check を見せ直してから approve を実行してください")
    tasks = {task.task_id: task for task in load_tasks(where)}
    ordered = tuple(tasks[task_id] for task_id in approval.task_order if task_id in tasks)
    return Approved(approval.round, load_profile(where), ordered, approval.skill_fingerprint)


def load_run_record(rollout_dir: Path) -> RunRecord | None:
    path = rollout_dir / layout.RUN_FILE
    if not path.is_file():
        return None
    mapping = _require_mapping(fsops.read_json(path), path)
    problems: list[str] = []
    record = RunRecord(
        label=_read_str(mapping.get("label"), "label", problems),
        fingerprint=_read_str(mapping.get("fingerprint"), "fingerprint", problems),
        ok=_read_bool(mapping.get("ok"), "ok", problems),
        delivered=_read_bool(mapping.get("delivered"), "delivered", problems),
        skill_invoked=_read_bool(mapping.get("skill_invoked"), "skill_invoked", problems),
        cost_usd=_read_float(mapping.get("cost_usd"), "cost_usd", problems),
        num_turns=_read_int(mapping.get("num_turns"), "num_turns", problems),
        subtype=_read_str(mapping.get("subtype"), "subtype", problems),
        permission_denials=_read_int(mapping.get("permission_denials"), "permission_denials", problems),
        mark_version=_read_int(mapping.get("mark_version"), "mark_version", problems),
    )
    _require_no_problems(path, problems)
    return record


def load_session_record(session_dir: Path) -> SessionRecord | None:
    path = session_dir / layout.SESSION_FILE
    if not path.is_file():
        return None
    mapping = _require_mapping(fsops.read_json(path), path)
    problems: list[str] = []
    record = SessionRecord(
        key=_read_str(mapping.get("key"), "key", problems),
        ok=_read_bool(mapping.get("ok"), "ok", problems),
        cost_usd=_read_float(mapping.get("cost_usd"), "cost_usd", problems),
        error=_read_str(mapping.get("error"), "error", problems),
    )
    _require_no_problems(path, problems)
    return record


def load_summary(place: layout.TaskPlace, mode: str) -> Summary | None:
    path = place.summary_path(mode)
    if not path.is_file():
        return None
    mapping = _require_mapping(fsops.read_json(path), path)
    problems: list[str] = []
    summary = Summary(
        task_id=_read_str(mapping.get("task_id"), "task_id", problems),
        mode=_read_str(mapping.get("mode"), "mode", problems),
        k=_read_int(mapping.get("k"), "k", problems),
        chosen_label=_read_str(mapping.get("chosen_label"), "chosen_label", problems),
        chosen_id=_read_str(mapping.get("chosen_id"), "chosen_id", problems),
        why=_read_str(mapping.get("why"), "why", problems),
        fallback=_read_bool(mapping.get("fallback"), "fallback", problems),
        error=_read_str(mapping.get("error"), "error", problems),
        chosen_fingerprint=_read_str(mapping.get("chosen_fingerprint"), "chosen_fingerprint", problems),
        finals=_read_strs(mapping.get("finals"), "finals", problems),
        delivered=_read_strs(mapping.get("delivered"), "delivered", problems),
        kept_base=_read_strs(mapping.get("kept_base"), "kept_base", problems),
        fell_back=_read_strs(mapping.get("fell_back"), "fell_back", problems),
        rollouts=_read_strs(mapping.get("rollouts"), "rollouts", problems),
        sessions=_read_strs(mapping.get("sessions"), "sessions", problems),
        diversity=_read_float(mapping.get("diversity"), "diversity", problems),
        lesson=_read_bool(mapping.get("lesson"), "lesson", problems),
        cost_usd=_read_float(mapping.get("cost_usd"), "cost_usd", problems),
    )
    _require_no_problems(path, problems)
    return summary


def load_adoptions(where: layout.Layout) -> list[Adoption]:
    if not where.adopted_path.is_file():
        return []
    mapping = _require_mapping(fsops.read_json(where.adopted_path), where.adopted_path)
    problems: list[str] = []
    found = [_parse_adoption(item, problems) for item in _read_items(mapping.get("adoptions"), "adoptions", problems)]
    _require_no_problems(where.adopted_path, problems)
    return found


def load_checks(path: Path) -> list[Check]:
    """事後の検査の一覧。path は judging か planning が渡す（checks.json を読むのはその2つだけ。STATE-04）。"""
    if not path.is_file():
        return []
    mapping = _require_mapping(fsops.read_json(path), path)
    problems: list[str] = []
    found = [_parse_check(item, problems) for item in _read_items(mapping.get("checks"), "checks", problems)]
    _require_no_problems(path, problems)
    return found


def compute_progress(where: layout.Layout, approved: Approved) -> Progress:
    """完了の記録（summary.json）の有無から進み具合を求める。"""
    pending = [
        f"{task.task_id}/{mode}"
        for task in approved.tasks
        for mode in approved.profile.modes
        if not where.task_place(approved.round, task.task_id).summary_path(mode).is_file()
    ]
    total = len(approved.tasks) * len(approved.profile.modes)
    return Progress(approved.round, total, total - len(pending), tuple(pending))


def build_json(record: Approval | RunRecord | SessionRecord | Summary | Adoption) -> dict[str, object]:
    """記録を JSON の辞書にする。キーはフィールド名と同じ綴りになる（NAM-03）。書くのは呼び出し側。"""
    return asdict(record)


def _parse_adoption(data: object, problems: list[str]) -> Adoption:
    mapping = data if isinstance(data, dict) else {}
    return Adoption(
        round=_read_int(mapping.get("round"), "round", problems),
        task_id=_read_str(mapping.get("task_id"), "task_id", problems),
        mode=_read_str(mapping.get("mode"), "mode", problems),
        label=_read_str(mapping.get("label"), "label", problems),
        fingerprint=_read_str(mapping.get("fingerprint"), "fingerprint", problems),
        adopted_on=_read_str(mapping.get("adopted_on"), "adopted_on", problems),
    )


def _parse_check(data: object, problems: list[str]) -> Check:
    mapping = data if isinstance(data, dict) else {}
    check = Check(
        name=_read_str(mapping.get("name"), "name", problems),
        command=_read_str(mapping.get("command"), "command", problems),
        timeout_sec=_read_int(mapping.get("timeout_sec"), "timeout_sec", problems),
    )
    if not check.name or not check.command or check.timeout_sec <= 0:
        problems.append("checks の各項目は name、command（空でない文字列）と timeout_sec（正の整数）にしてください")
    return check


def _require_mapping(data: object, path: Path) -> dict[str, object]:
    if not isinstance(data, dict):
        raise InvalidFileError(f"{path} の最上位はオブジェクトにしてください")
    return {str(key): value for key, value in data.items()}


def _require_no_problems(path: Path, problems: list[str]) -> None:
    if problems:
        raise InvalidFileError(f"{path} に問題があります: " + "、".join(problems))


def _read_str(value: object, name: str, problems: list[str]) -> str:
    if not isinstance(value, str):
        problems.append(f"{name} は文字列にしてください")
        return ""
    return value


def _read_int(value: object, name: str, problems: list[str]) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        problems.append(f"{name} は整数にしてください")
        return 0
    return value


def _read_float(value: object, name: str, problems: list[str]) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        problems.append(f"{name} は数にしてください")
        return 0.0
    return float(value)


def _read_bool(value: object, name: str, problems: list[str]) -> bool:
    if not isinstance(value, bool):
        problems.append(f"{name} は true か false にしてください")
        return False
    return value


def _read_strs(value: object, name: str, problems: list[str]) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        problems.append(f"{name} は文字列の配列にしてください")
        return ()
    return tuple(str(item) for item in value)


def _read_items(value: object, name: str, problems: list[str]) -> list[object]:
    if not isinstance(value, list):
        problems.append(f"{name} は配列にしてください")
        return []
    return list(value)
