"""実行の結果から指標を計算し、候補を採るかを決める（ADR 0008）。副作用は持たない。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class RunScore:
    """1回の実行の採点。checks は (検査の ID, 合格したか) の組。"""

    case_id: str
    must_passed: bool
    checks: tuple[tuple[str, bool], ...]


@dataclass(frozen=True)
class Summary:
    """1つの版の1つの分割の指標。率は件数から分数で計算する。"""

    cases: int
    runs: int
    pass_rate: Fraction
    check_rate: Fraction
    case_rates: tuple[tuple[str, Fraction], ...]
    check_rates: tuple[tuple[str, Fraction], ...]


@dataclass(frozen=True)
class Decision:
    adopted: bool
    reason: str
    regressions: tuple[str, ...]
    overfit: bool


def compute_summary(scores: Sequence[RunScore]) -> Summary:
    """合格率はケースごとの合格の割合の平均、検査の通過率は全実行・全検査で通った割合。"""
    by_case: dict[str, list[bool]] = {}
    by_check: dict[str, list[bool]] = {}
    for score in scores:
        by_case.setdefault(score.case_id, []).append(score.must_passed)
        for check_id, passed in score.checks:
            by_check.setdefault(check_id, []).append(passed)
    case_rates = tuple((case_id, Fraction(sum(flags), len(flags))) for case_id, flags in sorted(by_case.items()))
    check_rates = tuple((check_id, Fraction(sum(flags), len(flags))) for check_id, flags in sorted(by_check.items()))
    total_checks = sum(len(flags) for flags in by_check.values())
    passed_checks = sum(sum(flags) for flags in by_check.values())
    return Summary(
        cases=len(by_case),
        runs=len(scores),
        pass_rate=sum((rate for _case, rate in case_rates), Fraction(0)) / len(case_rates)
        if case_rates
        else Fraction(0),
        check_rate=Fraction(passed_checks, total_checks) if total_checks else Fraction(0),
        case_rates=case_rates,
        check_rates=check_rates,
    )


def is_perfect(summary: Summary) -> bool:
    """全ケースの全実行が合格し、全検査が通った。"""
    return summary.runs > 0 and summary.pass_rate == 1 and summary.check_rate == 1


def list_regressions(current: Summary, candidate: Summary) -> tuple[str, ...]:
    """今の版では全実行が合格し、候補では全実行が不合格になったケース。"""
    candidate_rates = dict(candidate.case_rates)
    return tuple(case_id for case_id, rate in current.case_rates if rate == 1 and candidate_rates.get(case_id) == 0)


def compute_decision(
    current_val: Summary, candidate_val: Summary, current_train: Summary, candidate_train: Summary
) -> Decision:
    """検証用で退行が無く、合格率か（同点なら）検査の通過率が上がれば採る。"""
    regressions = list_regressions(current_val, candidate_val)
    improved_train = candidate_train.pass_rate > current_train.pass_rate or (
        candidate_train.pass_rate == current_train.pass_rate and candidate_train.check_rate > current_train.check_rate
    )
    if regressions:
        reason = f"検証用で退行したケースがある（{', '.join(regressions)}）"
        return Decision(adopted=False, reason=reason, regressions=regressions, overfit=improved_train)
    if candidate_val.pass_rate > current_val.pass_rate:
        return Decision(adopted=True, reason="検証用の合格率が上がった", regressions=(), overfit=False)
    if candidate_val.pass_rate == current_val.pass_rate and candidate_val.check_rate > current_val.check_rate:
        reason = "検証用の合格率は同じで、検査の通過率が上がった"
        return Decision(adopted=True, reason=reason, regressions=(), overfit=False)
    return Decision(
        adopted=False, reason="検証用の合格率も検査の通過率も上がらなかった", regressions=(), overfit=improved_train
    )
