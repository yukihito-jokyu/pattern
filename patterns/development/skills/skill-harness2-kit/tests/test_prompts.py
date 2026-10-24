"""prompts のテスト。ひな形のファイルと TEMPLATES の表の一致（STATE-02）。"""

from __future__ import annotations

import re
import unittest

from h2_kit import prompts
from h2_kit.errors import KitError
from tests import support

TEMPLATES_DIR = support.TEMPLATES / "prompts"


class PromptsTest(unittest.TestCase):
    def test_every_file_is_in_the_table(self) -> None:
        files = sorted(path.stem for path in TEMPLATES_DIR.glob("*.md"))
        self.assertEqual(files, sorted(prompts.TEMPLATES))

    def test_placeholders_match_the_table(self) -> None:
        for name, keys in prompts.TEMPLATES.items():
            with self.subTest(name=name):
                found = prompts.list_placeholders(prompts.read_template(TEMPLATES_DIR, name))
                plain = [key for key in found if not key.startswith(prompts.BLOCK_PREFIX)]
                self.assertEqual(sorted(plain), sorted(keys))
                for block in (key for key in found if key.startswith(prompts.BLOCK_PREFIX)):
                    self.assertIn(prompts.build_block_name(block), prompts.TEMPLATES)

    def test_render_fills_blocks_and_drops_comments(self) -> None:
        values = {"job": "仕事", "layout": "- `context/task.md`"}
        text = prompts.render_prompt(TEMPLATES_DIR, "mission", values)
        self.assertNotIn("<!--", text)
        self.assertNotIn("${", text)
        self.assertIsNone(re.search(r"\n{3,}", text))

    def test_missing_value_raises(self) -> None:
        with self.assertRaises(KitError):
            prompts.render_prompt(TEMPLATES_DIR, "mission", {"job": "仕事"})

    def test_part_is_empty_when_not_wanted(self) -> None:
        self.assertEqual(prompts.render_part(TEMPLATES_DIR, "_round", {"t": "1"}, when=False), "")
