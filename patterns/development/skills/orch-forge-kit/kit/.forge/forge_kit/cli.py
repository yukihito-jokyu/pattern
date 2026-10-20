"""補助 CLI の引数を読み、各段のモジュールを呼んで結果を出力する。画面への出力はこのモジュールだけで行う。"""

from __future__ import annotations

import argparse
import datetime
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Callable

from forge_kit import (
    analyze,
    building,
    collect,
    compare,
    decide,
    designing,
    execute,
    goals,
    layout,
    prepare,
    proc,
    report,
    score,
    status,
)
from forge_kit.errors import KitError

DEFAULT_PARALLEL = 3
# 段を進めるコマンドの後には、次にすることを status で確かめるよう案内する
ADVANCING = {
    "charter-new",
    "charter-check",
    "charter-approve",
    "design-new",
    "design-check",
    "design-approve",
    "build",
    "bundle-check",
    "install",
    "prepare",
    "execute",
    "collect",
    "score",
    "analyze",
    "propose",
    "compare",
    "decide",
    "report",
}


def _target(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--target", required=True, help="作業領域の名前（kebab-case）")
    return parser


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forge.py", description="開発用のオーケストレーションスキルをサブエージェントで作り、評価して改善する"
    )
    parser.add_argument("--root", help="対象のリポジトリのルート（既定: .forge/ を置いたディレクトリ）")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("targets", help="作業領域とリポジトリのスキルを一覧にする")
    sub.add_parser("metric-catalog", help="指標のカタログを出す")
    _target(sub.add_parser("charter-new", help="charter のひな形を書く")).add_argument(
        "--skill-name", required=True, help="作る・直すスキルの名前（kebab-case）"
    )
    for name, help_text in (
        ("charter-check", "charter を検査し、人が読む charter.md を書く"),
        ("charter-approve", "人の承認を charter に記録する"),
        ("status", "今の段階と次にすることを出す"),
        ("design-check", "設計役の design.json を検査し、人が読む design.md を書く"),
        ("design-approve", "人の承認を設計に記録する"),
        ("bundle-check", "構築役の下書きをバンドルの決まりで検査する"),
        ("install", "検査済みの下書きを対象のリポジトリの .claude/ へ入れる"),
        ("report", "全体の報告を書く"),
    ):
        _target(sub.add_parser(name, help=help_text))
    for name, help_text in (
        ("design-new", "設計役のプロンプトを書く"),
        ("build", "設計から下書きのひな形と構築役のプロンプトを書く"),
    ):
        _target(sub.add_parser(name, help=help_text)).add_argument(
            "--feedback", default="", help="人が直してほしいと言ったこと（そのまま渡す）"
        )
    for name, help_text in (
        ("prepare", "評価を準備する（コピーと実行役のプロンプト）"),
        ("execute", "実行役（claude -p）を起動する"),
        ("collect", "実行役の後の事実を集め、採点役のプロンプトを書く"),
        ("score", "指標を計算する"),
    ):
        command = _target(sub.add_parser(name, help=help_text))
        command.add_argument("--variant", required=True, choices=list(layout.VARIANTS))
        command.add_argument("--round", type=int, default=1, dest="round_no")
        if name == "collect":
            command.add_argument("--parallel", type=int, default=DEFAULT_PARALLEL, help="検査コマンドを並行に回す数")
    for name, help_text in (
        ("analyze", "分析役のプロンプトと編集用のバンドルの写しを用意する"),
        ("propose", "分析役の提案を検査し、proposal.md を書く"),
        ("compare", "今のバンドルと候補の採点を比べる"),
    ):
        _target(sub.add_parser(name, help=help_text)).add_argument("--round", type=int, required=True, dest="round_no")
    chosen = _target(sub.add_parser("decide", help="人が決めた採否を記録する（採用ならバンドルを置き換える）"))
    chosen.add_argument("--round", type=int, required=True, dest="round_no")
    verdict = chosen.add_mutually_exclusive_group(required=True)
    verdict.add_argument("--adopt", action="store_true")
    verdict.add_argument("--reject", action="store_true")
    return parser


def _handlers(root: Path) -> dict[str, Callable[[argparse.Namespace], str]]:
    today = datetime.date.today().isoformat()

    def where(args: argparse.Namespace) -> layout.Layout:
        return layout.make_layout(root, args.target, proc.copies_root(root))

    def slot(args: argparse.Namespace) -> layout.Slot:
        return layout.make_slot(args.variant, args.round_no)

    return {
        "targets": lambda _args: goals.targets(root),
        "metric-catalog": lambda _args: goals.metric_catalog(),
        "charter-new": lambda args: goals.charter_new(where(args), args.skill_name),
        "charter-check": lambda args: goals.charter_check(where(args)),
        "charter-approve": lambda args: goals.charter_approve(where(args), today),
        "status": lambda args: status.status(where(args)),
        "design-new": lambda args: designing.design_new(where(args), args.feedback),
        "design-check": lambda args: designing.design_check(where(args)),
        "design-approve": lambda args: designing.design_approve(where(args), today),
        "build": lambda args: building.build(where(args), args.feedback),
        "bundle-check": lambda args: building.bundle_check(where(args)),
        "install": lambda args: building.install(where(args), today),
        "prepare": lambda args: prepare.prepare(where(args), slot(args)),
        "execute": lambda args: execute.execute(where(args), slot(args), proc.launch),
        "collect": lambda args: collect.collect(where(args), slot(args), args.parallel),
        "score": lambda args: score.score(where(args), slot(args)),
        "analyze": lambda args: analyze.analyze(where(args), args.round_no),
        "propose": lambda args: analyze.propose(where(args), args.round_no),
        "compare": lambda args: compare.compare(where(args), args.round_no),
        "decide": lambda args: decide.decide(where(args), args.round_no, adopted=args.adopt, today=today),
        "report": lambda args: report.report(where(args)),
    }


def main(argv: Sequence[str], default_root: Path) -> int:
    args = make_parser().parse_args(argv)
    root = Path(args.root).resolve() if args.root else default_root
    try:
        text = _handlers(root)[args.command](args)
    except KitError as exc:
        print(f"エラー: {exc.message}", file=sys.stderr)
        return 1
    print(text)
    if args.command in ADVANCING:
        print(f"次: {status.CLI} status --target {args.target}")
    return 0
