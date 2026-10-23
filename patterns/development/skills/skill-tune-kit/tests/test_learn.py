"""learn のテスト。学習役に見せる範囲と、写しの検出を確かめる（STATE-03）。"""

from __future__ import annotations

import unittest

from tests import support
from tune_kit import layout


class LearnTest(unittest.TestCase):
    def test_evidence_and_prompt_show_train_only(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        support.run_until_learn(self, root)
        evidence = (where.round_dir(1) / layout.EVIDENCE_FILE).read_text(encoding="utf-8")
        prompt = (where.round_dir(1) / layout.LEARNER_PROMPT_FILE).read_text(encoding="utf-8")
        train = sorted(case_id for case_id, split in support.SPLITS.items() if split == "train")
        held_out = sorted(case_id for case_id, split in support.SPLITS.items() if split != "train")
        for case_id in train:
            self.assertIn(f"## ケース {case_id}（", evidence)
        for case_id in held_out:
            self.assertNotIn(support.build_prompt(case_id), evidence + prompt)
        self.assertLess(evidence.index("## ケース c01"), evidence.index("## ケース c02"))

    def test_copy_of_held_out_text_is_rejected(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        support.run_until_learn(self, root)
        support.write_skill_line(where, "v1", "例: " + support.build_prompt("c03"))
        support.write_proposal(
            where, 1, [{"file": "SKILL.md", "summary": "例を足した", "cause": "c", "cases": ["c01"]}]
        )
        code, _out, err = support.run_cli(root, "learn-check", "--round", "1")
        self.assertEqual(code, 1)
        self.assertIn("検証用・テスト用の文の写しがあります（c03:", err)
        self.assertFalse((where.round_dir(1) / layout.PROPOSAL_FILE).exists())
        prompt = (where.round_dir(1) / layout.LEARNER_PROMPT_FILE).read_text(encoding="utf-8")
        self.assertIn("検証用・テスト用の文の写しがあります", prompt)

    def test_name_change_and_undeclared_change_are_rejected(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        support.run_until_learn(self, root)
        skill = where.version_dir("v1") / layout.SKILL_FILE
        skill.write_text(skill.read_text(encoding="utf-8").replace("name: sample", "name: renamed"), encoding="utf-8")
        (where.version_dir("v1") / "references" / "formats.md").write_text("変えた\n", encoding="utf-8")
        support.write_proposal(where, 1, [{"file": "SKILL.md", "summary": "s", "cause": "c", "cases": ["c01"]}])
        code, _out, err = support.run_cli(root, "learn-check", "--round", "1")
        self.assertEqual(code, 1)
        self.assertIn("references/formats.md を変えたのに proposal.json の changes にありません", err)
        self.assertIn("SKILL.md の frontmatter の name を変えないでください", err)

    def test_train_copy_is_only_a_warning(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        support.run_until_learn(self, root)
        support.write_skill_line(where, "v1", "例: " + support.build_prompt("c01"))
        support.write_proposal(
            where, 1, [{"file": "SKILL.md", "summary": "例を足した", "cause": "c", "cases": ["c01"]}]
        )
        out = support.run_ok(self, root, "learn-check", "--round", "1")
        self.assertIn("写しの警告 1 件", out)
