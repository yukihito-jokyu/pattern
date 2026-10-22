"""対象のリポジトリの .autoflow/ の中の置き場とファイル名、実行の id と作業ブランチの名前を決める。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from autoflow_kit.errors import KitError

KIT_DIR = ".autoflow"
CLI = f"python3 {KIT_DIR}/autoflow.py"
CLAUDE_DIR = ".claude"
BRANCH_PREFIX = "autoflow/"

PROFILE_FILE = "profile.json"
APPROVAL_FILE = "profile-approval.json"
SETTINGS_LOCAL_FILE = "settings.local.json"
RUNS_DIR = "runs"
INTAKE_MD = "intake.md"

TASK_MD = "task.md"
GUIDE_MD = "guide.md"
TRAIL_FILE = "trail.jsonl"
PROMPT_MD = "prompt.md"
DIFF_FILE = "diff.patch"
PLAN_DIR = "plan"
PLAN_FILE = "plan.json"
PLAN_MD = "plan.md"
FLOW_FILE = "flow.json"
BUILD_DIR = "build"
REPORT_FILE = "report.json"
EVIDENCE_DIR = "evidence"
RISK_DIR = "risk"
JUDGMENT_FILE = "judgment.json"
REVIEW_DIR = "review"
CANDIDATES_FILE = "candidates.json"
RESULT_FILE = "result.json"
RESULT_MD = "result.md"
GATES_DIR = "gates"
PACKAGE_FILE = "package.json"
# レビューの指示のファイル。あれば setup がプロファイルの review.guide_files に入れる
GUIDE_FILES = ("REVIEW.md",)

# 取得元の種類と、ref（課題の番号）が要るか。取り方はスキルの references/sources.md の表に書く
SOURCES = {"text": False, "backlog": True, "redmine": True, "gitlab": True, "github": True}
RUN_ID = re.compile(r"^[0-9]{8}-[0-9]{6}(-[a-z0-9]+(-[a-z0-9]+)*)?$")
REF_SLUG = re.compile(r"[^a-z0-9]+")
SLUG_CHARS = 30


def make_run_id(now: str, ref: str) -> str:
    """開始の時刻（ISO 8601）と ref から実行の id を作る。例: 20261021-143000-proj-123。"""
    digits = re.sub(r"[^0-9]", "", now)[:14]
    if len(digits) != 14:
        raise KitError(f"時刻 {now!r} から実行の id を作れません")
    slug = REF_SLUG.sub("-", ref.lower()).strip("-")[:SLUG_CHARS].strip("-")
    base = f"{digits[:8]}-{digits[8:]}"
    return f"{base}-{slug}" if slug else base


def make_branch(run_id: str) -> str:
    return f"{BRANCH_PREFIX}{run_id}"


@dataclass(frozen=True)
class Layout:
    """対象のリポジトリのルートから、ファイルの置き場を求める。"""

    root: Path

    @property
    def kit_dir(self) -> Path:
        return self.root / KIT_DIR

    @property
    def runs_dir(self) -> Path:
        return self.kit_dir / RUNS_DIR

    @property
    def profile_path(self) -> Path:
        return self.kit_dir / PROFILE_FILE

    @property
    def approval_path(self) -> Path:
        return self.kit_dir / APPROVAL_FILE

    @property
    def intake_path(self) -> Path:
        return self.runs_dir / INTAKE_MD

    @property
    def settings_local_path(self) -> Path:
        return self.root / CLAUDE_DIR / SETTINGS_LOCAL_FILE

    def repo_path(self, relative: str) -> Path:
        """リポジトリのルートからの相対パス（プロファイルに書いたパス、検出するファイル）の置き場。"""
        return self.root / relative

    def relative(self, path: Path) -> str:
        """リポジトリのルートからの相対パス。スキルとサブエージェントに渡すパスはこの形にする。"""
        return path.relative_to(self.root).as_posix()

    def run_dir(self, run_id: str) -> Path:
        if not RUN_ID.match(run_id):
            raise KitError(f"実行の id {run_id!r} の形が違います（例: 20261021-143000-proj-123）")
        return self.runs_dir / run_id

    def trail_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / TRAIL_FILE

    def task_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / TASK_MD

    def guide_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / GUIDE_MD

    def snapshot_profile_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / PROFILE_FILE

    def plan_dir(self, run_id: str, plan_no: int) -> Path:
        return self.run_dir(run_id) / PLAN_DIR / str(plan_no)

    def plan_prompt_path(self, run_id: str, plan_no: int) -> Path:
        return self.plan_dir(run_id, plan_no) / PROMPT_MD

    def plan_path(self, run_id: str, plan_no: int) -> Path:
        return self.plan_dir(run_id, plan_no) / PLAN_FILE

    def plan_md_path(self, run_id: str, plan_no: int) -> Path:
        return self.plan_dir(run_id, plan_no) / PLAN_MD

    def flow_path(self, run_id: str, plan_no: int) -> Path:
        return self.plan_dir(run_id, plan_no) / FLOW_FILE

    def build_dir(self, run_id: str, attempt: int) -> Path:
        return self.run_dir(run_id) / BUILD_DIR / str(attempt)

    def build_prompt_path(self, run_id: str, attempt: int) -> Path:
        return self.build_dir(run_id, attempt) / PROMPT_MD

    def report_path(self, run_id: str, attempt: int) -> Path:
        return self.build_dir(run_id, attempt) / REPORT_FILE

    def evidence_path(self, run_id: str, seq: int) -> Path:
        return self.run_dir(run_id) / EVIDENCE_DIR / f"{seq}.json"

    def evidence_log_path(self, run_id: str, seq: int, check_id: str) -> Path:
        return self.run_dir(run_id) / EVIDENCE_DIR / f"{seq}-{check_id}.log"

    def risk_dir(self, run_id: str, risk_no: int) -> Path:
        return self.run_dir(run_id) / RISK_DIR / str(risk_no)

    def risk_prompt_path(self, run_id: str, risk_no: int) -> Path:
        return self.risk_dir(run_id, risk_no) / PROMPT_MD

    def risk_diff_path(self, run_id: str, risk_no: int) -> Path:
        return self.risk_dir(run_id, risk_no) / DIFF_FILE

    def judgment_path(self, run_id: str, risk_no: int) -> Path:
        return self.risk_dir(run_id, risk_no) / JUDGMENT_FILE

    def round_dir(self, run_id: str, round_no: int) -> Path:
        return self.run_dir(run_id) / REVIEW_DIR / f"round-{round_no}"

    def review_diff_path(self, run_id: str, round_no: int) -> Path:
        return self.round_dir(run_id, round_no) / DIFF_FILE

    def finder_prompt_path(self, run_id: str, round_no: int, lens: str) -> Path:
        return self.round_dir(run_id, round_no) / f"finder-{lens}-prompt.md"

    def findings_path(self, run_id: str, round_no: int, lens: str) -> Path:
        return self.round_dir(run_id, round_no) / f"finder-{lens}.json"

    def candidates_path(self, run_id: str, round_no: int) -> Path:
        return self.round_dir(run_id, round_no) / CANDIDATES_FILE

    def verifier_prompt_path(self, run_id: str, round_no: int, voter: int) -> Path:
        return self.round_dir(run_id, round_no) / f"verifier-{voter}-prompt.md"

    def votes_path(self, run_id: str, round_no: int, voter: int) -> Path:
        return self.round_dir(run_id, round_no) / f"verifier-{voter}.json"

    def result_path(self, run_id: str, round_no: int) -> Path:
        return self.round_dir(run_id, round_no) / RESULT_FILE

    def result_md_path(self, run_id: str, round_no: int) -> Path:
        return self.round_dir(run_id, round_no) / RESULT_MD

    def gate_path(self, run_id: str, gate: str, seq: int) -> Path:
        return self.run_dir(run_id) / GATES_DIR / f"{gate.lower()}-{seq}.md"

    def handoff_path(self, run_id: str, seq: int) -> Path:
        return self.run_dir(run_id) / f"handoff-{seq}.md"
