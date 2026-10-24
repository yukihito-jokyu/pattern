"""status のテスト。全行の書き出しと段階の移り変わり（OPS-01）。"""

from __future__ import annotations

import unittest

from h2_kit import adoption, execution, layout, planning, skilltree, status, workspace
from tests import support

LINE_KINDS = ("対象:", "段階:", "進み:", "問題:", "次:")


def _build_lines(where: layout.Layout) -> dict[str, str]:
    lines = status.status(where).splitlines()
    for line in lines:
        if not line.startswith(LINE_KINDS):
            raise AssertionError(f"決めた書き出しで始まらない行: {line}")
    return {line.split(":", 1)[0] + ":": line.split(":", 1)[1].strip() for line in lines}


class StatusTest(unittest.TestCase):
    def test_line_kinds_are_fixed(self) -> None:
        self.assertEqual(status.LINE_KINDS, LINE_KINDS)

    def test_stages_follow_the_files(self) -> None:
        where = support.build_where(support.build_repo(self))
        self.assertEqual(_build_lines(where)["段階:"], "準備")
        support.write_profile(where)
        support.write_task(where)
        self.assertEqual(_build_lines(where)["段階:"], "準備")
        planning.check(where)
        self.assertEqual(_build_lines(where)["段階:"], "承認待ち")
        planning.approve(where, support.TODAY)
        self.assertEqual(_build_lines(where)["段階:"], "実行待ち")
        execution.run(where, None, lambda _line: None)
        lines = _build_lines(where)
        self.assertEqual((lines["段階:"], lines["進み:"]), ("結果の確認", "ラウンド 1、1/1（タスク×モード）"))
        summary = workspace.load_summary(where.task_place(1, support.TASK_ID), layout.PARALLEL)
        assert summary is not None
        code = skilltree.build_confirm_code(summary.chosen_fingerprint)
        adoption.adopt(where, support.TASK_ID, layout.PARALLEL, code, support.TODAY)
        self.assertEqual(_build_lines(where)["段階:"], "採用済み")

    def test_problems_are_shown_on_their_own_line(self) -> None:
        where = support.build_approved(self)
        support.write_profile(where, k=0)
        self.assertIn("k は", _build_lines(where)["問題:"])
        support.write_profile(where, k=2)
        lines = _build_lines(where)
        self.assertEqual(lines["段階:"], "承認待ち")
        self.assertIn("profile.json が変わりました", lines["問題:"])
