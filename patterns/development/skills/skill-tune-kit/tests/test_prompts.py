"""prompts のテスト。ひな形と置き換えの表の一致を確かめる（STATE-02）。"""

from __future__ import annotations

import unittest

from tune_kit import errors, fsops, prompts


class PromptsTest(unittest.TestCase):
    def test_templates_match_table(self) -> None:
        for name, expected in prompts.TEMPLATES.items():
            text = fsops.read_text(prompts.build_template_path(name))
            self.assertEqual(prompts.list_placeholders(text), expected, name)

    def test_render_rejects_missing_value(self) -> None:
        with self.assertRaises(errors.KitError):
            prompts.render_prompt("executor", {"skill_dir": "x"})

    def test_render_replaces_every_placeholder(self) -> None:
        values = {name: f"<{name}>" for name in prompts.TEMPLATES["grader"]}
        text = prompts.render_prompt("grader", values)
        self.assertNotIn("${", text)
        self.assertIn("<grade_path>", text)
