"""install のテスト。"""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import install


def _run_install(*argv: str) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return install.main(list(argv))


class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name).resolve()

    def test_installs_the_cli_and_the_skill(self) -> None:
        self.assertEqual(_run_install(str(self.repo)), 0)
        for path in (".h2/h2.py", ".h2/h2_kit/cli.py", ".h2/templates/prompts/mission.md", ".h2/.gitignore"):
            self.assertTrue((self.repo / path).is_file(), path)
        self.assertTrue((self.repo / ".claude/skills/skill-harness2/references/profile-guide.md").is_file())
        done = subprocess.run(
            [sys.executable, ".h2/h2.py", "status", "sample"],
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(done.returncode, 0)
        self.assertIn("段階: 準備", done.stdout)

    def test_conflict_needs_force_and_keeps_targets(self) -> None:
        _run_install(str(self.repo))
        skill = self.repo / ".claude/skills/skill-harness2/SKILL.md"
        skill.write_text("手で変えた", encoding="utf-8")
        stale = self.repo / ".h2/h2_kit/old.py"
        stale.write_text("", encoding="utf-8")
        profile = self.repo / ".h2/targets/x/profile.json"
        profile.parent.mkdir(parents=True)
        profile.write_text("{}", encoding="utf-8")
        self.assertEqual(_run_install(str(self.repo)), 1)
        self.assertEqual(skill.read_text(encoding="utf-8"), "手で変えた")
        self.assertEqual(_run_install(str(self.repo), "--force"), 0)
        self.assertNotEqual(skill.read_text(encoding="utf-8"), "手で変えた")
        self.assertFalse(stale.exists())
        self.assertTrue(profile.is_file())
