"""policy のテスト。H1・H2 の規則ごとに test_<規則の id> を置く（GATE-01）。"""

from __future__ import annotations

import dataclasses
import re
import unittest

from autoflow_kit import contracts, policy, profile
from tests import support

SETTINGS = profile.make_profile((support.UNIT,), ())


def plan(**overrides: object) -> contracts.Plan:
    problems: list[str] = []
    parsed = contracts.parse_plan(support.feature_plan(**overrides), [kind.name for kind in policy.KINDS], problems)
    assert not problems, problems
    return parsed


def stuck(failed: int = 0, rounds: int = 0, blockers: tuple[str, ...] = ()) -> tuple[str, ...]:
    return policy.h2_reasons(policy.Progress(failed, rounds, blockers), SETTINGS.limits)


class PolicyTest(unittest.TestCase):
    def test_rules_have_tests(self) -> None:
        for rule in (*policy.H1_RULES, *policy.H2_RULES):
            self.assertTrue(hasattr(self, f"test_{rule.id}"), f"規則 {rule.id} のテスト test_{rule.id} が無い")

    def test_h1_open_question(self) -> None:
        low = {"question": "名前", "default": "multiply", "impact": "low"}
        self.assertEqual(policy.h1_reasons(plan(open_questions=[low]), SETTINGS), ())
        high = {**low, "impact": "high"}
        self.assertEqual(policy.h1_reasons(plan(open_questions=[high]), SETTINGS), ("h1_open_question",))

    def test_h1_new_dependency(self) -> None:
        self.assertEqual(policy.h1_reasons(plan(dependencies_to_add=["numpy"]), SETTINGS), ("h1_new_dependency",))

    def test_h1_wide_scope(self) -> None:
        limit = SETTINGS.limits.max_scope_files
        self.assertEqual(policy.h1_reasons(plan(scope=[f"m{i}.py" for i in range(limit)]), SETTINGS), ())
        wide = plan(scope=[f"m{i}.py" for i in range(limit + 1)])
        self.assertEqual(policy.h1_reasons(wide, SETTINGS), ("h1_wide_scope",))

    def test_h1_human_paths(self) -> None:
        self.assertEqual(policy.h1_reasons(plan(scope=["CLAUDE.md"]), SETTINGS), ("h1_human_paths",))
        self.assertEqual(policy.h1_reasons(plan(scope=["src/auth/login.py"]), SETTINGS), ("h1_human_paths",))

    def test_h2_blocked(self) -> None:
        self.assertEqual(stuck(blockers=("権限が無い",)), ("h2_blocked",))

    def test_h2_too_many_failures(self) -> None:
        self.assertEqual(stuck(failed=SETTINGS.limits.fix_attempts - 1), ())
        self.assertEqual(stuck(failed=SETTINGS.limits.fix_attempts), ("h2_too_many_failures",))

    def test_h2_too_many_open_rounds(self) -> None:
        self.assertEqual(stuck(rounds=SETTINGS.limits.review_rounds - 1), ())
        self.assertEqual(stuck(rounds=SETTINGS.limits.review_rounds), ("h2_too_many_open_rounds",))

    def test_merge_tier(self) -> None:
        self.assertEqual(policy.merge_tier(policy.HIGH, policy.LOW), policy.HIGH)
        self.assertEqual(policy.merge_tier(policy.LOW, policy.MEDIUM), policy.MEDIUM)
        self.assertEqual(policy.merge_tier(policy.MEDIUM, policy.LOW), policy.MEDIUM)

    def test_tier_of_changes(self) -> None:
        low = policy.tier_of_changes(("docs/a.md", "tests/test_calc.py"), 10, SETTINGS)
        self.assertEqual(low.tier, policy.LOW)
        self.assertEqual(policy.tier_of_changes(("calc.py",), 10, SETTINGS).tier, policy.MEDIUM)
        self.assertEqual(policy.tier_of_changes(("package.json",), 1, SETTINGS).tier, policy.HIGH)
        self.assertEqual(policy.tier_of_changes(("docs/a.md",), 5000, SETTINGS).tier, policy.HIGH)
        human = policy.tier_of_changes(("REVIEW.md",), 1, SETTINGS)
        self.assertEqual((human.tier, human.human_files), (policy.MEDIUM, ("REVIEW.md",)))

    def test_has_match(self) -> None:
        self.assertTrue(policy.has_match("AGENTS.md", ("**/AGENTS.md",)))
        self.assertTrue(policy.has_match("a/b/AGENTS.md", ("**/AGENTS.md",)))
        self.assertFalse(policy.has_match("AGENTS.txt", ("**/AGENTS.md",)))

    def test_check_plan(self) -> None:
        fix = dataclasses.replace(plan(), kind="fix")
        self.assertEqual(len(policy.check_plan(fix)), 2)
        self.assertEqual(
            policy.check_plan(dataclasses.replace(plan(), repro="make test")),
            ["repro は種類 feature では書かない（再現の手順は不具合の修正だけ）"],
        )

    def test_compose(self) -> None:
        flow = policy.compose(dataclasses.replace(plan(), kind="fix", repro="x", root_cause="y"), SETTINGS)
        self.assertTrue(flow.repro)
        self.assertIn("再現のテスト", flow.steps)
        self.assertEqual(flow.steps[-2:], (f"{policy.H3} 最終承認", "コミット"))
        self.assertEqual(policy.compose(plan(dependencies_to_add=["x"]), SETTINGS).steps[1], f"{policy.H1} 方向の確認")

    def test_gates_have_unique_options(self) -> None:
        self.assertEqual([gate.id for gate in policy.GATES], [policy.H0, policy.H1, policy.H2, policy.H3])
        for gate in policy.GATES:
            names = [option.name for option in gate.options]
            self.assertEqual(len(names), len(set(names)))

    def test_depths_match_lenses(self) -> None:
        lenses = {lens.name for lens in policy.LENSES}
        for depth in policy.DEPTHS:
            self.assertLessEqual(set(depth.lenses), lenses)
            self.assertLessEqual(depth.threshold, depth.verifiers)

    def test_rule_ids_match_functions(self) -> None:
        rules: list[policy.PlanRule | policy.ProgressRule] = [*policy.H1_RULES, *policy.H2_RULES]
        for rule in rules:
            name = re.sub(r"^_(is|has)_", "", rule.test.__name__)
            self.assertEqual(rule.id.split("_", 1)[1], name, f"規則 {rule.id} の判定の関数 {rule.test.__name__}")
