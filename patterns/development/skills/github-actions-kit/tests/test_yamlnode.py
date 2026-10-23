"""yamlnode（行番号と書き方を持つ YAML の木）のテスト。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gha_kit import yamlnode
from gha_kit.yamlnode import Map, Scalar
from tests.support import write

WORKFLOW = """\
# 目的
on:
  push:
env:
  VERSION: "3.12"
jobs:
  test:
    steps:
      - &checkout
        run: |
          make test
      - *checkout
"""


class LoadTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_keeps_the_on_key_as_text_with_its_line(self) -> None:
        write(self.root, "ci.yml", WORKFLOW)

        root = yamlnode.load(self.root, "ci.yml").root

        assert isinstance(root, Map)
        self.assertEqual(root.names(), ["on", "env", "jobs"])
        self.assertEqual(root.key_line("on"), 2)

    def test_records_the_quote_and_block_styles(self) -> None:
        write(self.root, "ci.yml", WORKFLOW)
        root = yamlnode.load(self.root, "ci.yml").root
        assert isinstance(root, Map)

        version = yamlnode.as_map(root.get("env"))

        self.assertEqual(version.get("VERSION") if version else None, Scalar("3.12", 5, '"'))

    def test_records_anchor_and_alias_lines(self) -> None:
        write(self.root, "ci.yml", WORKFLOW)

        self.assertEqual(yamlnode.load(self.root, "ci.yml").anchor_lines, (9, 12))

    def test_reports_broken_yaml_without_a_root(self) -> None:
        write(self.root, "ci.yml", "on: [push\n")

        doc = yamlnode.load(self.root, "ci.yml")

        self.assertIsNone(doc.root)
        self.assertNotEqual(doc.error, "")


if __name__ == "__main__":
    unittest.main()
