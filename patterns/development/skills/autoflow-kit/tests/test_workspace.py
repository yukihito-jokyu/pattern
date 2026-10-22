"""workspace のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import fsops, workspace
from autoflow_kit.errors import InvalidFileError, StageError
from tests import support


class WorkspaceTest(unittest.TestCase):
    def test_approved_profile(self) -> None:
        where = support.make_repo(self)
        self.assertEqual(workspace.approved_profile(where).verify.commands, (support.UNIT,))

    def test_profile_changed_after_approval(self) -> None:
        where = support.make_repo(self)
        fsops.write_text(where.profile_path, fsops.read_text(where.profile_path).replace("60", "61"))
        with self.assertRaisesRegex(StageError, "承認の後に変わりました"):
            workspace.approved_profile(where)

    def test_profile_missing_or_unapproved(self) -> None:
        where = support.make_repo(self)
        where.approval_path.unlink()
        with self.assertRaisesRegex(StageError, "承認されていません"):
            workspace.approved_profile(where)
        where.profile_path.unlink()
        with self.assertRaisesRegex(StageError, "がありません"):
            workspace.approved_profile(where)

    def test_plan_checked_by_kind(self) -> None:
        where, run_id = support.started(self)
        fsops.write_json(where.plan_path(run_id, 1), support.feature_plan(kind="fix"))
        with self.assertRaises(InvalidFileError) as caught:
            workspace.load_plan(where, run_id, 1)
        self.assertEqual(len(caught.exception.problems), 2)

    def test_runs(self) -> None:
        where = support.make_repo(self)
        with self.assertRaisesRegex(StageError, "実行がありません"):
            workspace.latest_run(where)
        for run_id in ("20261021-150000", "20261021-143000-a", "not-a-run"):
            fsops.append_line(where.runs_dir / run_id / "trail.jsonl", "{}")
        self.assertEqual(workspace.runs(where), ("20261021-143000-a", "20261021-150000"))
        self.assertEqual(workspace.latest_run(where), "20261021-150000")

    def test_missing_trail(self) -> None:
        where = support.make_repo(self)
        with self.assertRaisesRegex(StageError, "記録がありません"):
            workspace.load_trail(where, support.RUN_ID)

    def test_scripts_and_settings(self) -> None:
        where = support.make_repo(self)
        fsops.write_json(where.repo_path("package.json"), {"scripts": {"lint": "eslint .", "test": "vitest"}})
        self.assertEqual(workspace.load_scripts(where.repo_path("package.json")), ("lint", "test"))
        self.assertEqual(workspace.load_settings(where.settings_local_path), {})
