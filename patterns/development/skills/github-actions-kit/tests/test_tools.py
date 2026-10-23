"""tools（外部ツールの出力の読み取り）のテスト。ツールは FakeRunner に置き換え、出力は固定の文字列にする。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from gha_kit import tools
from gha_kit.errors import ToolError
from gha_kit.findings import Finding
from gha_kit.proc import Result
from tests.support import FakeRunner

CI = ".github/workflows/ci.yml"
ZIZMOR = {
    "ident": "unpinned-uses",
    "desc": "unpinned action reference",
    "ignored": False,
    "locations": [
        {
            "symbolic": {"kind": "Primary", "key": {"Local": {"verbatim_path": CI}}, "annotation": "not pinned"},
            "concrete": {"location": {"start_point": {"row": 9}}},
        }
    ],
}


class ToolsTest(unittest.TestCase):
    def test_reads_yamllint_parsable_lines(self) -> None:
        line = f"{CI}:3:5: [error] wrong indentation: expected 4 but found 2 (indentation)\n"
        runner = FakeRunner({"yamllint": Result(1, line, "")})

        findings = tools.yamllint(Path.cwd(), [CI], runner)

        self.assertEqual(
            findings, [Finding(CI, 3, "TOOL-01", "[yamllint:indentation] wrong indentation: expected 4 but found 2")]
        )

    def test_reads_actionlint_json_and_maps_untrusted_input(self) -> None:
        record = {"kind": "expression", "filepath": CI, "line": 7, "message": '"x" is potentially untrusted'}
        runner = FakeRunner({"actionlint": Result(1, json.dumps([record]), "")})

        findings = tools.actionlint(Path.cwd(), [CI], runner)

        self.assertEqual([(f.rule, f.line) for f in findings], [("ERR-02", 7)])

    def test_reads_shellcheck_json_of_scripts_only(self) -> None:
        comment = {"file": ".github/scripts/build.sh", "line": 2, "code": 2086, "message": "Double quote"}
        runner = FakeRunner({"shellcheck": Result(1, json.dumps({"comments": [comment]}), "")})

        findings = tools.shellcheck(Path.cwd(), [".github/scripts/build.sh", ".github/scripts/tool.py"], runner)

        self.assertEqual(
            [f.render() for f in findings], ["TEST-01 .github/scripts/build.sh:2 [shellcheck:SC2086] Double quote"]
        )
        self.assertEqual(runner.calls[0][-1], ".github/scripts/build.sh")

    def test_reads_the_primary_location_of_zizmor(self) -> None:
        runner = FakeRunner({"zizmor": Result(13, json.dumps([ZIZMOR]), "")})

        findings = tools.zizmor(Path.cwd(), [CI], runner)

        self.assertEqual([(f.rule, f.line) for f in findings], [("DEP-06", 10)])
        self.assertIn("--offline", runner.calls[0])

    def test_reports_an_unreadable_file_and_checks_the_rest(self) -> None:
        broken = ".github/workflows/draft.yml"
        stderr = f"Caused by:\n    0: failed to load file://{broken} as workflow\n"
        runner = FakeRunner({"zizmor": [Result(1, "", stderr), Result(13, json.dumps([ZIZMOR]), "")]})

        findings = tools.zizmor(Path.cwd(), [CI, broken], runner)

        self.assertEqual([(f.path, f.rule) for f in findings], [(broken, "TEST-01"), (CI, "DEP-06")])

    def test_raises_a_tool_error_on_an_abnormal_exit(self) -> None:
        runner = FakeRunner({"zizmor": Result(1, "", "boom")})

        with self.assertRaises(ToolError):
            tools.zizmor(Path.cwd(), [CI], runner)


if __name__ == "__main__":
    unittest.main()
