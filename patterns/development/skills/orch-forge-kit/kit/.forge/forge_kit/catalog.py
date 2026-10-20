"""charter で選べる評価指標のカタログを持つ。人と指標を決める対話は、この一覧から始める。"""

from __future__ import annotations

import re
from dataclasses import dataclass

METHODS = ("machine", "grader")
DIRECTIONS = ("higher", "lower")
PRIORITIES = ("must", "should")
CUSTOM_ID = re.compile(r"^custom_[1-9][0-9]*$")
RATE_MAX = 1.0


@dataclass(frozen=True)
class Metric:
    """1つの指標の定義。max_value が None の指標は量（費用・秒・回数）で、上限が無い。"""

    id: str
    name: str
    method: str
    direction: str
    default_threshold: float
    max_value: float | None
    recommended: bool
    tells: str
    computes: str
    requires: str


METRICS: tuple[Metric, ...] = (
    Metric(
        id="check_pass",
        name="検査の通過率",
        method="machine",
        direction="higher",
        default_threshold=1.0,
        max_value=RATE_MAX,
        recommended=True,
        tells="スキルに従って作ったものが、リポジトリの検査（テスト・lint・型など）を通るか",
        computes="実行ごとに、コピーで environment.check_command を回し、終了コード0だった実行の割合",
        requires="environment.check_command",
    ),
    Metric(
        id="acceptance",
        name="受け入れ条件の充足率",
        method="grader",
        direction="higher",
        default_threshold=1.0,
        max_value=RATE_MAX,
        recommended=True,
        tells="依頼したことを、抜けなく満たしているか",
        computes="採点役が acceptance の各条件を満たしたかを判定し、満たした割合を実行ごとに出して平均する",
        requires="各課題の acceptance（1件以上）",
    ),
    Metric(
        id="protected_untouched",
        name="保護パスの非変更率",
        method="machine",
        direction="higher",
        default_threshold=1.0,
        max_value=RATE_MAX,
        recommended=True,
        tells="検査の設定やルールの正本など、変えてはいけないファイルを変えずに済ませるか",
        computes="environment.protected_paths の glob に当たるファイルを1つも変えなかった実行の割合",
        requires="environment.protected_paths（1件以上）",
    ),
    Metric(
        id="completion",
        name="完了率",
        method="machine",
        direction="higher",
        default_threshold=1.0,
        max_value=RATE_MAX,
        recommended=True,
        tells="費用や時間の上限に達したり、エラーで止まったりせずに、最後まで終えるか",
        computes="実行の記録の result が success で、打ち切られず、終了コード0だった実行の割合",
        requires="",
    ),
    Metric(
        id="delegation",
        name="サブエージェントへの委任率",
        method="machine",
        direction="higher",
        default_threshold=0.8,
        max_value=RATE_MAX,
        recommended=True,
        tells="ファイルの編集を、メインのセッションではなく役ごとのサブエージェントに任せているか",
        computes="実行ごとに、編集（Edit・Write など）のうちサブエージェントが行った割合を出して平均する。"
        "編集の無い実行は数えない",
        requires="",
    ),
    Metric(
        id="flow_conformance",
        name="手順の遵守率",
        method="grader",
        direction="higher",
        default_threshold=1.0,
        max_value=RATE_MAX,
        recommended=True,
        tells="スキルの `## 手順` の各項目を、飛ばさず順に行ったか",
        computes="採点役が、実行の記録から手順の各項目を行ったかを判定し、行った割合を実行ごとに出して平均する",
        requires="",
    ),
    Metric(
        id="report_format",
        name="報告の形式の遵守率",
        method="grader",
        direction="higher",
        default_threshold=1.0,
        max_value=RATE_MAX,
        recommended=True,
        tells="作業の最後の報告が、スキルの `## 報告` の定めた項目と順序になっているか",
        computes="採点役が、最後の返答が `## 報告` の定めに従っているかを判定し、従った実行の割合",
        requires="",
    ),
    Metric(
        id="files_agreement",
        name="変更ファイルの一致度",
        method="machine",
        direction="higher",
        default_threshold=0.8,
        max_value=RATE_MAX,
        recommended=False,
        tells="同じ依頼に対して、誰が実行しても同じファイルを作り・変えるか",
        computes="課題ごとに、実行どうしの変更ファイルの集合の Jaccard 係数を総当たりで平均する",
        requires="budget.agents が 2 以上",
    ),
    Metric(
        id="cost_usd",
        name="1回の実行の費用（推定、ドル）",
        method="machine",
        direction="lower",
        default_threshold=2.0,
        max_value=None,
        recommended=False,
        tells="1つの依頼をこなすのに、サブエージェントの分も含めてどれだけの費用がかかるか",
        computes="実行の記録の result の total_cost_usd（推定）を、実行ごとに平均する",
        requires="",
    ),
    Metric(
        id="duration_sec",
        name="1回の実行の時間（秒）",
        method="machine",
        direction="lower",
        default_threshold=900.0,
        max_value=None,
        recommended=False,
        tells="1つの依頼をこなすのに、どれだけの時間がかかるか",
        computes="実行の記録の result の duration_ms を秒にし、実行ごとに平均する",
        requires="",
    ),
    Metric(
        id="launches",
        name="サブエージェントの起動回数",
        method="machine",
        direction="lower",
        default_threshold=10.0,
        max_value=None,
        recommended=False,
        tells="1つの依頼で、サブエージェントを何回起動するか（多すぎると費用と時間が増える）",
        computes="メインのセッションが Agent ツールでサブエージェントを起動した回数を、実行ごとに平均する",
        requires="",
    ),
)

# 2人以上の実行を比べて初めて計算できる指標
AGREEMENT_METRICS = frozenset({"files_agreement"})


def find(metric_id: str) -> Metric | None:
    return next((metric for metric in METRICS if metric.id == metric_id), None)


def is_custom(metric_id: str) -> bool:
    return CUSTOM_ID.match(metric_id) is not None


def custom_metric(metric_id: str, criterion: str) -> Metric:
    """人が対話で足した指標。採点役が実行ごとに criterion を満たすかを判定し、満たした割合を出す。"""
    return Metric(
        id=metric_id,
        name=f"独自の条件（{metric_id}）",
        method="grader",
        direction="higher",
        default_threshold=1.0,
        max_value=RATE_MAX,
        recommended=False,
        tells=criterion,
        computes="採点役が、実行ごとに条件を満たしたかを判定し、満たした実行の割合",
        requires="",
    )
