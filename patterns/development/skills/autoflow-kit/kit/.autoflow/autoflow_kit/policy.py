"""関所（人と機械）・リスクの段・レビューの深さの表と、それを当てはめる関数を置く。

関所の条件と表の正本はここだけである（GATE-01）。人が読む版は make docs で gates.md に生成する。
"""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Callable

from autoflow_kit import contracts, profile, shape

H0 = "H0"
H1 = "H1"
H2 = "H2"
H3 = "H3"
LOW = "low"
MEDIUM = "medium"
HIGH = "high"
APPROVE = "approve"
CHANGES = "changes"
PROCEED = "proceed"
REPLAN = "replan"
CONTINUE = "continue"
ABORT = "abort"
IMPORTANT = "important"
NIT = "nit"
PRE_EXISTING = "pre_existing"


@dataclass(frozen=True)
class Tier:
    name: str
    depth: str
    human: str


@dataclass(frozen=True)
class Lens:
    name: str
    label: str


@dataclass(frozen=True)
class Depth:
    name: str
    lenses: tuple[str, ...]
    verifiers: int
    threshold: int


@dataclass(frozen=True)
class Kind:
    name: str
    label: str
    repro: bool
    checks: str


@dataclass(frozen=True)
class Progress:
    """実行の区切り（計画、H2 と H3 の決定）からの進み具合。trail.progress が記録から作る。"""

    failed_checks: int
    open_rounds: int
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class PlanRule:
    id: str
    text: str
    test: Callable[[contracts.Plan, profile.Profile], bool]


@dataclass(frozen=True)
class ProgressRule:
    id: str
    text: str
    test: Callable[[Progress, profile.Limits], bool]


@dataclass(frozen=True)
class Option:
    name: str
    label: str
    then: str


@dataclass(frozen=True)
class Gate:
    id: str
    label: str
    when: str
    show: str
    options: tuple[Option, ...]


@dataclass(frozen=True)
class ReviewRules:
    categories: tuple[str, ...]
    tags: tuple[str, ...]
    blocking: tuple[str, ...]
    diff_only_from_round: int


@dataclass(frozen=True)
class RuleTier:
    """差分だけから規則で決めたリスクの段。human_files は常に人が読むパスに当たったファイル。"""

    tier: str
    reasons: tuple[str, ...]
    human_files: tuple[str, ...]


@dataclass(frozen=True)
class Flow:
    """計画の種類と範囲から組んだ、1件の依頼の手順。"""

    kind: str
    repro: bool
    forecast_tier: str
    h1_reasons: tuple[str, ...]
    steps: tuple[str, ...]


# リスクの段。低い順に並べる。段はレビューの深さと、H3 で人がすることの重さを決める
TIERS = (
    Tier(LOW, "quick", "報告書の要約・証拠・レビューの結果・検査が見ていないことを読み、納得できれば承認する"),
    Tier(MEDIUM, "standard", "low に加えて、差分の全体を読む"),
    Tier(HIGH, "deep", "medium に加えて、注意するファイルを1行ずつ読み、2人目のレビューを頼むかを決める"),
)
# レビューの観点。探索役は観点ごとに1人ずつ起動する。観点を足したら finder.md の観点の節も直す（PROC-02）
LENSES = (
    Lens("correctness", "正しさ（論理、境界の値、エラーの扱い）"),
    Lens("security", "安全（入力の検証、認可、秘密情報）"),
    Lens("intent", "依頼との一致（受け入れ条件、計画の範囲、リポジトリの決まり）"),
    Lens("impact", "影響の範囲（呼び出し元、互換性、データ）"),
)
# レビューの深さ。threshold は、指摘を残すのに要る「本物」の票の数
DEPTHS = (
    Depth("quick", ("correctness", "intent"), 2, 2),
    Depth("standard", ("correctness", "security", "intent"), 3, 2),
    Depth("deep", ("correctness", "security", "intent", "impact"), 3, 2),
)
# 依頼の種類。repro が真なら、実装の前に再現のテストを書き、落ちることを verify で確かめる
KINDS = (
    Kind("feature", "機能の追加", False, "新しい振る舞いを、受け入れ条件ごとにコマンドかテストで確かめる"),
    Kind("fix", "不具合の修正", True, "直す前に再現のテストが落ち、直した後に通ることを確かめる"),
    Kind("refactor", "振る舞いを変えない整理", False, "既存のテストが変更の前後で通ることを確かめる"),
    Kind("docs", "文書だけの変更", False, "文書の中のコマンドとパスが実在することを確かめる"),
    Kind("chore", "設定・依存・道具の更新", False, "検査コマンドが全部通り、戻し方が書けることを確かめる"),
)
REVIEW = ReviewRules(
    categories=("bug", "security", "criteria", "fit"),
    tags=(IMPORTANT, PRE_EXISTING, NIT),
    blocking=(IMPORTANT,),
    diff_only_from_round=2,
)


def _is_match(path: str, pattern: str) -> bool:
    """glob の一致。`*` は `/` もまたぐ。`**/` で始まる glob は、ルートの直下のファイルにも一致する。"""
    if fnmatch.fnmatchcase(path, pattern):
        return True
    return pattern.startswith("**/") and fnmatch.fnmatchcase(path, pattern[3:])


def has_match(path: str, patterns: Iterable[str]) -> bool:
    return any(_is_match(path, pattern) for pattern in patterns)


def _has_open_question(plan: contracts.Plan, _profile: profile.Profile) -> bool:
    return any(question.impact == contracts.HIGH_IMPACT for question in plan.open_questions)


def _has_new_dependency(plan: contracts.Plan, _profile: profile.Profile) -> bool:
    return bool(plan.dependencies_to_add)


def _has_wide_scope(plan: contracts.Plan, settings: profile.Profile) -> bool:
    return len(plan.scope) > settings.limits.max_scope_files


def _has_human_paths(plan: contracts.Plan, settings: profile.Profile) -> bool:
    return any(has_match(path, settings.risk.always_human) for path in plan.scope)


def _is_blocked(progress: Progress, _limits: profile.Limits) -> bool:
    return bool(progress.blockers)


def _has_too_many_failures(progress: Progress, limits: profile.Limits) -> bool:
    return progress.failed_checks >= limits.fix_attempts


def _has_too_many_open_rounds(progress: Progress, limits: profile.Limits) -> bool:
    return progress.open_rounds >= limits.review_rounds


# H1（方向の確認）を起こす条件。規則を足したら tests/test_policy.py に test_<id> を足す
H1_RULES = (
    PlanRule("h1_open_question", "方向を変えうる未決の値（impact が high）が計画にある", _has_open_question),
    PlanRule("h1_new_dependency", "依存を足す計画である", _has_new_dependency),
    PlanRule("h1_wide_scope", "計画の範囲が limits.max_scope_files を超える", _has_wide_scope),
    PlanRule("h1_human_paths", "計画の範囲が risk.always_human のパスに当たる", _has_human_paths),
)
# H2（行き詰まり）を起こす条件。記事の「3ラウンドで止まって方針を見直す」に当たる
H2_RULES = (
    ProgressRule("h2_blocked", "実装役が、止まった理由（blockers）を報告した", _is_blocked),
    ProgressRule("h2_too_many_failures", "検査の失敗が limits.fix_attempts 回続いた", _has_too_many_failures),
    ProgressRule(
        "h2_too_many_open_rounds", "Important が残るレビューが limits.review_rounds 回続いた", _has_too_many_open_rounds
    ),
)
GATES = (
    Gate(
        H0,
        "準備の承認",
        "リポジトリごとに1回（autoflow-setup）",
        "setup-check が出すプロファイルの人が読む版",
        (
            Option(APPROVE, "承認する", "setup-approve に回答の原文を渡す"),
            Option(CHANGES, "直してほしいことを伝える", "profile.json を直し、setup-check からやり直す"),
        ),
    ),
    Gate(
        H1,
        "方向の確認",
        "計画の後、実装の前。H1_RULES のどれかに当たるときだけ",
        "計画（plan.md）",
        (
            Option(PROCEED, "この計画で進める", "実装に進む"),
            Option(REPLAN, "計画を直す", "回答を計画役に渡し、計画からやり直す"),
            Option(ABORT, "やめる", "実行を止める"),
        ),
    ),
    Gate(
        H2,
        "行き詰まり",
        "実装の途中。H2_RULES のどれかに当たるときだけ",
        "関所の理由（gates/h2-<n>.md）",
        (
            Option(CONTINUE, "回答を添えて続ける", "回答を実装役に渡し、実装に戻る"),
            Option(REPLAN, "計画からやり直す", "回答を計画役に渡し、計画からやり直す"),
            Option(ABORT, "やめる", "実行を止める"),
        ),
    ),
    Gate(
        H3,
        "最終承認",
        "毎回。検証とレビューを通った後",
        "報告書（handoff-<n>.md）",
        (
            Option(APPROVE, "承認する", "承認した tree と今の tree が同じなら、作業ブランチにコミットする"),
            Option(CHANGES, "直してほしいことを伝える", "回答を実装役に渡し、実装に戻る"),
            Option(ABORT, "やめる", "実行を止める。作業ブランチと変更は残る"),
        ),
    ),
)


def tier_order(name: str) -> int:
    return [tier.name for tier in TIERS].index(name)


def tier_of(name: str) -> Tier:
    return next(tier for tier in TIERS if tier.name == name)


def depth_of(tier_name: str) -> Depth:
    depth = tier_of(tier_name).depth
    return next(item for item in DEPTHS if item.name == depth)


def kind_of(name: str) -> Kind:
    return next(kind for kind in KINDS if kind.name == name)


def gate_of(gate_id: str) -> Gate:
    return next(gate for gate in GATES if gate.id == gate_id)


def rule_text(rule_id: str) -> str:
    rules: tuple[PlanRule | ProgressRule, ...] = (*H1_RULES, *H2_RULES)
    return next((rule.text for rule in rules if rule.id == rule_id), rule_id)


def merge_tier(rule_tier: str, ai_tier: str) -> str:
    """規則の段と AI の段の大きい方。AI の判定は段を上げる方向にだけ効く（GATE-06）。"""
    return max(rule_tier, ai_tier, key=tier_order)


def tier_of_changes(files: tuple[str, ...], lines: int, settings: profile.Profile) -> RuleTier:
    """変更（パスと行数）だけからリスクの段を決める。計画や報告の自己申告は使わない。"""
    risk, limits = settings.risk, settings.limits
    reasons = []
    tier = MEDIUM
    if files and all(has_match(path, (*risk.low, *settings.paths.tests)) for path in files):
        tier = LOW
        reasons.append("変更が risk.low とテストのパスだけ")
    human_files = tuple(path for path in files if has_match(path, risk.always_human))
    if human_files:
        tier = merge_tier(tier, MEDIUM)
        reasons.append(f"risk.always_human のパスを変える: {', '.join(human_files)}")
    if lines > limits.large_diff_lines:
        tier = merge_tier(tier, MEDIUM)
        reasons.append(f"差分が {lines} 行で limits.large_diff_lines（{limits.large_diff_lines}）を超える")
    high_files = [path for path in files if has_match(path, risk.high)]
    if high_files:
        tier = HIGH
        reasons.append(f"risk.high のパスを変える: {', '.join(high_files)}")
    if lines > limits.huge_diff_lines:
        tier = HIGH
        reasons.append(f"差分が {lines} 行で limits.huge_diff_lines（{limits.huge_diff_lines}）を超える")
    if not reasons:
        reasons.append("規則に当たらない通常の変更")
    return RuleTier(tier, tuple(reasons), human_files)


def h1_reasons(plan: contracts.Plan, settings: profile.Profile) -> tuple[str, ...]:
    return tuple(rule.id for rule in H1_RULES if rule.test(plan, settings))


def h2_reasons(progress: Progress, limits: profile.Limits) -> tuple[str, ...]:
    return tuple(rule.id for rule in H2_RULES if rule.test(progress, limits))


def check_plan(plan: contracts.Plan) -> list[str]:
    """種類ごとの決まりで計画を確かめる。parse_plan の形の検証が通った後に呼ぶ。"""
    problems = []
    if kind_of(plan.kind).repro and not plan.repro.strip():
        problems.append(f"repro が空です。種類 {plan.kind} では、直す前に落ちる再現のコマンドを書く")
    if kind_of(plan.kind).repro and not plan.root_cause.strip():
        problems.append(f"root_cause が空です。種類 {plan.kind} では、原因の見立てを書く")
    if not kind_of(plan.kind).repro and plan.repro:
        problems.append(f"repro は種類 {plan.kind} では書かない（再現の手順は不具合の修正だけ）")
    return problems


def compose(plan: contracts.Plan, settings: profile.Profile) -> Flow:
    """計画の種類・範囲とプロファイルから、手順・予測の段・H1 の要否を組む。"""
    kind = kind_of(plan.kind)
    reasons = h1_reasons(plan, settings)
    forecast = tier_of_changes(plan.scope, 0, settings).tier
    steps = ["計画"]
    steps += [f"{H1} 方向の確認"] if reasons else []
    steps += ["再現のテスト", "再現の検証"] if kind.repro else []
    steps += ["実装", "検証", "リスクの判定", f"レビュー（{tier_of(forecast).depth} の予測）", "報告書"]
    steps += [f"{H3} 最終承認", "コミット"]
    return Flow(plan.kind, kind.repro, forecast, reasons, tuple(steps))


def parse_flow(value: object, problems: list[str]) -> Flow:
    data = shape.as_object(value, "", problems)
    shape.unknown_keys(data, ("kind", "repro", "forecast_tier", "h1_reasons", "steps"), "", problems)
    return Flow(
        kind=shape.choice(data, "kind", (kind.name for kind in KINDS), "", problems),
        repro=shape.boolean(data, "repro", "", problems),
        forecast_tier=shape.choice(data, "forecast_tier", (tier.name for tier in TIERS), "", problems),
        h1_reasons=shape.texts(data, "h1_reasons", "", problems),
        steps=shape.texts(data, "steps", "", problems),
    )
