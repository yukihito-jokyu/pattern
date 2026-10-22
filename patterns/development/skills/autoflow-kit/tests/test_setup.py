"""setup のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import fsops, profile, setup, workspace
from autoflow_kit.errors import StageError
from tests import support


class SetupTest(unittest.TestCase):
    def test_detect_make_check_only(self) -> None:
        where = support.make_repo(self)
        fsops.write_text(where.repo_path("Makefile"), "check:\n\tmake test\ntest:\n\tpytest\n")
        fsops.write_json(where.repo_path("package.json"), {"scripts": {"lint": "eslint ."}})
        self.assertEqual([command.id for command in setup.detect_commands(where)], ["make-check"])

    def test_detect_package_and_languages(self) -> None:
        where = support.make_repo(self)
        fsops.write_json(where.repo_path("package.json"), {"scripts": {"lint": "x", "test": "y", "dev": "z"}})
        fsops.write_text(where.repo_path("pnpm-lock.yaml"), "")
        fsops.write_text(where.repo_path("go.mod"), "module x\n")
        runs = [command.run for command in setup.detect_commands(where)]
        self.assertEqual(runs, ["pnpm lint", "pnpm test", "go build ./...", "go vet ./...", "go test ./..."])

    def test_setup_new(self) -> None:
        where = support.make_repo(self)
        where.profile_path.unlink()
        fsops.write_text(where.repo_path("REVIEW.md"), "# レビュー\n")
        self.assertIn("WARN 検査コマンドが見つかりません", setup.setup_new(where, force=False))
        with self.assertRaisesRegex(StageError, "既にあります"):
            setup.setup_new(where, force=False)
        fsops.write_text(where.repo_path("Makefile"), "test:\n\tpytest\n")
        self.assertNotIn("WARN", setup.setup_new(where, force=True))
        settings = workspace.load_profile_file(where.profile_path)
        self.assertEqual((settings.review.guide_files, settings.verify.commands[0].run), (("REVIEW.md",), "make test"))

    def test_setup_check_warns_missing_guide(self) -> None:
        settings = profile.make_profile((support.UNIT,), ("REVIEW.md",))
        where = support.make_repo(self, settings)
        self.assertIn("WARN review.guide_files の REVIEW.md がありません", setup.setup_check(where))

    def test_approve_requires_answer(self) -> None:
        where = support.make_repo(self)
        with self.assertRaisesRegex(StageError, "承認にしない"):
            setup.setup_approve(where, " ", support.NOW, allow=False)

    def test_approve_records_digest_and_allow(self) -> None:
        where = support.make_repo(self)
        fsops.write_json(where.settings_local_path, {"permissions": {"allow": ["Bash(ls)"]}, "model": "x"})
        setup.setup_approve(where, "承認します", support.NOW, allow=True)
        setup.setup_approve(where, "承認します", support.NOW, allow=True)
        approval = fsops.read_json(where.approval_path)
        assert isinstance(approval, dict)
        self.assertEqual(approval["sha256"], profile.digest(fsops.read_text(where.profile_path)))
        self.assertEqual(approval["who"], support.EMAIL)
        expected = {"permissions": {"allow": ["Bash(ls)", f"Bash({support.UNIT.run})"]}, "model": "x"}
        self.assertEqual(workspace.load_settings(where.settings_local_path), expected)
