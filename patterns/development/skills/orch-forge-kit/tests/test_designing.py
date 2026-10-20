"""designing のテスト。設計役のプロンプト、設計の検査と承認、直してほしいことの受け渡しを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import contracts, designing, fsops, render, workspace
from forge_kit.errors import InvalidFileError, StageError
from tests import support


class DesigningTest(unittest.TestCase):
    def setUp(self) -> None:
        self.where = support.approved_layout(self, support.orch_charter(support.NEW_SKILL))

    def test_design_new(self) -> None:
        out = designing.design_new(self.where, "")
        self.assertIn(f"job {contracts.AGENTS['designer']} design ", out)
        prompt = fsops.read_text(self.where.designer_prompt_path)
        self.assertIn(str(self.where.design_path), prompt)
        self.assertIn(f"\n{render.MISSING}\n", prompt)
        self.assertNotIn("在庫を空にする関数を足して", fsops.read_text(self.where.visible_charter_path))

    def test_design_new_refuses_existing_skill(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        with self.assertRaises(StageError):
            designing.design_new(where, "")

    def test_design_check_and_approve(self) -> None:
        designing.design_new(self.where, "")
        fsops.write_json(self.where.design_path, {"schema_version": 1})
        with self.assertRaises(InvalidFileError):
            designing.design_check(self.where)
        support.act_designer(self.where)
        self.assertIn("役 2、手順 4、人の関所 1", designing.design_check(self.where))
        designing.design_approve(self.where, support.TODAY)
        model, _sha = workspace.approved_charter(self.where)
        self.assertEqual(workspace.build_progress(self.where, model).design_state, "approved")

    def test_feedback(self) -> None:
        designing.design_new(self.where, "")
        support.act_designer(self.where)
        designing.design_check(self.where)
        designing.design_approve(self.where, support.TODAY)
        with self.assertRaises(StageError):
            designing.design_new(self.where, "")
        designing.design_new(self.where, "レビュー役を2人にして")
        self.assertIn("レビュー役を2人にして", fsops.read_text(self.where.designer_prompt_path))
        self.assertFalse(self.where.design_approval_path.exists())


if __name__ == "__main__":
    unittest.main()
