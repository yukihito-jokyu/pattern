"""段の入口。実行の記録と今の tree を読み、今がその段の番かを確かめる（GATE-03）。"""

from __future__ import annotations

from dataclasses import dataclass

from autoflow_kit import changes, trail, workspace
from autoflow_kit.errors import StageError
from autoflow_kit.layout import CLI, Layout
from autoflow_kit.profile import Profile


@dataclass(frozen=True)
class Context:
    """段が使う、実行の状態。profile は開始時に写したプロファイル（OPS-02）。"""

    where: Layout
    run_id: str
    profile: Profile
    events: tuple[trail.Event, ...]
    tree: str
    next: trail.Next

    @property
    def start(self) -> trail.Event:
        return self.events[0]


def peek(where: Layout, run_id: str) -> Context:
    """段を確かめずに、今の状態だけを読む（status が使う）。"""
    events = workspace.load_trail(where, run_id)
    expected = events[0].branch
    current = changes.branch(where.root)
    if current != expected:
        raise StageError(
            f"今のブランチは {current} です。実行 {run_id} の作業ブランチ {expected} に切り替えてから続ける"
        )
    tree = changes.snapshot(where.root)
    return Context(where, run_id, workspace.load_profile(where, run_id), events, tree, trail.next_step(events, tree))


def begin(where: Layout, run_id: str, step: str) -> Context:
    """段の入口で最初に呼ぶ。今が step の番でなければ StageError にする。"""
    ctx = peek(where, run_id)
    if ctx.next.step != step:
        raise StageError(
            f"今は {step} の番ではなく {ctx.next.step} の番です（{ctx.next.why}）。"
            f"{CLI} status --run {run_id} で次を確かめる"
        )
    return ctx


def require_prompted(ctx: Context, role: str, command: str) -> None:
    """プロンプトを書いた後の段（*-check、review-collect、review-tally）で、役の順序を確かめる。"""
    if ctx.next.prompted != role:
        raise StageError(f"先に {CLI} {command} --run {ctx.run_id} でプロンプトを書き、役を起動する")


def require_same_tree(expected: str, actual: str) -> None:
    """読み取りだけの役の前後で tree が同じかを確かめる（GATE-07）。"""
    if expected != actual:
        raise StageError(
            "読み取りだけの役の間に作業ツリーが変わりました"
            f"（控えた tree: {expected[:12]}、今: {actual[:12]}）。"
            "git status で変わったファイルを確かめ、人に報告して止まる"
        )
