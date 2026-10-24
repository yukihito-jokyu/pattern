"""adopt の段。人が選んだ候補を、確認の符号を確かめてから対象スキルに書き込む（PROC-07）。"""

from __future__ import annotations

from h2_kit import fsops, layout, render, skilltree, validate, workspace
from h2_kit.errors import StageError


def adopt(where: layout.Layout, task_id: str, mode: str, confirm: str, today: str) -> str:
    """承認時のスキルから変わっていないこと、記録と木が一致すること、確認の符号が一致することを確かめて書き込む。"""
    approved = workspace.load_approved(where)
    current, _ = workspace.load_skill(where, approved.profile)
    if skilltree.compute_fingerprint(current) != approved.skill_fingerprint:
        raise StageError(
            "承認の後に対象スキルが変わりました（採用済みか、手で変えた）。このラウンドの候補は書き込めません"
        )
    place = where.task_place(approved.round, task_id)
    summary = workspace.load_summary(place, mode)
    if summary is None:
        raise StageError(f"{task_id}/{mode} はまだ終わっていません。status で進みを確かめてください")
    if not summary.chosen_label:
        raise StageError(f"{task_id}/{mode} には選ばれた候補がありません")
    tree, outside = skilltree.read_tree(place.harness_dir(mode, summary.chosen_label))
    fingerprint = skilltree.compute_fingerprint(tree)
    if fingerprint != summary.chosen_fingerprint:
        raise StageError(f"{summary.chosen_label} の木が summary.json の記録と違います。run の記録を確かめてください")
    if confirm != skilltree.build_confirm_code(fingerprint):
        raise StageError("確認の符号が違います。show が出した符号を --confirm に渡してください")
    problems = validate.check_tree(tree, current, outside)
    if problems:
        raise StageError("候補が検証に通りません:\n" + render.render_bullets(problems))
    skilltree.write_tree(tree, where.skill_dir(approved.profile.skill))
    record = workspace.Adoption(approved.round, task_id, mode, summary.chosen_label, fingerprint, today)
    adoptions = [*workspace.load_adoptions(where), record]
    fsops.write_json(where.adopted_path, {"adoptions": [workspace.build_json(item) for item in adoptions]})
    changes = skilltree.compute_changes(current, tree)
    lines = [
        f"{task_id}/{mode} の {summary.chosen_label} を書き込んだ（{approved.profile.skill}、{len(changes)} ファイル）",
        "次: git diff で差分を確かめ、よければコミットする。新しいラウンドは check → 人の承認 → approve",
    ]
    return "\n".join(lines)
