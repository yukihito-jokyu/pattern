"""人の関所の段（decide）。人の回答の原文と、そのときの tree と、答えた人を記録する（GATE-05）。"""

from __future__ import annotations

from autoflow_kit import context, fsops, policy, proc, trail
from autoflow_kit.errors import StageError
from autoflow_kit.layout import Layout


def decide(where: Layout, run_id: str, gate: str, choice: str, answer: str, now: str) -> str:
    ctx = context.begin(where, run_id, trail.DECIDE)
    if gate != ctx.next.gate:
        raise StageError(f"今の関所は {ctx.next.gate} です（--gate {gate} は違う）")
    options = [option.name for option in policy.gate_of(gate).options]
    if choice not in options:
        raise StageError(f"{gate} で選べるのは {', '.join(options)} です（今: {choice}）")
    if not answer.strip():
        raise StageError("人の回答の原文を --answer に渡す。回答が無い・空・自動で閉じた質問は、承認にも選択にもしない")
    who = proc.git_user(where.root)
    event = trail.decided(gate, choice, answer, ctx.tree, who, now)
    fsops.append_line(where.trail_path(run_id), trail.encode(event))
    return f"記録した: {gate} {choice}（tree {ctx.tree[:12]}、答えた人 {who or '—'}）"
