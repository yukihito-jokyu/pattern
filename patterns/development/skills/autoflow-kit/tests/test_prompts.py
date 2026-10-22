"""prompts のテスト。ひな形と表の置き換えの名前が一致することを確かめる（PROC-02）。"""

from __future__ import annotations

import unittest

from autoflow_kit import fsops, policy, prompts
from autoflow_kit.errors import KitError


class PromptsTest(unittest.TestCase):
    def test_templates_match_table(self) -> None:
        for name, (file_name, expected) in prompts.TEMPLATES.items():
            text = fsops.read_text(prompts.TEMPLATES_DIR / file_name)
            self.assertEqual(prompts.placeholders(text), expected, name)

    def test_fill(self) -> None:
        _file_name, expected = prompts.TEMPLATES["risk"]
        values = {key: f"<{key}>" for key in expected}
        text = prompts.fill("risk", values)
        self.assertNotIn("${", text)
        self.assertIn("<output_path>", text)

    def test_fill_rejects_wrong_values(self) -> None:
        with self.assertRaises(KitError):
            prompts.fill("risk", {"diff_path": "x"})
        with self.assertRaises(KitError):
            prompts.fill("unknown", {})

    def test_finder_lists_every_lens(self) -> None:
        text = fsops.read_text(prompts.TEMPLATES_DIR / prompts.TEMPLATES["finder"][0])
        for lens in policy.LENSES:
            self.assertIn(f"`{lens.name}`", text)

    def test_agents_write_their_output(self) -> None:
        for name, (file_name, expected) in prompts.TEMPLATES.items():
            output = "report_path" if name == "builder" else "output_path"
            self.assertIn(output, expected)
            self.assertIn(f"完了: ${{{output}}}", fsops.read_text(prompts.TEMPLATES_DIR / file_name))
