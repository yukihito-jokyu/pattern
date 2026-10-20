"""collect のテスト。実行の後の事実（差分、検査、起動と編集）を集め、採点役のプロンプトを書くことを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import collect, execute, fsops, layout, prepare, workspace
from tests import support


class CollectTest(unittest.TestCase):
    def setUp(self) -> None:
        self.where = support.approved_layout(self, support.orch_charter())
        self.slot = layout.make_slot("baseline", 1)
        prepare.prepare(self.where, self.slot)

    def test_collect_delegated(self) -> None:
        execute.execute(self.where, self.slot, support.fake_launcher(stream="delegated"))
        out = collect.collect(self.where, self.slot, parallel=2)
        self.assertIn("採点役 2 件", out)
        self.assertIn("job forge-grader T1-a1 ", out)
        facts = workspace.load_facts(self.where, self.slot, "T1-a1")
        self.assertEqual(facts.changed_files, (support.IMPL_FILE,))
        self.assertFalse(any(self.where.copy_dir(self.slot, "T1-a1").rglob("__pycache__")))
        self.assertEqual((facts.check_exit, facts.edits_main, facts.edits_sub), (0, 0, 1))
        self.assertEqual(facts.launches, ("dev-orch-implementer", "dev-orch-reviewer"))
        self.assertTrue(facts.completed)
        prompt = fsops.read_text(self.where.grader_prompt_path(self.slot, "T1-a1"))
        self.assertIn("`step:2`", prompt)
        self.assertIn(str(self.where.trace_md_path(self.slot, "T1-a1")), prompt)
        self.assertIn(
            "変えたファイル: inventory/remove.py", fsops.read_text(self.where.result_md_path(self.slot, "T1-a1"))
        )

    def test_protected_changed_and_failed_check(self) -> None:
        launcher = support.fake_launcher(files={"check.py": "import sys\nsys.exit(3)\n"})
        execute.execute(self.where, self.slot, launcher)
        collect.collect(self.where, self.slot, parallel=1)
        facts = workspace.load_facts(self.where, self.slot, "T1-a2")
        self.assertEqual((facts.check_exit, facts.protected_changed), (3, ("check.py",)))

    def test_unfinished_run_gets_unmet_grade(self) -> None:
        execute.execute(self.where, self.slot, support.fake_launcher(stream="unfinished"))
        out = collect.collect(self.where, self.slot, parallel=1)
        self.assertIn("WARN T1-a1 は最後まで終えなかった", out)
        grade = workspace.load_grade(self.where, self.slot, "T1-a1")
        self.assertFalse(any(item.met for item in grade.items))

    def test_contamination(self) -> None:
        execute.execute(self.where, self.slot, support.fake_launcher())
        fsops.write_text(self.where.root / "inventory/stock.py", "評価の間に変わった\n")
        self.assertIn("WARN 評価の間に元のリポジトリで 1 件", collect.collect(self.where, self.slot, parallel=1))


if __name__ == "__main__":
    unittest.main()
