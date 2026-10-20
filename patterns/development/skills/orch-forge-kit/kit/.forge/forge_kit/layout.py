"""作業領域（.forge/）と評価用のコピーの中のパスとファイル名を決める。"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path

from forge_kit.errors import KitError

KIT_DIR = ".forge"
KIT_PREFIX = "forge-"
TARGETS_DIR = "targets"
WORK_DIR = "work"
ROUNDS_DIR = "rounds"
FINAL_DIR = "final"
BUILD_DIR = "build"
CLAUDE_DIR = ".claude"
SKILLS_DIR = "skills"
AGENTS_DIR = "agents"
REFERENCES_DIR = "references"
SKILL_FILE = "SKILL.md"
AGENT_SUFFIX = ".md"
BUILD_SKILL = "forge-build"
DESIGN_SCHEMA_MD = "design-schema.md"
BUNDLE_RULES_MD = "bundle-rules.md"

CHARTER_FILE = "charter.json"
CHARTER_MD = "charter.md"
VISIBLE_CHARTER_MD = "visible-charter.md"
REPORT_MD = "report.md"
DESIGN_FILE = "design.json"
DESIGN_MD = "design.md"
DESIGN_APPROVAL_FILE = "design-approval.json"
DESIGNER_PROMPT_FILE = "designer-prompt.md"
BUILDER_PROMPT_FILE = "builder-prompt.md"
DRAFT_DIR = "draft"
BUNDLE_CHECK_FILE = "bundle-check.json"
BUNDLE_CHECK_MD = "bundle-check.md"
INSTALL_FILE = "install.json"
PLAN_FILE = "plan.json"
SCORES_FILE = "scores.json"
SCORES_MD = "scores.md"
FINGERPRINT_FILE = "fingerprint.json"
SLOT_BUNDLE_DIR = "bundle"
ANALYST_PROMPT_FILE = "analyst-prompt.md"
PROPOSAL_FILE = "proposal.json"
PROPOSAL_MD = "proposal.md"
COMPARE_FILE = "compare.json"
COMPARE_MD = "compare.md"
DECISION_FILE = "decision.json"
PROPOSED_DIR = "proposed"
PREVIOUS_DIR = "previous"

PROMPT_FILE = "prompt.md"
SYSTEM_FILE = "system.md"
STREAM_FILE = "stream.jsonl"
STDERR_FILE = "stderr.txt"
EXEC_FILE = "exec.json"
FACTS_FILE = "facts.json"
TRACE_MD = "trace.md"
RESULT_MD = "result.md"
PATCH_FILE = "changes.patch"
GRADER_PROMPT_FILE = "grader-prompt.md"
GRADE_FILE = "grade.json"

VARIANTS = ("baseline", "candidate", "final")
TARGET_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Slot:
    """1回の評価の置き場。baseline は1回目のラウンドだけ、final はラウンドを持たない（0）。"""

    variant: str
    round_no: int

    @property
    def name(self) -> str:
        return FINAL_DIR if self.variant == "final" else f"round-{self.round_no}-{self.variant}"


def make_slot(variant: str, round_no: int) -> Slot:
    if variant not in VARIANTS:
        raise KitError(f"--variant は {', '.join(VARIANTS)} のどれかにしてください（今: {variant}）")
    if variant == "final":
        return Slot("final", 0)
    if variant == "baseline" and round_no != 1:
        raise KitError("baseline の評価は 1回目のラウンドだけで行います。--round 1 を指定してください")
    if round_no < 1:
        raise KitError(f"--round は 1 以上にしてください（今: {round_no}）")
    return Slot(variant, round_no)


@dataclass(frozen=True)
class Layout:
    """1つの対象の作業領域。root はリポジトリのルート、copies_root は評価用のコピーを置く場所（ADR 0003）。"""

    root: Path
    target: str
    copies_root: Path

    @property
    def target_dir(self) -> Path:
        return self.root / KIT_DIR / TARGETS_DIR / self.target

    @property
    def charter_path(self) -> Path:
        return self.target_dir / CHARTER_FILE

    @property
    def charter_md_path(self) -> Path:
        return self.target_dir / CHARTER_MD

    @property
    def visible_charter_path(self) -> Path:
        """設計役・構築役・分析役に見せる charter。ホールドアウトの課題を除く。"""
        return self.target_dir / VISIBLE_CHARTER_MD

    @property
    def report_path(self) -> Path:
        return self.target_dir / REPORT_MD

    @property
    def claude_dir(self) -> Path:
        """対象のリポジトリの .claude/。バンドルの置き場（skills/ と agents/）を持つ。"""
        return self.root / CLAUDE_DIR

    @property
    def design_schema_path(self) -> Path:
        return self.claude_dir / SKILLS_DIR / BUILD_SKILL / REFERENCES_DIR / DESIGN_SCHEMA_MD

    @property
    def bundle_rules_path(self) -> Path:
        return self.claude_dir / SKILLS_DIR / BUILD_SKILL / REFERENCES_DIR / BUNDLE_RULES_MD

    @property
    def build_dir(self) -> Path:
        return self.target_dir / BUILD_DIR

    @property
    def design_path(self) -> Path:
        return self.build_dir / DESIGN_FILE

    @property
    def design_md_path(self) -> Path:
        return self.build_dir / DESIGN_MD

    @property
    def design_approval_path(self) -> Path:
        return self.build_dir / DESIGN_APPROVAL_FILE

    @property
    def designer_prompt_path(self) -> Path:
        return self.build_dir / DESIGNER_PROMPT_FILE

    @property
    def builder_prompt_path(self) -> Path:
        return self.build_dir / BUILDER_PROMPT_FILE

    @property
    def draft_dir(self) -> Path:
        """構築役が書く下書きのバンドル。skills/<スキル名>/ と agents/ を持つ。"""
        return self.build_dir / DRAFT_DIR

    @property
    def bundle_check_path(self) -> Path:
        return self.build_dir / BUNDLE_CHECK_FILE

    @property
    def bundle_check_md_path(self) -> Path:
        return self.build_dir / BUNDLE_CHECK_MD

    @property
    def install_path(self) -> Path:
        return self.build_dir / INSTALL_FILE

    @property
    def work_root(self) -> Path:
        return self.root / KIT_DIR / WORK_DIR / self.target

    def skill_md_path(self, skill_name: str) -> Path:
        return self.claude_dir / SKILLS_DIR / skill_name / SKILL_FILE

    def round_dir(self, round_no: int) -> Path:
        return self.target_dir / ROUNDS_DIR / f"round-{round_no}"

    def slot_dir(self, slot: Slot) -> Path:
        if slot.variant == "final":
            return self.target_dir / FINAL_DIR
        return self.round_dir(slot.round_no) / slot.variant

    def plan_path(self, slot: Slot) -> Path:
        return self.slot_dir(slot) / PLAN_FILE

    def scores_path(self, slot: Slot) -> Path:
        return self.slot_dir(slot) / SCORES_FILE

    def scores_md_path(self, slot: Slot) -> Path:
        return self.slot_dir(slot) / SCORES_MD

    def work_dir(self, slot: Slot) -> Path:
        return self.work_root / slot.name

    def fingerprint_path(self, slot: Slot) -> Path:
        return self.work_dir(slot) / FINGERPRINT_FILE

    def slot_bundle_dir(self, slot: Slot) -> Path:
        """その評価で使うバンドルの写し。評価の後に対象スキルが変わっても、採点は写しを読む。"""
        return self.work_dir(slot) / SLOT_BUNDLE_DIR

    def slot_skill_md_path(self, slot: Slot, skill_name: str) -> Path:
        return self.slot_bundle_dir(slot) / SKILLS_DIR / skill_name / SKILL_FILE

    def slot_copies_dir(self, slot: Slot) -> Path:
        return self.copies_root / self.target / slot.name

    def copy_dir(self, slot: Slot, run_id: str) -> Path:
        return self.slot_copies_dir(slot) / run_id

    def out_dir(self, slot: Slot, run_id: str) -> Path:
        return self.work_dir(slot) / run_id

    def prompt_path(self, slot: Slot, run_id: str) -> Path:
        return self.out_dir(slot, run_id) / PROMPT_FILE

    def system_path(self, slot: Slot, run_id: str) -> Path:
        return self.out_dir(slot, run_id) / SYSTEM_FILE

    def stream_path(self, slot: Slot, run_id: str) -> Path:
        return self.out_dir(slot, run_id) / STREAM_FILE

    def stderr_path(self, slot: Slot, run_id: str) -> Path:
        return self.out_dir(slot, run_id) / STDERR_FILE

    def exec_path(self, slot: Slot, run_id: str) -> Path:
        return self.out_dir(slot, run_id) / EXEC_FILE

    def facts_path(self, slot: Slot, run_id: str) -> Path:
        return self.out_dir(slot, run_id) / FACTS_FILE

    def trace_md_path(self, slot: Slot, run_id: str) -> Path:
        return self.out_dir(slot, run_id) / TRACE_MD

    def result_md_path(self, slot: Slot, run_id: str) -> Path:
        return self.out_dir(slot, run_id) / RESULT_MD

    def patch_path(self, slot: Slot, run_id: str) -> Path:
        return self.out_dir(slot, run_id) / PATCH_FILE

    def grader_prompt_path(self, slot: Slot, run_id: str) -> Path:
        return self.out_dir(slot, run_id) / GRADER_PROMPT_FILE

    def grade_path(self, slot: Slot, run_id: str) -> Path:
        return self.out_dir(slot, run_id) / GRADE_FILE

    def analyst_prompt_path(self, round_no: int) -> Path:
        return self.round_dir(round_no) / ANALYST_PROMPT_FILE

    def proposal_path(self, round_no: int) -> Path:
        return self.round_dir(round_no) / PROPOSAL_FILE

    def proposal_md_path(self, round_no: int) -> Path:
        return self.round_dir(round_no) / PROPOSAL_MD

    def proposed_dir(self, round_no: int) -> Path:
        """分析役が直す候補のバンドル。skills/<スキル名>/ と agents/ を持つ。"""
        return self.round_dir(round_no) / PROPOSED_DIR

    def previous_dir(self, round_no: int) -> Path:
        return self.round_dir(round_no) / PREVIOUS_DIR

    def compare_path(self, round_no: int) -> Path:
        return self.round_dir(round_no) / COMPARE_FILE

    def compare_md_path(self, round_no: int) -> Path:
        return self.round_dir(round_no) / COMPARE_MD

    def decision_path(self, round_no: int) -> Path:
        return self.round_dir(round_no) / DECISION_FILE


def make_layout(root: Path, target: str, copies_root: Path) -> Layout:
    if not TARGET_ID.match(target):
        raise KitError(f"--target は kebab-case（小文字・数字・ハイフン）にしてください（今: {target}）")
    return Layout(root.resolve(), target, copies_root)


def run_id(task_id: str, agent_no: int) -> str:
    return f"{task_id}-a{agent_no}"


def agent_file(agent_name: str) -> str:
    return agent_name + AGENT_SUFFIX


def is_matched(path: str, patterns: tuple[str, ...]) -> bool:
    """パスが glob のどれかに当たるか。* は / もまたぐ（`.github/*` は下の全ファイルに当たる）。"""
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)
