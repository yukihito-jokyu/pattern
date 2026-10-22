"""cli のテスト。依頼からコミットまでを、サブコマンドだけで通す。"""

from __future__ import annotations

import unittest
from pathlib import Path

from autoflow_kit import cli, layout, status
from tests import support


class CliTest(unittest.TestCase):
    def run_ok(self, root: Path, *args: str) -> str:
        code, out, err = support.run_cli(root, *args)
        self.assertEqual((code, err), (0, ""), out)
        return out

    def check_status(self, root: Path, run_id: str) -> list[str]:
        lines = self.run_ok(root, "status", "--run", run_id).splitlines()
        for line in lines:
            self.assertTrue(line.startswith(status.LINE_KINDS), line)
        return lines

    def test_whole_flow(self) -> None:
        where = support.make_repo(self)
        root, body = where.root, support.body_file(where)
        out = self.run_ok(root, "start", "--source", "text", "--title", "掛け算を足す", "--body-file", str(body))
        run_id = out.splitlines()[0].removeprefix("実行: ")
        self.assertTrue(layout.RUN_ID.match(run_id), out)
        steps = [
            ("verify", None),
            ("plan-new", lambda: support.act_planner(where, run_id)),
            ("plan-check", None),
            ("build-new", lambda: support.act_builder(where, run_id)),
            ("build-check", None),
            ("verify", None),
            ("risk-new", lambda: support.act_risk(where, run_id)),
            ("risk-check", None),
            ("review-new", lambda: support.act_finders(where, run_id)),
            ("review-collect", None),
            ("review-tally", None),
            ("handoff", None),
        ]
        for name, act in steps:
            out = self.run_ok(root, name, "--run", run_id)
            self.assertTrue(out.endswith(f"次: {layout.CLI} status --run {run_id}\n"))
            self.check_status(root, run_id)
            if act is not None:
                act()
        self.run_ok(root, "decide", "--run", run_id, "--gate", "H3", "--choice", "approve", "--answer", "承認します")
        self.assertIn("コミットした", self.run_ok(root, "commit", "--run", run_id))
        self.assertTrue(self.check_status(root, run_id)[-1].startswith("終了:"))
        self.assertIn("| コミットした実行 | 1 |", self.run_ok(root, "metrics"))

    def test_errors_exit_1(self) -> None:
        where = support.make_repo(self)
        code, out, err = support.run_cli(where.root, "status")
        self.assertEqual((code, out), (1, ""))
        self.assertTrue(err.startswith("エラー: 実行がありません"))

    def test_setup_commands(self) -> None:
        where = support.make_repo(self)
        self.assertIn("既にあります", support.run_cli(where.root, "setup-new")[2])
        self.assertIn("# プロファイル", self.run_ok(where.root, "setup-check"))
        self.assertIn("承認を記録した", self.run_ok(where.root, "setup-approve", "--answer", "承認します"))

    def test_every_step_has_help(self) -> None:
        self.assertEqual(set(cli.RUN_STEPS), set(cli.HELP))
