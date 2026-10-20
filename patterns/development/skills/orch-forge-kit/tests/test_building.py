"""building のテスト。設計から骨組みと構築役のプロンプトを書き、下書きを検査して、リポジトリへ入れることを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import building, bundle, designing, fsops, layout, workspace
from forge_kit.errors import InvalidFileError, StageError
from tests import support


class BuildingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.where = support.approved_layout(self, support.orch_charter(support.NEW_SKILL))
        designing.design_new(self.where, "")
        support.act_designer(self.where)
        designing.design_check(self.where)
        designing.design_approve(self.where, support.TODAY)

    def test_build_writes_skeleton(self) -> None:
        out = building.build(self.where, "")
        self.assertIn("job forge-builder build ", out)
        files = bundle.files(self.where.draft_dir, support.NEW_SKILL)
        self.assertEqual(
            files,
            (
                "skills/new-orch/SKILL.md",
                "agents/new-orch-implementer.md",
                "agents/new-orch-reviewer.md",
            ),
        )
        skill_md = fsops.read_text(self.where.draft_dir / files[0])
        self.assertIn("2. `new-orch-implementer` に任せる: 変更を加え、検査を通す", skill_md)
        self.assertIn("- S1: 決まらない名前をどうするか 既定: 既存の書き方に合わせる", skill_md)

    def test_bundle_check(self) -> None:
        building.build(self.where, "")
        with self.assertRaises(InvalidFileError) as caught:
            building.bundle_check(self.where)
        self.assertIn("B10 ", caught.exception.message)
        support.act_builder(self.where)
        self.assertIn("問題なし", building.bundle_check(self.where))
        self.assertTrue(self.where.bundle_check_md_path.is_file())

    def test_install(self) -> None:
        building.build(self.where, "")
        support.act_builder(self.where)
        building.bundle_check(self.where)
        reviewer = self.where.draft_dir / "agents/new-orch-reviewer.md"
        fsops.write_text(reviewer, fsops.read_text(reviewer) + "検査の後に足した行\n")
        with self.assertRaises(StageError):
            building.install(self.where, support.TODAY)
        building.bundle_check(self.where)
        building.install(self.where, support.TODAY)
        self.assertTrue(bundle.has_bundle(self.where.claude_dir, support.NEW_SKILL))
        installation = workspace.load_installation(self.where)
        self.assertEqual(len(installation.files) if installation else 0, 3)
        with self.assertRaises(StageError):
            building.install(self.where, support.TODAY)

    def test_feedback(self) -> None:
        building.build(self.where, "報告に費用を足して")
        self.assertIn("報告に費用を足して", fsops.read_text(self.where.builder_prompt_path))
        self.assertTrue((self.where.draft_dir / layout.SKILLS_DIR / support.NEW_SKILL).is_dir())


if __name__ == "__main__":
    unittest.main()
