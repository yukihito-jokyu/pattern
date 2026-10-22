"""テストの共通部品。見本のリポジトリを一時ディレクトリに git で作り、サブエージェントの代わりに出力を書く。"""

from __future__ import annotations

import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from collections.abc import Mapping, Sequence
from pathlib import Path

from autoflow_kit import (
    building,
    cli,
    context,
    fsops,
    handoff,
    intake,
    planning,
    policy,
    profile,
    reviewing,
    risking,
    setup,
    shape,
    trail,
    verifying,
    workspace,
)
from autoflow_kit.layout import Layout

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE_REPO = FIXTURES / "sample-repo"
NOW = "2026-10-21T14:30:00+09:00"
LATER = "2026-10-21T15:00:00+09:00"
RUN_ID = "20261021-143000"
EMAIL = "dev@example.com"
ANSWER = "これで進めてください"
UNIT = profile.Command("unit", "python3 -B -m unittest discover -s tests -t .", 60)
GITIGNORE = ".autoflow/runs/\n__pycache__/\n"
TASK_BODY = "calc に掛け算の関数 multiply を足してください。"
CALC_FEATURE = '''"""見本の計算の関数。"""


def add(a: int, b: int) -> int:
    return a + b


def clamp(value: int, low: int, high: int) -> int:
    """value を low 以上 high 以下に収める。"""
    return max(low, value)


def multiply(a: int, b: int) -> int:
    return a * b
'''
TEST_FEATURE = """import unittest

import calc


class CalcTest(unittest.TestCase):
    def test_add(self) -> None:
        self.assertEqual(calc.add(2, 3), 5)

    def test_clamp_low(self) -> None:
        self.assertEqual(calc.clamp(-1, 0, 10), 0)

    def test_multiply(self) -> None:
        self.assertEqual(calc.multiply(2, 3), 6)
"""
FEATURE_FILES = {"calc.py": CALC_FEATURE, "tests/test_calc.py": TEST_FEATURE}


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=root, capture_output=True, check=True, text=True)
    return completed.stdout


def make_repo(test: unittest.TestCase, settings: profile.Profile | None = None) -> Layout:
    """見本のリポジトリを git で作り、承認済みのプロファイルを置いてコミットする。"""
    base = Path(tempfile.mkdtemp()).resolve()
    test.addCleanup(shutil.rmtree, base, ignore_errors=True)
    root = base / "repo"
    shutil.copytree(SAMPLE_REPO, root)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", EMAIL)
    git(root, "config", "user.name", "dev")
    git(root, "config", "commit.gpgsign", "false")
    fsops.write_text(root / ".gitignore", GITIGNORE)
    where = Layout(root)
    approve(where, settings or profile.make_profile((UNIT,), ()))
    commit_all(where, "init")
    return where


def approve(where: Layout, settings: profile.Profile) -> None:
    fsops.write_json(where.profile_path, shape.to_data(settings))
    setup.setup_approve(where, "承認します", NOW, allow=False)


def commit_all(where: Layout, message: str) -> None:
    git(where.root, "add", "-A")
    git(where.root, "commit", "-q", "-m", message)


def write_files(where: Layout, files: Mapping[str, str]) -> None:
    for relative, content in files.items():
        fsops.write_text(where.repo_path(relative), content)


def body_file(where: Layout, text: str = TASK_BODY) -> Path:
    """依頼の本文。リポジトリの外に置く（作業ツリーを汚さない）。"""
    path = where.root.parent / "body.md"
    fsops.write_text(path, text)
    return path


def started(test: unittest.TestCase, settings: profile.Profile | None = None) -> tuple[Layout, str]:
    where = make_repo(test, settings)
    origin = trail.Origin("text", "", "", "掛け算を足す")
    intake.start(where, origin, body_file(where), NOW)
    return where, RUN_ID


def events(where: Layout, run_id: str) -> tuple[trail.Event, ...]:
    return workspace.load_trail(where, run_id)


def feature_plan(**overrides: object) -> dict[str, object]:
    plan: dict[str, object] = {
        "kind": "feature",
        "goal": "calc に掛け算の関数を足す",
        "non_goals": ["clamp の不具合は直さない"],
        "scope": ["calc.py", "tests/test_calc.py"],
        "criteria": [
            {
                "id": "C1",
                "text": "multiply が積を返す",
                "check": "command",
                "run": 'python3 -B -c "import calc; assert calc.multiply(2, 3) == 6"',
            },
            {"id": "C2", "text": "既存の関数と同じ書き方である", "check": "review", "run": ""},
        ],
        "repro": "",
        "root_cause": "",
        "open_questions": [],
        "dependencies_to_add": [],
        "revert": "このコミットを git revert する",
        "commit_subject": "PROJ-1 掛け算の関数を足す",
    }
    plan.update(overrides)
    return plan


def fix_plan() -> dict[str, object]:
    return feature_plan(
        kind="fix",
        goal="clamp が上限を超えた値を返さないようにする",
        scope=["calc.py", "tests/test_calc.py"],
        criteria=[{"id": "C1", "text": "上限を超えた値は上限になる", "check": "review", "run": ""}],
        repro='python3 -B -c "import calc; assert calc.clamp(11, 0, 10) == 10"',
        root_cause="clamp が high を見ていない",
        commit_subject="PROJ-2 clamp の上限を直す",
    )


def act_planner(where: Layout, run_id: str, plan: Mapping[str, object] | None = None) -> None:
    number = trail.count(events(where, run_id), trail.PLANNED) + 1
    fsops.write_json(where.plan_path(run_id, number), dict(plan or feature_plan()))


def act_builder(
    where: Layout,
    run_id: str,
    files: Mapping[str, str] | None = None,
    *,
    resolutions: Sequence[Mapping[str, object]] = (),
    blockers: Sequence[str] = (),
) -> None:
    """実装役の代わりに、ファイルを書き、報告を書く。"""
    write_files(where, FEATURE_FILES if files is None else files)
    attempt = trail.count(events(where, run_id), trail.BUILT) + 1
    report = {
        "summary": "multiply を足した",
        "explanation": "calc.py に multiply を足し、テストを足した",
        "resolutions": [dict(item) for item in resolutions],
        "blockers": list(blockers),
    }
    fsops.write_json(where.report_path(run_id, attempt), report)


def act_risk(where: Layout, run_id: str, tier: str = policy.LOW, *, human_required: bool = False) -> None:
    number = trail.count(events(where, run_id), trail.RISKED) + 1
    judgment = {"tier": tier, "human_required": human_required, "reasons": ["小さな追加"], "attention_files": []}
    fsops.write_json(where.judgment_path(run_id, number), judgment)


def finding(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "title": "負の数の扱いが決まっていない",
        "file": "calc.py",
        "line": 14,
        "category": "bug",
        "evidence": "multiply(-1, 2) の結果を確かめるテストが無い",
        "bug_class": "境界の値",
        "other_locations": [],
        "pre_existing": False,
    }
    item.update(overrides)
    return item


def depth(where: Layout, run_id: str) -> policy.Depth:
    risk = trail.last(events(where, run_id), trail.RISKED)
    return policy.depth_of(risk.tier if risk is not None else policy.HIGH)


def act_finders(where: Layout, run_id: str, found: Mapping[str, Sequence[Mapping[str, object]]] | None = None) -> None:
    """探索役の代わりに、観点ごとの指摘を書く。found に無い観点は指摘なし。"""
    round_no = trail.count(events(where, run_id), trail.REVIEWED) + 1
    for lens in depth(where, run_id).lenses:
        items = [dict(item) for item in (found or {}).get(lens, ())]
        fsops.write_json(where.findings_path(run_id, round_no, lens), {"findings": items})


def act_verifiers(where: Layout, run_id: str, ballots: Sequence[Mapping[str, tuple[str, str]]] | None = None) -> None:
    """検証役の代わりに投票する。ballots[k] は {候補の id: (verdict, tag)}。無い候補は real・important。"""
    round_no = trail.count(events(where, run_id), trail.REVIEWED) + 1
    ids = [item.id for item in workspace.load_candidates(where, run_id, round_no)]
    for voter in range(1, depth(where, run_id).verifiers + 1):
        chosen = ballots[voter - 1] if ballots and voter <= len(ballots) else {}
        votes = []
        for candidate_id in ids:
            verdict, tag = chosen.get(candidate_id, ("real", policy.IMPORTANT))
            votes.append({"id": candidate_id, "verdict": verdict, "tag": tag, "reason": "差分で確かめた"})
        fsops.write_json(where.votes_path(run_id, round_no, voter), {"votes": votes})


def planned(
    test: unittest.TestCase, plan: Mapping[str, object] | None = None, settings: profile.Profile | None = None
) -> tuple[Layout, str]:
    """開始・作業の前の検証・計画まで済ませる。"""
    where, run_id = started(test, settings)
    verifying.verify(where, run_id, NOW)
    planning.plan_new(where, run_id, NOW)
    act_planner(where, run_id, plan)
    planning.plan_check(where, run_id, NOW)
    return where, run_id


def build(
    where: Layout,
    run_id: str,
    files: Mapping[str, str] | None = None,
    *,
    resolutions: Sequence[Mapping[str, object]] = (),
    blockers: Sequence[str] = (),
) -> None:
    """実装の1回（プロンプト、実装役、報告の検証）。"""
    building.build_new(where, run_id, NOW)
    act_builder(where, run_id, files, resolutions=resolutions, blockers=blockers)
    building.build_check(where, run_id, NOW)


def verified(test: unittest.TestCase) -> tuple[Layout, str]:
    """計画・実装・検証まで済ませる（機能の追加）。"""
    where, run_id = planned(test)
    build(where, run_id)
    verifying.verify(where, run_id, NOW)
    return where, run_id


def risk(where: Layout, run_id: str, tier: str = policy.LOW) -> None:
    """リスクの判定の1回（プロンプト、判定役、段の決定）。"""
    risking.risk_new(where, run_id, NOW)
    act_risk(where, run_id, tier)
    risking.risk_check(where, run_id, NOW)


def risked(test: unittest.TestCase, tier: str = policy.LOW) -> tuple[Layout, str]:
    where, run_id = verified(test)
    risk(where, run_id, tier)
    return where, run_id


def review_round(
    where: Layout,
    run_id: str,
    found: Mapping[str, Sequence[Mapping[str, object]]] | None = None,
    ballots: Sequence[Mapping[str, tuple[str, str]]] | None = None,
) -> None:
    """レビューの1ラウンド（探索、候補、投票、集計）。"""
    reviewing.review_new(where, run_id, NOW)
    act_finders(where, run_id, found)
    reviewing.review_collect(where, run_id, NOW)
    act_verifiers(where, run_id, ballots)
    reviewing.review_tally(where, run_id, NOW)


def handed_off(test: unittest.TestCase) -> tuple[Layout, str]:
    """指摘の無いレビューを通し、報告書まで済ませる。"""
    where, run_id = risked(test)
    review_round(where, run_id)
    handoff.handoff(where, run_id, NOW)
    return where, run_id


def run_cli(root: Path, *args: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(args), root)
    return code, out.getvalue(), err.getvalue()


def next_step(where: Layout, run_id: str) -> trail.Next:
    return context.peek(where, run_id).next
