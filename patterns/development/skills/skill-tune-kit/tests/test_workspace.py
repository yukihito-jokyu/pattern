"""workspace のテスト。ファイルから求める進み具合を確かめる（STATE-01）。"""

from __future__ import annotations

import unittest
from fractions import Fraction

from tests import support
from tune_kit import errors, fsops, layout, metrics, plan, workspace


class WorkspaceTest(unittest.TestCase):
    def test_change_after_approval_stops_stages(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        data = support.read_json(where.cases_path)
        assert isinstance(data, dict)
        data["cases"][0]["prompt"] = "変えた依頼"
        fsops.write_json(where.cases_path, data)
        with self.assertRaises(errors.StageError):
            workspace.load_approved(where)

    def test_changed_case_makes_its_result_stale(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        support.run_eval(self, root, layout.FIRST_VERSION, (plan.TRAIN, plan.VAL))
        fsops.write_text(where.input_dir("c01") / "memo.txt", "入力を足した")
        support.run_approve(self, root)
        approved = workspace.load_approved(where)
        states = {
            ref.case_id: workspace.compute_run_state(where, approved, ref)
            for ref in workspace.list_runs(approved, "v0", (plan.TRAIN,))
        }
        self.assertEqual(states["c01"], workspace.UNPREPARED)
        self.assertEqual(states["c02"], workspace.DONE)

    def test_stop_reason_follows_budget(self) -> None:
        model = plan.parse_plan(support.build_plan(max_rounds=3, patience=2))[0]
        assert model is not None
        imperfect = metrics.Summary(1, 1, Fraction(0), Fraction(0), (), ())
        rejected = support.build_decisions(adopted=(False, False))
        self.assertEqual(workspace.compute_stop_reason(model, rejected[:1], imperfect), "")
        self.assertIn("続けて不採用", workspace.compute_stop_reason(model, rejected, imperfect))

    def test_current_version_is_last_adopted(self) -> None:
        decisions = support.build_decisions(adopted=(True, False))
        self.assertEqual(workspace.compute_current(decisions), "v1")

    def test_skill_name_is_read_from_frontmatter(self) -> None:
        self.assertEqual(workspace.find_skill_name("---\nname: 'sample'\n---\n本文"), "sample")
        self.assertEqual(workspace.find_skill_name("本文だけ"), "")
