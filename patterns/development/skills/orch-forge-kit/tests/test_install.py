"""install のテスト。配布物を対象のリポジトリへ写し、既存の変更を上書きしないことを確かめる。"""

from __future__ import annotations

import contextlib
import io
import json
import unittest

import install

from forge_kit import fsops
from tests import support


def run(*args: str) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return install.main(list(args))


class InstallTest(unittest.TestCase):
    def test_installs_kit(self) -> None:
        root = support.make_repo(self)
        self.assertEqual(run("--dest", str(root)), 0)
        self.assertTrue((root / ".forge/forge.py").is_file())
        self.assertTrue((root / ".forge/templates/prompts/analyst.md").is_file())
        self.assertTrue((root / ".claude/skills/forge-run/SKILL.md").is_file())
        self.assertTrue((root / ".claude/agents/forge-grader.md").is_file())
        self.assertTrue((root / ".claude/skills/dev-orch/SKILL.md").is_file())
        self.assertIn(".forge/work/", fsops.read_text(root / ".gitignore").splitlines())
        settings = json.loads(fsops.read_text(root / ".claude/settings.json"))
        self.assertEqual(settings["permissions"]["allow"], [install.CLI_RULE])

    def test_refuses_to_overwrite_changes(self) -> None:
        root = support.make_repo(self)
        run("--dest", str(root))
        fsops.write_text(root / ".claude/agents/forge-grader.md", "人が変えた\n")
        self.assertEqual(run("--dest", str(root)), 1)
        self.assertEqual(run("--dest", str(root), "--force"), 0)
        self.assertNotEqual(fsops.read_text(root / ".claude/agents/forge-grader.md"), "人が変えた\n")

    def test_add_cli_rule(self) -> None:
        root = support.make_repo(self)
        settings = root / ".claude/settings.json"
        fsops.write_text(settings, '{"permissions": {"allow": ["Read"]}, "hooks": {}}\n')
        run("--dest", str(root))
        run("--dest", str(root))
        data = json.loads(fsops.read_text(settings))
        self.assertEqual(data["permissions"]["allow"], ["Read", install.CLI_RULE])
        self.assertIn("hooks", data)
        fsops.write_text(settings, "{")
        self.assertFalse(install.add_cli_rule(root))
        self.assertEqual(fsops.read_text(settings), "{")


if __name__ == "__main__":
    unittest.main()
