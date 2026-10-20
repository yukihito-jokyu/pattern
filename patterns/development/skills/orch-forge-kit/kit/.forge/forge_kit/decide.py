"""人が決めた採否を記録する。採用なら、今のバンドルを退避してから、候補を対象のリポジトリの .claude/ へ写す。"""

from __future__ import annotations

from forge_kit import bundle, contracts, fsops, workspace
from forge_kit.errors import StageError
from forge_kit.layout import Layout


def decide(where: Layout, round_no: int, *, adopted: bool, today: str) -> str:
    model, _sha = workspace.approved_charter(where)
    progress = workspace.progress(where, model)
    current = next((item for item in progress.rounds if item.round_no == round_no), None)
    if current is None or not current.checked:
        raise StageError(f"{round_no} 回目の提案がまだ確かめられていません。status で次にすることを確かめてください")
    if current.decision is not None:
        raise StageError(f"{round_no} 回目は決定済みです")
    if current.has_changes and not current.compared:
        raise StageError(f"{round_no} 回目はまだ比べていません。先に compare を実行してください")
    if adopted and not current.has_changes:
        raise StageError("バンドルの変更が無い提案は採用できません。--reject で閉じてください")
    name = model.target.skill_name
    if adopted:
        fsops.remove_tree(where.previous_dir(round_no))
        bundle.copy(where.claude_dir, where.previous_dir(round_no), name)
        bundle.place(where, name, where.proposed_dir(round_no))
    decision = contracts.Decision(round_no, adopted, today)
    fsops.write_json(where.decision_path(round_no), contracts.to_data(decision))
    if adopted:
        return f"採用しました: {name} を更新した（元のバンドルは {where.previous_dir(round_no)}）"
    return f"不採用を記録しました: {round_no} 回目（バンドルは変えていない）"
