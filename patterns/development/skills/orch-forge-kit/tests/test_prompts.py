"""prompts のテスト。全ひな形の置き換えの名前が表と一致し、過不足があれば落ちることを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import fsops, prompts
from forge_kit.errors import KitError


class PromptsTest(unittest.TestCase):
    def test_every_template_matches_table(self) -> None:
        on_disk = {path.name for path in prompts.TEMPLATES_DIR.glob("*.md")}
        self.assertEqual(on_disk, {file_name for file_name, _names in prompts.TEMPLATES.values()})
        for name, (file_name, expected) in prompts.TEMPLATES.items():
            with self.subTest(name=name):
                self.assertEqual(prompts.placeholders(fsops.read_text(prompts.TEMPLATES_DIR / file_name)), expected)

    def test_render(self) -> None:
        text = prompts.render("executor", {"skill_name": "dev-orch", "task_prompt": "在庫を減らして"})
        self.assertEqual(text.strip(), "/dev-orch 在庫を減らして")
        with self.assertRaises(KitError):
            prompts.render("executor", {"skill_name": "dev-orch"})


if __name__ == "__main__":
    unittest.main()
