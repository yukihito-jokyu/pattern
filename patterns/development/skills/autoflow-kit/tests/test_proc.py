"""proc のテスト。"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from autoflow_kit import fsops, proc
from autoflow_kit.errors import CommandError
from tests import support


class ProcTest(unittest.TestCase):
    def test_shell_output_and_ci(self) -> None:
        result = proc.shell("echo out; echo err >&2; echo CI=$CI; exit 3", Path.cwd(), 10)
        self.assertEqual(result.exit_code, 3)
        self.assertFalse(result.timed_out)
        self.assertIn("err", result.output)
        self.assertIn("CI=1", result.tail)

    def test_shell_timeout(self) -> None:
        result = proc.shell("sleep 5", Path.cwd(), 1)
        self.assertTrue(result.timed_out)
        self.assertEqual(result.exit_code, proc.TIMEOUT_EXIT)

    def test_git_reads(self) -> None:
        where = support.make_repo(self)
        root = where.root
        self.assertEqual(proc.git_toplevel(root), root)
        self.assertEqual(proc.git_branch(root), "main")
        self.assertEqual(proc.git_user(root), support.EMAIL)
        self.assertEqual(proc.git_status(root), ())
        self.assertTrue(proc.git_is_ignored(root, ".autoflow/runs/x/trail.jsonl"))
        self.assertFalse(proc.git_is_ignored(root, "calc.py"))
        fsops.write_text(root / "new.txt", "x\n")
        self.assertEqual(proc.git_status(root), ("?? new.txt",))

    def test_git_commit_returns_head(self) -> None:
        where = support.make_repo(self)
        fsops.write_text(where.root / "new.txt", "x\n")
        proc.git_stage_all(where.root)
        sha = proc.git_commit(where.root, "件名\n")
        self.assertEqual(sha, proc.git_head(where.root))
        self.assertEqual(support.git(where.root, "log", "-1", "--format=%s").strip(), "件名")

    def test_git_failure(self) -> None:
        base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        with self.assertRaises(CommandError):
            proc.git_head(base)
