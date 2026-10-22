"""escalation のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import escalation, fsops, policy, profile, trail
from tests import support

NOW = support.NOW


class EscalationTest(unittest.TestCase):
    def test_no_reasons(self) -> None:
        where, run_id = support.started(self)
        events = support.events(where, run_id)
        self.assertEqual(escalation.record(where, run_id, events, profile.DEFAULT_LIMITS, NOW), ())
        self.assertEqual(support.events(where, run_id), events)

    def test_fix_attempts(self) -> None:
        where, run_id = support.started(self)
        failures = [
            trail.verified(n, trail.CHECK, False, "t", NOW) for n in range(1, profile.DEFAULT_LIMITS.fix_attempts + 1)
        ]
        events = (*support.events(where, run_id), *failures)
        reasons = escalation.record(where, run_id, events, profile.DEFAULT_LIMITS, NOW)
        self.assertEqual(reasons, ("h2_too_many_failures",))
        last = support.events(where, run_id)[-1]
        self.assertEqual((last.kind, last.gate, last.number, last.tree), (trail.ESCALATED, policy.H2, 1, "t"))
        text = fsops.read_text(where.gate_path(run_id, policy.H2, 1))
        self.assertIn("続いた検査の失敗: 3 回（上限 3）", text)
