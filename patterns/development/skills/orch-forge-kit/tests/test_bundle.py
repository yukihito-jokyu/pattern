"""bundle のテスト。バンドルの決まり（RULES）の1つずつと、写し・置き換え・差分を確かめる。"""

from __future__ import annotations

import re
import unittest
from collections.abc import Mapping

from forge_kit import bundle, fsops, layout
from tests import support

SKILL_MD = f"{layout.SKILLS_DIR}/{support.SKILL}/{layout.SKILL_FILE}"
IMPLEMENTER = f"{layout.AGENTS_DIR}/{support.SKILL}-implementer.md"


class BundleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = support.make_repo(self) / layout.CLAUDE_DIR

    def edit(self, relative: str, old: str, new: str) -> None:
        path = self.root / relative
        text = fsops.read_text(path)
        self.assertIn(old, text)
        fsops.write_text(path, text.replace(old, new, 1))

    def problems(
        self, *, roles: Mapping[str, tuple[str, ...]] | None = None, fragments: frozenset[str] = frozenset()
    ) -> list[str]:
        return bundle.check(self.root, support.SKILL, roles=roles, fragments=fragments)

    def assert_rule(
        self,
        rule_id: str,
        *,
        roles: Mapping[str, tuple[str, ...]] | None = None,
        fragments: frozenset[str] = frozenset(),
    ) -> None:
        found = self.problems(roles=roles, fragments=fragments)
        self.assertTrue(any(problem.startswith(rule_id + " ") for problem in found), f"{rule_id} が落ちない: {found}")

    def test_fixture_passes(self) -> None:
        self.assertEqual(self.problems(), [])

    def test_every_rule_has_test(self) -> None:
        names = {name for name in dir(self) if name.startswith("test_b")}
        self.assertEqual(names, {f"test_{rule.id.lower()}" for rule in bundle.RULES})
        self.assertTrue(all(re.fullmatch(r"B\d{2}", rule.id) for rule in bundle.RULES))

    def test_b01(self) -> None:
        self.edit(SKILL_MD, "name: dev-orch", "name: other")
        self.assert_rule("B01")

    def test_b02(self) -> None:
        self.edit(SKILL_MD, "description: ", "when_to_use: " + "あ" * bundle.DESCRIPTION_MAX_CHARS + "\ndescription: ")
        self.assert_rule("B02")

    def test_b03(self) -> None:
        self.edit(SKILL_MD, "disable-model-invocation: true", "context: fork")
        self.assert_rule("B03")

    def test_b04(self) -> None:
        fsops.write_text(bundle.skill_dir(self.root, support.SKILL) / "notes.md", "メモ\n")
        self.assert_rule("B04")

    def test_b05(self) -> None:
        self.edit(SKILL_MD, "既定: 既存の書き方に合わせる", "")
        self.assert_rule("B05")

    def test_b06(self) -> None:
        self.edit(IMPLEMENTER, "name: dev-orch-implementer", "name: implementer")
        self.assert_rule("B06")

    def test_b07(self) -> None:
        self.edit(IMPLEMENTER, "tools:", "permissionMode: bypass\ntools:")
        self.assert_rule("B07")

    def test_b08(self) -> None:
        self.edit(IMPLEMENTER, "tools: Read,", "tools: Agent, Read,")
        self.assert_rule("B08")

    def test_b09(self) -> None:
        self.edit(SKILL_MD, "`dev-orch-reviewer` に任せる", "`dev-orch-checker` に任せる")
        self.assert_rule("B09")

    def test_b10(self) -> None:
        self.edit(IMPLEMENTER, "依頼の文", f"{bundle.TODO_MARK}: 依頼の文")
        self.assert_rule("B10")

    def test_b11(self) -> None:
        self.assert_rule("B11", roles={"implementer": ("Read",), "reviewer": ("Read", "Glob", "Grep")})

    def test_b12(self) -> None:
        self.assert_rule("B12", fragments=frozenset({"在庫のライブラリに機能を足す依頼"}))

    def test_b13(self) -> None:
        self.edit(IMPLEMENTER, "tools: Read, Write, Edit, Bash", "tools: Read, Write, Edit, Glob, Bash")
        self.assert_rule("B13")
        self.edit(IMPLEMENTER, "tools: Read, Write, Edit, Glob, Bash", "tools: Read, Write, Edit, Bash")
        self.edit(SKILL_MD, "## 手順", "## 手順\n\nGlob で探す。")
        self.assert_rule("B13")
        self.edit(SKILL_MD, "## 手順\n\nGlob で探す。", "## 手順")
        self.assertEqual(self.problems(), [])

    def test_copy_place_and_diff(self) -> None:
        other = self.root.parent / "proposed"
        bundle.copy(self.root, other, support.SKILL)
        self.assertEqual(bundle.diff(self.root, other, support.SKILL), "")
        fsops.write_text(other / IMPLEMENTER, "変えた\n")
        self.assertIn("+変えた", bundle.diff(self.root, other, support.SKILL))
        fsops.remove_tree(other / f"{layout.AGENTS_DIR}/{support.SKILL}-reviewer.md")
        where = support.make_where(self.root.parent, support.SKILL)
        bundle.place(where, support.SKILL, other)
        self.assertFalse((self.root / f"{layout.AGENTS_DIR}/{support.SKILL}-reviewer.md").exists())
        self.assertEqual(bundle.digest(self.root, support.SKILL), bundle.digest(other, support.SKILL))

    def test_strip_kit(self) -> None:
        fsops.write_text(self.root / "skills/forge-run/SKILL.md", "x\n")
        fsops.write_text(self.root / "agents/forge-grader.md", "x\n")
        bundle.strip_kit(self.root)
        self.assertFalse((self.root / "skills/forge-run").exists())
        self.assertFalse((self.root / "agents/forge-grader.md").exists())
        self.assertTrue(bundle.has_bundle(self.root, support.SKILL))

    def test_steps(self) -> None:
        text = fsops.read_text(self.root / SKILL_MD)
        self.assertEqual(len(bundle.steps(text)), 4)
        self.assertEqual(bundle.frontmatter(text)["name"], support.SKILL)


if __name__ == "__main__":
    unittest.main()
