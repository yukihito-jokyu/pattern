"""intake のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import fsops, intake, profile, trail, workspace
from autoflow_kit.errors import StageError
from tests import support

ORIGIN = trail.Origin("backlog", "PROJ-12", "https://example.com/PROJ-12", "掛け算を足す")


class IntakeTest(unittest.TestCase):
    def test_start(self) -> None:
        where = support.make_repo(self)
        text = intake.start(where, ORIGIN, support.body_file(where), support.NOW)
        run_id = "20261021-143000-proj-12"
        self.assertIn(f"実行: {run_id}", text)
        self.assertEqual(support.git(where.root, "branch", "--show-current").strip(), f"autoflow/{run_id}")
        self.assertIn(support.TASK_BODY, fsops.read_text(where.task_path(run_id)))
        self.assertEqual(fsops.read_text(where.guide_path(run_id)), "- なし\n")
        self.assertEqual(workspace.load_profile(where, run_id).verify.commands, (support.UNIT,))
        start = support.events(where, run_id)[0]
        self.assertEqual((start.kind, start.ref, start.branch), (trail.STARTED, "PROJ-12", f"autoflow/{run_id}"))

    def test_needs_clean_tree(self) -> None:
        where = support.make_repo(self)
        fsops.write_text(where.repo_path("calc.py"), "x = 1\n")
        with self.assertRaisesRegex(StageError, "未コミットの変更"):
            intake.start(where, ORIGIN, support.body_file(where), support.NOW)

    def test_needs_ignored_runs(self) -> None:
        where = support.make_repo(self)
        fsops.write_text(where.repo_path(".gitignore"), "__pycache__/\n")
        support.commit_all(where, "ignore を外す")
        with self.assertRaisesRegex(StageError, ".gitignore に入っていません"):
            intake.start(where, ORIGIN, support.body_file(where), support.NOW)

    def test_needs_approved_profile(self) -> None:
        where = support.make_repo(self)
        where.approval_path.unlink()
        support.commit_all(where, "承認を消す")
        with self.assertRaisesRegex(StageError, "承認されていません"):
            intake.start(where, ORIGIN, support.body_file(where), support.NOW)

    def test_origin_checks(self) -> None:
        where = support.make_repo(self)
        no_ref = trail.Origin("redmine", "", "", "題名")
        with self.assertRaisesRegex(StageError, "--ref"):
            intake.start(where, no_ref, support.body_file(where), support.NOW)
        with self.assertRaisesRegex(StageError, "が空です"):
            intake.start(where, ORIGIN, support.body_file(where, " \n"), support.NOW)

    def test_guide_is_copied(self) -> None:
        where = support.make_repo(self, profile.make_profile((support.UNIT,), ("REVIEW.md",)))
        fsops.write_text(where.repo_path("REVIEW.md"), "必ず境界の値を確かめる\n")
        support.commit_all(where, "レビューの指示")
        intake.start(where, ORIGIN, support.body_file(where), support.NOW)
        self.assertIn("必ず境界の値を確かめる", fsops.read_text(where.guide_path("20261021-143000-proj-12")))
