"""install.py（配布先に写す）のテスト。配布先は一時ディレクトリにする。"""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import install
from tests.support import write


class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_copies_the_cli_the_report_action_and_both_skills(self) -> None:
        install.install(self.target)

        for rel in (
            ".gha/gha.py",
            ".gha/gha_kit/cli.py",
            ".gha/zizmor.yml",
            ".github/actions/run-report/run_report.py",
            ".github/dependabot.yml",
            ".claude/skills/gha-workflow/SKILL.md",
            ".claude/skills/gha-review/SKILL.md",
        ):
            self.assertTrue((self.target / rel).is_file(), rel)

    def test_keeps_the_allow_list_of_the_target(self) -> None:
        write(self.target, ".gha/zizmor.yml", "# 配布先の許可表\n")

        install.install(self.target)

        self.assertEqual((self.target / ".gha/zizmor.yml").read_text(encoding="utf-8"), "# 配布先の許可表\n")

    def test_keeps_the_dependabot_config_of_the_target(self) -> None:
        write(self.target, ".github/dependabot.yml", "# 配布先の設定\n")

        install.install(self.target)

        self.assertEqual((self.target / ".github/dependabot.yml").read_text(encoding="utf-8"), "# 配布先の設定\n")

    def test_replaces_stale_files_in_replaced_directories(self) -> None:
        write(self.target, ".gha/gha_kit/old_module.py", "")

        install.install(self.target)

        self.assertFalse((self.target / ".gha/gha_kit/old_module.py").exists())

    def test_writes_nothing_on_a_dry_run(self) -> None:
        install.install(self.target, dry_run=True)

        self.assertEqual(list(self.target.iterdir()), [])

    def test_refuses_to_install_into_the_kit_itself(self) -> None:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(install.main([str(install.KIT)]), 2)


if __name__ == "__main__":
    unittest.main()
