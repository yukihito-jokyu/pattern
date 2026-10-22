"""install のテスト。"""

from __future__ import annotations

import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path

import install

from autoflow_kit import fsops


class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dest = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.dest, ignore_errors=True)

    def run_install(self, *args: str) -> tuple[int, str]:
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = install.main(["--dest", str(self.dest), *args])
        return code, err.getvalue()

    def test_install_copies_kit(self) -> None:
        fsops.write_text(self.dest / ".gitignore", "node_modules/")
        self.assertEqual(self.run_install(), (0, ""))
        for relative in (
            ".autoflow/autoflow.py",
            ".autoflow/autoflow_kit/trail.py",
            ".autoflow/templates/prompts/finder.md",
            ".claude/skills/autoflow/SKILL.md",
            ".claude/agents/autoflow-builder.md",
        ):
            self.assertTrue((self.dest / relative).is_file(), relative)
        self.assertFalse(list(self.dest.rglob("__pycache__")))
        lines = fsops.read_text(self.dest / ".gitignore").splitlines()
        self.assertEqual(lines, ["node_modules/", *install.GITIGNORE_LINES])

    def test_reinstall_keeps_user_changes(self) -> None:
        self.run_install()
        self.assertEqual(self.run_install(), (0, ""))
        skill = self.dest / ".claude/skills/autoflow/SKILL.md"
        fsops.write_text(skill, "人が変えた\n")
        code, err = self.run_install()
        self.assertEqual(code, 1)
        self.assertIn(".claude/skills/autoflow", err)
        self.assertEqual(fsops.read_text(skill), "人が変えた\n")
        self.assertEqual(self.run_install("--force")[0], 0)
        self.assertNotEqual(fsops.read_text(skill), "人が変えた\n")
        self.assertEqual(install.missing_gitignore_lines(self.dest), [])

    def test_missing_dest(self) -> None:
        shutil.rmtree(self.dest)
        self.assertEqual(self.run_install()[0], 1)
