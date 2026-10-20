"""report のテスト。最後の評価の後に、指標の推移・ラウンド・人に判断してほしいことを書くことを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import fsops, layout, report, score, workspace
from forge_kit.errors import StageError
from tests import support


class ReportTest(unittest.TestCase):
    def test_report(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        support.scored_slot(where, layout.make_slot("baseline", 1), stream="delegated", met=True)
        with self.assertRaises(StageError):
            report.report(where)
        support.scored_slot(where, layout.make_slot("final", 0), stream="delegated", met=True)
        report.report(where)
        text = fsops.read_text(where.report_path)
        self.assertIn("| delegation | must | 0.800 | 1.000 | 1.000 | 1.000 |", text)
        self.assertIn("改善のラウンドは行っていない", text)
        self.assertIn("Bash(python3 check.py)", text)
        self.assertIn("## 6. 人に判断してほしいこと\n\n- なし", text)
        final = layout.make_slot("final", 0)
        for run in workspace.load_plan(where, final).runs:
            if run.task_id == "H1":
                grade = fsops.read_json(where.grade_path(final, run.run_id))
                assert isinstance(grade, dict)
                items = [{**item, "met": False} for item in grade["items"]]
                fsops.write_json(where.grade_path(final, run.run_id), {**grade, "items": items})
        score.score(where, final)
        report.report(where)
        self.assertIn("ホールドアウトでは未達。採った変更は無いので", fsops.read_text(where.report_path))


if __name__ == "__main__":
    unittest.main()
