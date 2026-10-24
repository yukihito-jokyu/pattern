"""作業場所のパス、ファイル名、ラベル、モードの定数。ほかのモジュールはここの定数だけを使う（CODE-06）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from h2_kit.errors import InvalidFileError

H2_DIR = ".h2"
TARGETS_DIR = "targets"
TEMPLATES_DIR = "templates"
PROMPTS_DIR = "prompts"
CLAUDE_DIR = ".claude"
SKILLS_DIR = "skills"
GIT_DIR = ".git"

# 対象（target）の中
PROFILE_FILE = "profile.json"
TASKS_DIR = "tasks"
TASK_FILE = "task.md"
TASK_WORKSPACE_DIR = "workspace"
CHECKS_FILE = "checks.json"
PLAN_FILE = "plan.md"
APPROVAL_FILE = "approval.json"
ADOPTED_FILE = "adopted.json"
RUNS_DIR = "runs"

# ラウンドとタスクの記録
BASE_SKILL_DIR = "base-skill"
LIBRARY_DIR = "library"
INDEX_FILE = "INDEX.md"
EXPERIENCE_FILE = "EXPERIENCE.md"
ENTRY_SKILL_DIR = "skill"
ROLLOUTS_DIR = "rollouts"
HARNESSES_DIR = "harnesses"
SESSIONS_DIR = "sessions"
SELECTION_DIR = "selection"
REFLECTION_DIR = "reflection"
SUMMARY_FILE = "summary.json"
JUDGED_FILE = "judged.json"

# 1回の実行
STREAM_FILE = "stream.jsonl"
STDERR_FILE = "stderr.txt"
TRAJECTORY_FILE = "trajectory.md"
DELIVERABLE_FILE = "deliverable.md"
REPLY_FILE = "reply.md"
OUTPUT_DIR = "output"
RUN_FILE = "run.json"

# 編集・選択・振り返りのセッション
CONTEXT_DIR = "context"
HARNESS_DIR = "harness"
BASE_HARNESS_DIR = "base_harness"
SOURCE_DIR = "source"
DECISIONS_DIR = "decisions"
DELIVERABLES_DIR = "deliverables"
POOL_DIR = "pool"
CANDIDATES_DIR = "candidates"
HARNESS_DIFF_FILE = "harness.diff"
POOL_ROLLOUT_FILE = "rollout.md"
PRODUCED_FILE = "produced.md"
ADOPTION_FILE = "adoption.json"
MISSION_FILE = "MISSION.md"
SESSION_FILE = "session.json"
EDITS_FILE = "edits.md"

# スキルの木
SKILL_FILE = "SKILL.md"
REFERENCES_DIR = "references"
SCRIPTS_DIR = "scripts"
ASSETS_DIR = "assets"
MD_SUFFIX = ".md"
SCRIPT_SUFFIXES = (".py", ".sh")
PY_SUFFIX = ".py"

# ラベルの接頭辞とモード（STATE-07 の台帳はこの綴りで数える）
BASE = "base"
INV = "inv"
DOM = "dom"
AGG = "agg"
CHECKPOINT = "c"
PARALLEL = "parallel"
SEQUENTIAL = "sequential"
MODES = (PARALLEL, SEQUENTIAL)

NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


def build_label(prefix: str, index: int) -> str:
    """ラベル（`base1`、`inv2`、`agg1`、`c3`）を作る。"""
    return f"{prefix}{index}"


def build_session_name(label: str, attempt: int) -> str:
    return f"{label}.a{attempt}"


def is_base_label(label: str) -> bool:
    return label.startswith(BASE)


def require_name(kind: str, name: str) -> str:
    """対象やタスクの名前を確かめる。小文字・数字・`-`・`_` の64文字以内。"""
    if not NAME.fullmatch(name):
        raise InvalidFileError(f"{kind}の名前 {name!r} は、小文字・数字・-・_ の64文字以内にしてください")
    return name


@dataclass(frozen=True)
class TaskPlace:
    """1つのラウンドの1つのタスクの記録の置き場（`runs/r<N>/<task>/`）。"""

    root: Path

    def mode_dir(self, mode: str) -> Path:
        """モードの記録。基準の実行はモードで共有するので `BASE` を渡す。"""
        return self.root / mode

    def rollout_dir(self, mode: str, label: str) -> Path:
        return self.mode_dir(mode) / ROLLOUTS_DIR / label

    def harness_dir(self, mode: str, label: str) -> Path:
        return self.mode_dir(mode) / HARNESSES_DIR / label

    def session_dir(self, mode: str, label: str, attempt: int) -> Path:
        return self.mode_dir(mode) / SESSIONS_DIR / build_session_name(label, attempt)

    def decision_path(self, mode: str, label: str) -> Path:
        """段の notes（落ちた段はエラー）。後の段の証拠と show が読む。"""
        return self.mode_dir(mode) / DECISIONS_DIR / f"{label}{MD_SUFFIX}"

    def library_view_dir(self, mode: str) -> Path:
        """このタスクより前のタスクの記録だけを集めたライブラリの写し。"""
        return self.mode_dir(mode) / LIBRARY_DIR

    def selection_dir(self, mode: str) -> Path:
        return self.mode_dir(mode) / SELECTION_DIR

    def reflection_dir(self, mode: str) -> Path:
        return self.mode_dir(mode) / REFLECTION_DIR

    def summary_path(self, mode: str) -> Path:
        return self.mode_dir(mode) / SUMMARY_FILE

    @property
    def judged_path(self) -> Path:
        return self.root / JUDGED_FILE


@dataclass(frozen=True)
class Layout:
    """利用者のリポジトリの中の、1つの対象（`.h2/targets/<target>/`）の置き場。"""

    repo: Path
    target: str

    @property
    def h2_dir(self) -> Path:
        return self.repo / H2_DIR

    @property
    def templates_dir(self) -> Path:
        return self.h2_dir / TEMPLATES_DIR / PROMPTS_DIR

    @property
    def target_dir(self) -> Path:
        return self.h2_dir / TARGETS_DIR / self.target

    @property
    def profile_path(self) -> Path:
        return self.target_dir / PROFILE_FILE

    @property
    def tasks_dir(self) -> Path:
        return self.target_dir / TASKS_DIR

    @property
    def plan_path(self) -> Path:
        return self.target_dir / PLAN_FILE

    @property
    def approval_path(self) -> Path:
        return self.target_dir / APPROVAL_FILE

    @property
    def adopted_path(self) -> Path:
        return self.target_dir / ADOPTED_FILE

    def skill_dir(self, skill: str) -> Path:
        return self.repo / skill

    def task_dir(self, task_id: str) -> Path:
        return self.tasks_dir / task_id

    def task_file(self, task_id: str) -> Path:
        return self.task_dir(task_id) / TASK_FILE

    def task_workspace(self, task_id: str) -> Path:
        return self.task_dir(task_id) / TASK_WORKSPACE_DIR

    def checks_path(self, task_id: str) -> Path:
        """事後の検査。`judging` と `planning` だけが使う（STATE-04）。"""
        return self.task_dir(task_id) / CHECKS_FILE

    def round_dir(self, number: int) -> Path:
        return self.target_dir / RUNS_DIR / f"r{number}"

    def base_skill_dir(self, number: int) -> Path:
        return self.round_dir(number) / BASE_SKILL_DIR

    def library_dir(self, number: int, mode: str) -> Path:
        return self.round_dir(number) / LIBRARY_DIR / mode

    def task_place(self, number: int, task_id: str) -> TaskPlace:
        return TaskPlace(self.round_dir(number) / task_id)
