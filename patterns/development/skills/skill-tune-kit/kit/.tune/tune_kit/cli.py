"""補助 CLI の入口。引数を読んで段の関数を呼び、結果を標準出力に、エラーを標準エラーに出す。"""

from __future__ import annotations

import argparse
import datetime
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from tune_kit import audit, decide, evaluate, layout, learn, planning, report, status
from tune_kit.errors import KitError

TEXT = "text"
NUMBER = "number"
SWITCH = "switch"


@dataclass(frozen=True)
class Option:
    flag: str
    help: str
    kind: str = TEXT
    required: bool = True


@dataclass(frozen=True)
class Command:
    """サブコマンド。run は (作業場所, 引数, 今日の日付) を受けて、標準出力に出す文を返す。"""

    help: str
    run: Callable[[layout.Layout, argparse.Namespace, str], str]
    options: tuple[Option, ...] = ()


ROUND = Option("--round", "ラウンドの番号（1から）", NUMBER)
SCOPE = (
    Option("--round", "ラウンドの番号（--final と、どちらか1つ）", NUMBER, required=False),
    Option("--final", "最後の監査（テスト用。報告のみ）", SWITCH, required=False),
)
EVAL = (
    Option("--version", "評価する版（v0、v1 …）"),
    Option("--splits", "分割をカンマ区切りで（例 train,val）"),
)


def _read_splits(args: argparse.Namespace) -> list[str]:
    return [name.strip() for name in str(args.splits).split(",") if name.strip()]


def _read_scope(args: argparse.Namespace) -> int | None:
    """--round と --final のどちらか1つ。最後の監査なら None。"""
    if (args.round is None) == (not args.final):
        raise KitError("--round <番号> か --final のどちらか1つを指定してください")
    return None if args.final else int(args.round)


def _read_chosen(args: argparse.Namespace) -> list[str]:
    """--apply の指摘の ID。--none なら空。"""
    if (args.apply is None) == (not args.none):
        raise KitError("--apply '<指摘の ID をカンマ区切り>' か --none のどちらか1つを指定してください")
    return [] if args.none else [item.strip() for item in str(args.apply).split(",") if item.strip()]


# サブコマンドの表。足したら tests/test_cli.py に test_command_<名前> を足す（TEST-03）
COMMANDS: dict[str, Command] = {
    "init": Command(
        "計画（plan.json）とケース（cases.json）のひな形を作る",
        lambda where, args, _today: planning.init(where, str(args.skill)),
        (Option("--skill", "対象スキルのディレクトリ（リポジトリのルートからの相対パス）"),),
    ),
    "check-plan": Command(
        "計画を検査し、分割と plan.md を書く", lambda where, _args, _today: planning.check_plan(where)
    ),
    "approve": Command(
        "人が承認した計画を記録し、対象スキルを v0 に写す", lambda where, _args, today: planning.approve(where, today)
    ),
    "status": Command(
        "今の段階と、次に実行すること・起動するサブエージェントを示す",
        lambda where, _args, _today: status.status(where),
    ),
    "eval-prepare": Command(
        "版の評価の作業場所と実行役のプロンプトを作る",
        lambda where, args, _today: evaluate.eval_prepare(where, str(args.version), _read_splits(args)),
        EVAL,
    ),
    "eval-collect": Command(
        "機械の検査を回し、採点役のプロンプトを作る",
        lambda where, args, _today: evaluate.eval_collect(where, str(args.version), _read_splits(args)),
        EVAL,
    ),
    "eval-score": Command(
        "機械の検査と採点を合わせて結果を記録する",
        lambda where, args, _today: evaluate.eval_score(where, str(args.version), _read_splits(args)),
        EVAL,
    ),
    "audit": Command(
        "不合格のケースの証拠と監査役のプロンプトを作る",
        lambda where, args, _today: audit.audit(where, _read_scope(args)),
        SCOPE,
    ),
    "audit-check": Command(
        "監査役の audit.json を検査し、audit.md を書く",
        lambda where, args, _today: audit.audit_check(where, _read_scope(args)),
        SCOPE,
    ),
    "data-fix": Command(
        "人が選んだデータの直しを適用し、承認を記録し直す",
        lambda where, args, today: audit.data_fix(where, int(args.round), _read_chosen(args), today),
        (
            ROUND,
            Option("--apply", "適用する指摘の ID をカンマ区切りで（--none と、どちらか1つ）", required=False),
            Option("--none", "どの直しも適用しない", SWITCH, required=False),
        ),
    ),
    "learn": Command(
        "今の版を候補に写し、学習用の証拠と学習役のプロンプトを作る",
        lambda where, args, _today: learn.learn(where, int(args.round)),
        (ROUND,),
    ),
    "learn-check": Command(
        "学習役の提案と候補を検査し、proposal.md を書く",
        lambda where, args, _today: learn.learn_check(where, int(args.round)),
        (ROUND,),
    ),
    "decide": Command(
        "検証用のスコアで候補を採るかを決める",
        lambda where, args, _today: decide.decide(where, int(args.round)),
        (ROUND,),
    ),
    "report": Command("最後の評価までの経過を report.md にまとめる", lambda where, _args, _today: report.report(where)),
    "apply": Command(
        "最良の版を対象スキルに適用する（--skip で見送る）",
        lambda where, args, today: report.apply(where, bool(args.skip), today),
        (Option("--skip", "適用を見送り、記録だけする", SWITCH, required=False),),
    ),
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=layout.CLI, description="skill-tune の補助 CLI。次にすることは status が示す。"
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="<サブコマンド>")
    for name, command in COMMANDS.items():
        sub = commands.add_parser(name, help=command.help, description=command.help)
        sub.add_argument("--target", required=True, help="対象の ID（.tune/targets/<ID>/）")
        for option in command.options:
            if option.kind == SWITCH:
                sub.add_argument(option.flag, action="store_true", help=option.help)
            else:
                kind = int if option.kind == NUMBER else str
                sub.add_argument(option.flag, type=kind, required=option.required, help=option.help)
    return parser


def main(argv: Sequence[str], root: Path) -> int:
    args = _build_parser().parse_args(list(argv))
    name = str(args.command)
    try:
        where = layout.build_layout(root, str(args.target))
        output = COMMANDS[name].run(where, args, datetime.date.today().isoformat())
    except KitError as exc:
        print(f"エラー: {exc.message}", file=sys.stderr)
        return 1
    print(output)
    if name != "status":
        print(f"次: {layout.CLI} status --target {where.target}")
    return 0
