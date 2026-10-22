"""補助 CLI の引数を読み、各段のモジュールを呼んで結果を出力する。時刻・画面への出力・終了コードはここだけで扱う。"""

from __future__ import annotations

import argparse
import datetime
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Callable

from autoflow_kit import (
    building,
    deciding,
    handoff,
    intake,
    layout,
    learning,
    planning,
    reviewing,
    risking,
    setup,
    status,
    trail,
    verifying,
)
from autoflow_kit.errors import KitError
from autoflow_kit.layout import Layout

# 実行を進めるサブコマンドと、その関数。後に、次を status で確かめる案内を出す
RUN_STEPS: dict[str, Callable[[Layout, str, str], str]] = {
    "plan-new": planning.plan_new,
    "plan-check": planning.plan_check,
    "build-new": building.build_new,
    "build-check": building.build_check,
    "verify": verifying.verify,
    "risk-new": risking.risk_new,
    "risk-check": risking.risk_check,
    "review-new": reviewing.review_new,
    "review-collect": reviewing.review_collect,
    "review-tally": reviewing.review_tally,
    "handoff": handoff.handoff,
    "commit": handoff.commit,
}
HELP = {
    "plan-new": "計画役のプロンプトを書く",
    "plan-check": "計画を検証し、手順を組み、H1 の要否を決める",
    "build-new": "実装役のプロンプトを書く",
    "build-check": "実装役の報告を検証する",
    "verify": "検査コマンドを実行し、証拠を記録する",
    "risk-new": "規則の段を求め、リスク判定役のプロンプトを書く",
    "risk-check": "規則と判定役の大きい方でリスクの段を決める",
    "review-new": "観点ごとの探索役のプロンプトを書く",
    "review-collect": "指摘をまとめ、検証役のプロンプトを書く",
    "review-tally": "票を集計し、指摘を残すか決める",
    "handoff": "H3 で人が読む報告書を書く",
    "commit": "承認した tree のまま作業ブランチにコミットする",
}


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autoflow.py", description="オートフローの段の順序と関所を受け持つ補助 CLI")
    parser.add_argument("--root", help="対象のリポジトリのルート（既定: .autoflow/ を置いたディレクトリ）")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup-new", help="プロファイルの案を書く").add_argument("--force", action="store_true")
    sub.add_parser("setup-check", help="プロファイルを検証し、人が読む版を出す")
    approve = sub.add_parser("setup-approve", help="H0 の人の承認を記録する")
    approve.add_argument("--answer", required=True, help="人の回答の原文")
    approve.add_argument("--allow", action="store_true", help="検査コマンドを .claude/settings.local.json の許可に足す")
    start = sub.add_parser("start", help="依頼から実行を始める（作業ブランチを作る）")
    start.add_argument("--source", required=True, choices=list(layout.SOURCES))
    start.add_argument("--ref", default="", help="課題の番号")
    start.add_argument("--url", default="", help="課題の URL")
    start.add_argument("--title", required=True, help="依頼の題名")
    start.add_argument("--body-file", required=True, help="依頼の本文を書いたファイル")
    sub.add_parser("status", help="今の段と次にすることを出す").add_argument("--run", default="", help="実行の id")
    for name, help_text in HELP.items():
        sub.add_parser(name, help=help_text).add_argument("--run", required=True, help="実行の id")
    decide = sub.add_parser("decide", help="人の関所の決定を、回答の原文付きで記録する")
    decide.add_argument("--run", required=True)
    decide.add_argument("--gate", required=True)
    decide.add_argument("--choice", required=True)
    decide.add_argument("--answer", required=True, help="人の回答の原文")
    sub.add_parser("metrics", help="全実行の人の介入とガードレールを数える")
    sub.add_parser("learn", help="繰り返したバグの種類・退けた指摘・人の依頼・インシデントを並べる")
    incident = sub.add_parser("incident", help="コミットした実行に、後で見つかった問題を記録する")
    incident.add_argument("--run", required=True)
    incident.add_argument("--text", required=True)
    return parser


def _now() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _run(args: argparse.Namespace, where: Layout) -> tuple[str, str]:
    """(出力, 次を確かめる実行の id)。id が空なら、status の案内を出さない。"""
    command, now = args.command, _now()
    if command in RUN_STEPS:
        return RUN_STEPS[command](where, args.run, now), args.run
    if command == "decide":
        return deciding.decide(where, args.run, args.gate, args.choice, args.answer, now), args.run
    if command == "status":
        return status.status(where, args.run), ""
    if command == "start":
        origin = trail.Origin(args.source, args.ref, args.url, args.title)
        return intake.start(where, origin, Path(args.body_file).resolve(), now), ""
    return _other(args, where, now), ""


def _other(args: argparse.Namespace, where: Layout, now: str) -> str:
    handlers: dict[str, Callable[[], str]] = {
        "setup-new": lambda: setup.setup_new(where, force=args.force),
        "setup-check": lambda: setup.setup_check(where),
        "setup-approve": lambda: setup.setup_approve(where, args.answer, now, allow=args.allow),
        "metrics": lambda: learning.metrics(where),
        "learn": lambda: learning.learn(where),
        "incident": lambda: learning.incident(where, args.run, args.text, now),
    }
    return handlers[args.command]()


def main(argv: Sequence[str], default_root: Path) -> int:
    args = make_parser().parse_args(argv)
    root = Path(args.root).resolve() if args.root else default_root.resolve()
    try:
        text, run_id = _run(args, Layout(root))
    except KitError as exc:
        print(f"エラー: {exc.message}", file=sys.stderr)
        return 1
    print(text)
    if run_id:
        print(f"次: {layout.CLI} status --run {run_id}")
    return 0
