"""H2（行き詰まり）の条件を確かめ、当たれば関所の理由を書いて、記録に escalate を足す。

実装・検証・レビューの3つの段が、自分の出来事を記録した直後に呼ぶ。
"""

from __future__ import annotations

from collections.abc import Sequence

from autoflow_kit import fsops, policy, trail, views
from autoflow_kit.layout import Layout
from autoflow_kit.profile import Limits


def record(where: Layout, run_id: str, events: Sequence[trail.Event], limits: Limits, now: str) -> tuple[str, ...]:
    """events は記録したばかりの出来事を含む全部。当たった H2 の規則の id を返す（無ければ空）。"""
    progress = trail.progress(events)
    reasons = policy.h2_reasons(progress, limits)
    if not reasons:
        return ()
    number = trail.count(events, trail.ESCALATED) + 1
    details = (
        f"続いた検査の失敗: {progress.failed_checks} 回（上限 {limits.fix_attempts}）",
        f"Important が残ったレビュー: {progress.open_rounds} 回（上限 {limits.review_rounds}）",
        *(f"実装役が止まった理由: {blocker}" for blocker in progress.blockers),
    )
    fsops.write_text(where.gate_path(run_id, policy.H2, number), views.render_gate(policy.H2, reasons, details))
    fsops.append_line(where.trail_path(run_id), trail.encode(trail.escalate(number, reasons, events[-1].tree, now)))
    return reasons
