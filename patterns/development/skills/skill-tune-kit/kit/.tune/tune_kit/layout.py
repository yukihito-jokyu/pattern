"""作業場所のファイルとディレクトリの名前と、パスの組み立てを受け持つ。ファイル名の文字列はこのモジュールだけに書く。"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from tune_kit.errors import KitError

TUNE_DIR = ".tune"
CLI = "python3 .tune/tune.py"
TARGETS_DIR = "targets"
WORK_DIR = "work"
SKILL_FILE = "SKILL.md"
GITIGNORE_FILE = ".gitignore"

PLAN_FILE = "plan.json"
PLAN_MD_FILE = "plan.md"
SPLIT_FILE = "split.json"
APPROVAL_FILE = "approval.json"
DATASET_DIR = "dataset"
CASES_FILE = "cases.json"
FILES_DIR = "files"
INPUT_DIR = "input"
EXPECTED_DIR = "expected"
VERSIONS_DIR = "versions"
RESULTS_DIR = "results"
ROUNDS_DIR = "rounds"
FINAL_DIR = "final"
REPORT_FILE = "report.md"
APPLIED_FILE = "applied.json"

# 1回の実行の作業場所（work/<target>/<run-key>/）
SANDBOX_DIR = "sandbox"
RUN_SKILL_DIR = "skill"
EXECUTOR_PROMPT_FILE = "executor-prompt.md"
RESPONSE_FILE = "response.md"
CHECKS_FILE = "checks.json"
CHANGES_FILE = "changes.patch"
GRADER_PROMPT_FILE = "grader-prompt.md"
GRADE_FILE = "grade.json"
RESULT_FILE = "result.json"

# ラウンド（rounds/r<N>/）と最後の監査（final/）
AUDIT_EVIDENCE_FILE = "audit-evidence.md"
AUDIT_PROMPT_FILE = "audit-prompt.md"
AUDIT_FILE = "audit.json"
AUDIT_MD_FILE = "audit.md"
FIXES_FILE = "fixes.json"
EVIDENCE_FILE = "evidence.md"
LEARNER_PROMPT_FILE = "learner-prompt.md"
PROPOSAL_FILE = "proposal.json"
PROPOSAL_MD_FILE = "proposal.md"
COMPARE_MD_FILE = "compare.md"
DECISION_FILE = "decision.json"

TEMPLATES_DIR = "templates"
PROMPTS_DIR = "prompts"
TEMPLATE_SUFFIX = ".md"

TARGET_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
FIRST_VERSION = "v0"


@dataclass(frozen=True)
class Layout:
    """1つの対象（target）の作業場所。root は利用者のリポジトリのルート。"""

    root: Path
    target: str

    @property
    def target_dir(self) -> Path:
        return self.root / TUNE_DIR / TARGETS_DIR / self.target

    @property
    def plan_path(self) -> Path:
        return self.target_dir / PLAN_FILE

    @property
    def plan_md_path(self) -> Path:
        return self.target_dir / PLAN_MD_FILE

    @property
    def split_path(self) -> Path:
        return self.target_dir / SPLIT_FILE

    @property
    def approval_path(self) -> Path:
        return self.target_dir / APPROVAL_FILE

    @property
    def dataset_dir(self) -> Path:
        return self.target_dir / DATASET_DIR

    @property
    def cases_path(self) -> Path:
        return self.dataset_dir / CASES_FILE

    @property
    def files_dir(self) -> Path:
        return self.dataset_dir / FILES_DIR

    def input_dir(self, case_id: str) -> Path:
        return self.files_dir / case_id / INPUT_DIR

    def expected_dir(self, case_id: str) -> Path:
        return self.files_dir / case_id / EXPECTED_DIR

    def version_dir(self, version: str) -> Path:
        return self.target_dir / VERSIONS_DIR / version

    def result_dir(self, version: str, case_id: str, run_no: int) -> Path:
        return self.target_dir / RESULTS_DIR / version / case_id / f"run-{run_no}"

    @property
    def work_dir(self) -> Path:
        return self.root / TUNE_DIR / WORK_DIR / self.target

    def run_dir(self, run_key: str) -> Path:
        return self.work_dir / run_key

    def round_dir(self, number: int) -> Path:
        return self.target_dir / ROUNDS_DIR / f"r{number}"

    @property
    def final_dir(self) -> Path:
        return self.target_dir / FINAL_DIR

    def audit_dir(self, number: int | None) -> Path:
        """ラウンドの監査は rounds/r<N>/、最後の監査（number が None）は final/。"""
        return self.final_dir if number is None else self.round_dir(number)

    @property
    def report_path(self) -> Path:
        return self.target_dir / REPORT_FILE

    @property
    def applied_path(self) -> Path:
        return self.target_dir / APPLIED_FILE

    def skill_dir(self, skill_path: str) -> Path:
        """計画の skill_path（リポジトリのルートからの相対パスか絶対パス）を絶対パスにする。"""
        return (self.root / skill_path).resolve()

    def display(self, path: Path) -> str:
        """人とサブエージェントに見せるパス。リポジトリの中ならルートからの相対パスにする。"""
        if path.is_relative_to(self.root):
            return path.relative_to(self.root).as_posix()
        return str(path)


def build_layout(root: Path, target: str) -> Layout:
    if not TARGET_ID.fullmatch(target):
        raise KitError(f"target の ID「{target}」は小文字の英数字とハイフン（64文字以内）にしてください")
    return Layout(root=root, target=target)


def build_version(number: int) -> str:
    return f"v{number}"


def build_run_key(version: str, case_id: str, run_no: int, case_sha: str) -> str:
    """実行の作業場所の名前。版を名前から読めないようにハッシュにする（採点役に版を伏せるため。ADR 0002）。"""
    return hashlib.sha256(f"{version}:{case_id}:{run_no}:{case_sha}".encode()).hexdigest()[:16]
