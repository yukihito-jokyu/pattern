"""trail のテスト。記録の出来事を並べ、状態機械が決める次の段を確かめる。"""

from __future__ import annotations

import json
import unittest

from autoflow_kit import policy, trail
from autoflow_kit.errors import StageError
from tests import support

NOW = support.NOW
ORIGIN = trail.Origin("text", "", "", "題名")
FLOW = policy.Flow("feature", False, policy.MEDIUM, (), ("計画",))


def begun() -> list[trail.Event]:
    return [
        trail.started(ORIGIN, "autoflow/x", "t0", NOW),
        trail.verified(1, trail.BASELINE, True, "t0", NOW),
        trail.prompted(trail.PLANNER, 1, "", "t0", NOW),
        trail.planned(1, FLOW, "t0", NOW),
    ]


def checked(tree: str = "t1") -> list[trail.Event]:
    return [
        *begun(),
        trail.prompted(trail.BUILDER, 1, trail.FIRST, "t0", NOW),
        trail.built(1, trail.FIRST, (), tree, NOW),
        trail.verified(2, trail.CHECK, True, tree, NOW),
    ]


class TrailTest(unittest.TestCase):
    def test_encode_omits_defaults(self) -> None:
        line = trail.encode(trail.verified(1, trail.CHECK, False, "t", NOW))
        self.assertEqual(json.loads(line), {"kind": "verified", "at": NOW, "tree": "t", "number": 1, "mode": "check"})
        problems: list[str] = []
        self.assertEqual(
            trail.parse_events([json.loads(trail.encode(event)) for event in checked()], problems), tuple(checked())
        )
        self.assertEqual(problems, [])

    def test_first_event_must_be_started(self) -> None:
        problems: list[str] = []
        trail.parse_events([json.loads(trail.encode(trail.incident("x", "t", NOW)))], problems)
        self.assertEqual(problems, ["最初の出来事は started にする"])
        with self.assertRaises(StageError):
            trail.next_step([], "t")

    def test_start_and_baseline(self) -> None:
        events = begun()[:1]
        self.assertEqual(trail.next_step(events, "t0").mode, trail.BASELINE)
        failed = [*events, trail.verified(1, trail.BASELINE, False, "t0", NOW)]
        self.assertEqual(trail.next_step(failed, "t0").step, trail.STOPPED)
        self.assertEqual(trail.next_step(begun()[:2], "t0").step, trail.PLAN)

    def test_plan_prompted(self) -> None:
        current = trail.next_step(begun()[:3], "t0")
        self.assertEqual(
            (current.step, current.number, current.prompted, current.prompted_tree),
            (trail.PLAN, 1, trail.PLANNER, "t0"),
        )

    def test_h1_and_choices(self) -> None:
        flow = policy.Flow("feature", False, policy.MEDIUM, ("h1_new_dependency",), ())
        events = [*begun()[:3], trail.planned(1, flow, "t0", NOW)]
        current = trail.next_step(events, "t0")
        self.assertEqual((current.step, current.gate, current.number), (trail.DECIDE, policy.H1, 1))
        steps = {
            policy.PROCEED: trail.BUILD,
            policy.REPLAN: trail.PLAN,
            policy.ABORT: trail.STOPPED,
        }
        for choice, step in steps.items():
            decided = [*events, trail.decided(policy.H1, choice, "回答", "t0", "", NOW)]
            self.assertEqual(trail.next_step(decided, "t0").step, step)

    def test_repro_comes_first(self) -> None:
        flow = policy.Flow("fix", True, policy.MEDIUM, (), ())
        events = [*begun()[:3], trail.planned(1, flow, "t0", NOW)]
        self.assertEqual(trail.next_step(events, "t0").reason, trail.REPRO)
        events += [trail.built(1, trail.REPRO, (), "t1", NOW)]
        self.assertEqual(trail.next_step(events, "t1").mode, trail.REPRO)
        not_failing = [*events, trail.verified(2, trail.REPRO, False, "t1", NOW)]
        self.assertEqual(trail.next_step(not_failing, "t1").reason, trail.REPRO)
        reproduced = [*events, trail.verified(2, trail.REPRO, True, "t1", NOW)]
        self.assertEqual(trail.next_step(reproduced, "t1").reason, trail.FIRST)

    def test_check_then_risk_then_review(self) -> None:
        events = checked()
        self.assertEqual(trail.next_step(events, "t1").step, trail.RISK)
        events += [trail.risked(1, policy.LOW, False, ("理由",), "t1", NOW)]
        self.assertEqual(trail.next_step(events, "t1").step, trail.REVIEW)
        failed = [
            *events,
            trail.built(2, trail.FINDINGS, (), "t2", NOW),
            trail.verified(3, trail.CHECK, False, "t2", NOW),
        ]
        self.assertEqual(trail.next_step(failed, "t2").reason, trail.FAILED)

    def test_review_outcomes(self) -> None:
        events = [*checked(), trail.risked(1, policy.LOW, False, ("理由",), "t1", NOW)]
        found = [*events, trail.reviewed(1, (1, 0, 0), "t1", NOW)]
        self.assertEqual(
            (trail.next_step(found, "t1").step, trail.next_step(found, "t1").reason), (trail.BUILD, trail.FINDINGS)
        )
        clean = [*events, trail.reviewed(1, (0, 2, 1), "t1", NOW)]
        self.assertEqual(trail.next_step(clean, "t1").step, trail.HANDOFF)
        reported = [*clean, trail.handed_off(1, policy.LOW, "件名\n", "t1", NOW)]
        current = trail.next_step(reported, "t1")
        self.assertEqual((current.step, current.gate, current.number), (trail.DECIDE, policy.H3, 1))

    def test_changed_after_verify(self) -> None:
        events = checked("t1")
        self.assertEqual(trail.next_step(events, "t1").step, trail.RISK)
        self.assertEqual(trail.next_step(events, "t2").step, trail.VERIFY)
        reported = [
            *events,
            trail.risked(1, policy.LOW, False, ("理由",), "t1", NOW),
            trail.reviewed(1, (0, 0, 0), "t1", NOW),
            trail.handed_off(1, policy.LOW, "件名\n", "t1", NOW),
        ]
        self.assertEqual(trail.next_step(reported, "t2").step, trail.VERIFY)

    def test_approval_binds_tree(self) -> None:
        events = [
            *checked("t1"),
            trail.risked(1, policy.LOW, False, ("理由",), "t1", NOW),
            trail.reviewed(1, (0, 0, 0), "t1", NOW),
            trail.handed_off(1, policy.LOW, "件名\n", "t1", NOW),
            trail.decided(policy.H3, policy.APPROVE, "承認", "t1", "", NOW),
        ]
        self.assertEqual(trail.next_step(events, "t1").step, trail.COMMIT)
        self.assertEqual(trail.next_step(events, "t2").step, trail.VERIFY)
        done = [*events, trail.committed("c1", "t1", NOW)]
        self.assertEqual(trail.next_step(done, "t1").step, trail.DONE)

    def test_progress_resets(self) -> None:
        events = [
            *checked(),
            trail.verified(3, trail.CHECK, False, "t1", NOW),
            trail.verified(4, trail.CHECK, False, "t1", NOW),
        ]
        self.assertEqual(trail.progress(events).failed_checks, 2)
        events.append(trail.decided(policy.H2, policy.CONTINUE, "続けて", "t1", "", NOW))
        self.assertEqual(trail.progress(events).failed_checks, 0)
        events.append(trail.built(2, trail.HUMAN, ("鍵が無い",), "t1", NOW))
        self.assertEqual(trail.progress(events).blockers, ("鍵が無い",))

    def test_escalated_opens_h2(self) -> None:
        events = [*checked(), trail.escalate(1, ("h2_too_many_failures",), "t1", NOW)]
        current = trail.next_step(events, "t1")
        self.assertEqual((current.step, current.gate, current.number), (trail.DECIDE, policy.H2, 1))
        resumed = [*events, trail.decided(policy.H2, policy.CONTINUE, "続けて", "t1", "", NOW)]
        self.assertEqual(trail.next_step(resumed, "t1").reason, trail.HUMAN)
