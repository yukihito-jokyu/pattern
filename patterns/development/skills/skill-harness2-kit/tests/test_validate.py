"""validate のテスト。STATE-06 の表の項目ごとに確かめる。"""

from __future__ import annotations

import unittest

from h2_kit import skilltree, validate

SKILL = "---\nname: s\ndescription: 議事録を整える\n---\n\n# 手順\n\n書式は `references/format.md` を読む。\n"
BASE = skilltree.build_tree({"SKILL.md": SKILL, "references/format.md": "# 書式\n"})


def _build_with(path: str, text: str) -> skilltree.SkillTree:
    return skilltree.build_replaced(BASE, path, text)


class ValidateTest(unittest.TestCase):
    def assert_rejected(self, tree: skilltree.SkillTree, word: str, rejected: list[str] | None = None) -> None:
        problems = validate.check_tree(tree, BASE, rejected or [])
        self.assertTrue(any(word in problem for problem in problems), problems)

    def test_base_passes(self) -> None:
        self.assertEqual(validate.check_tree(BASE, BASE, []), [])

    def test_file_off_the_surface(self) -> None:
        self.assert_rejected(BASE, "編集面の外", ["notes.txt"])

    def test_frontmatter(self) -> None:
        self.assert_rejected(_build_with("SKILL.md", SKILL.replace("name: s", "name: t")), "description 以外")
        self.assert_rejected(_build_with("SKILL.md", SKILL.replace("議事録を整える", "")), "description が空")
        self.assert_rejected(_build_with("SKILL.md", SKILL.replace("議事録を整える", "x" * 1025)), "1024")
        self.assert_rejected(_build_with("SKILL.md", SKILL.replace("議事録を整える", "<b>")), "< か >")
        self.assert_rejected(skilltree.build_tree({"references/format.md": "x"}), "SKILL.md がありません")

    def test_body_over_500_lines(self) -> None:
        self.assert_rejected(_build_with("SKILL.md", SKILL + "行\n" * 500), "500")

    def test_unnamed_reference(self) -> None:
        self.assert_rejected(_build_with("references/extra.md", "# 追加\n"), "名指しされていません")

    def test_named_path_must_exist(self) -> None:
        self.assert_rejected(
            _build_with("SKILL.md", SKILL + "最後に `scripts/check.py` を動かす。\n"), "木にありません"
        )

    def test_more_injections(self) -> None:
        self.assert_rejected(_build_with("SKILL.md", SKILL + "今の日付: !`date`\n"), "動的な挿入")

    def test_script_must_compile(self) -> None:
        tree = _build_with("SKILL.md", SKILL + "`scripts/check.py` を動かす。\n")
        self.assert_rejected(skilltree.build_replaced(tree, "scripts/check.py", "def broken(:\n"), "コンパイル")

    def test_grader_marker(self) -> None:
        self.assert_rejected(_build_with("references/format.md", '# 書式\n"pass_rate" を見る\n'), "採点の印")

    def test_problems_already_in_the_base_are_not_counted(self) -> None:
        base = skilltree.build_replaced(BASE, "references/old.md", "# 古い\n")
        self.assertEqual(validate.check_tree(base, base, []), [])

    def test_autolink_names_a_reference_with_its_heading(self) -> None:
        tree, linked = validate.build_autolinked(_build_with("references/extra.md", "# 追加の確かめ\n"))
        self.assertEqual(linked, ["references/extra.md"])
        self.assertIn("- 追加の確かめを確かめるときは `references/extra.md` を読む。", tree.find("SKILL.md") or "")
        self.assertEqual(validate.check_tree(tree, BASE, []), [])

    def test_autolink_does_not_exceed_500_lines(self) -> None:
        long_skill = SKILL + "行\n" * (500 - len(SKILL.splitlines()))
        tree = skilltree.build_tree({"SKILL.md": long_skill, "references/format.md": "x", "references/extra.md": "y"})
        self.assertEqual(validate.build_autolinked(tree)[1], [])
