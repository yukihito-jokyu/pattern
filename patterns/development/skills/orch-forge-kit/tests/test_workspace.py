"""workspace のテスト。承認の確認、記録の読み込み、ファイルの有無から求める進み具合を確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import fsops, layout, workspace
from forge_kit.errors import KitError, StageError
from tests import support


class WorkspaceTest(unittest.TestCase):
    def test_approved_charter(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        model, sha = workspace.approved_charter(where)
        self.assertEqual((model.target.id, len(sha)), (support.SKILL, 64))
        data = fsops.read_json(where.charter_path)
        assert isinstance(data, dict)
        data["purpose"] = "承認の後に変えた"
        fsops.write_json(where.charter_path, data)
        with self.assertRaises(StageError):
            workspace.approved_charter(where)

    def test_load_charter_checks_target(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        other = support.make_where(where.root, "other")
        fsops.copy_file(where.charter_path, other.charter_path)
        with self.assertRaises(KitError):
            workspace.load_charter(other)

    def test_progress(self) -> None:
        where = support.baseline_scored(self)
        model, _sha = workspace.approved_charter(where)
        found = workspace.progress(where, model)
        self.assertTrue(found.baseline.scored)
        self.assertEqual((found.rounds, found.decided_rounds), ((), 0))
        self.assertEqual(found.current_slot, layout.make_slot("baseline", 1))
        self.assertFalse(found.final.planned)

    def test_load_grade_uses_facts_keys(self) -> None:
        where = support.baseline_scored(self)
        slot = layout.make_slot("baseline", 1)
        grade = workspace.load_grade(where, slot, "T1-a1")
        self.assertEqual(grade.items[0].key, "acceptance:1")
        fsops.write_json(where.grade_path(slot, "T1-a1"), {"run_id": "T1-a1", "items": []})
        with self.assertRaises(KitError):
            workspace.load_grade(where, slot, "T1-a1")

    def test_build_progress(self) -> None:
        where = support.approved_layout(self, support.orch_charter(support.NEW_SKILL))
        model, _sha = workspace.approved_charter(where)
        self.assertEqual(workspace.build_progress(where, model).design_state, "missing")
        support.act_designer(where)
        self.assertEqual(workspace.build_progress(where, model).design_state, "unapproved")


if __name__ == "__main__":
    unittest.main()
