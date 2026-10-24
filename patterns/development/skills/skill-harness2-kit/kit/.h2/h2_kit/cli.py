"""補助 CLI の入口。引数を読み、段を呼び、結果を標準出力、エラーを標準エラーに出す（OPS-01）。"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from h2_kit import adoption, execution, judging, layout, planning, results, status
from h2_kit.errors import KitError

COMMANDS = ("init", "check", "approve", "status", "run", "show", "adopt", "judge")


def main(argv: Sequence[str], repo: Path) -> int:
    """終了コードは成功 0、失敗 1、引数の誤り 2（argparse）。"""
    args = _build_parser().parse_args(list(argv))
    try:
        where = layout.Layout(repo, layout.require_name("対象", args.target))
        text = HANDLERS[args.command](where, args)
    except KitError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    print(text)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="h2.py", description="skill-harness2 の補助 CLI")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        command = commands.add_parser(name)
        command.add_argument("target", help="対象の名前（.h2/targets/<対象>/）")
    commands.choices["init"].add_argument(
        "--skill", required=True, help="対象スキルのディレクトリ（リポジトリからの相対パス）"
    )
    for name in ("run", "show", "judge"):
        commands.choices[name].add_argument("--task", help="1つのタスクだけにする")
    commands.choices["show"].add_argument("--mode", choices=layout.MODES, help="1つのモードだけにする")
    adopt = commands.choices["adopt"]
    adopt.add_argument("--task", required=True)
    adopt.add_argument("--mode", required=True, choices=layout.MODES)
    adopt.add_argument("--confirm", required=True, help="show が出した確認の符号")
    return parser


def _run_init(where: layout.Layout, args: argparse.Namespace) -> str:
    return planning.init(where, str(args.skill))


def _run_check(where: layout.Layout, _args: argparse.Namespace) -> str:
    return planning.check(where)


def _run_approve(where: layout.Layout, _args: argparse.Namespace) -> str:
    return planning.approve(where, date.today().isoformat())


def _run_status(where: layout.Layout, _args: argparse.Namespace) -> str:
    return status.status(where)


def _run_run(where: layout.Layout, args: argparse.Namespace) -> str:
    return execution.run(where, args.task, _write_progress)


def _run_show(where: layout.Layout, args: argparse.Namespace) -> str:
    return results.show(where, args.task, args.mode)


def _run_adopt(where: layout.Layout, args: argparse.Namespace) -> str:
    return adoption.adopt(where, str(args.task), str(args.mode), str(args.confirm), date.today().isoformat())


def _run_judge(where: layout.Layout, args: argparse.Namespace) -> str:
    return judging.judge(where, args.task)


def _write_progress(line: str) -> None:
    print(line, flush=True)


HANDLERS: dict[str, Callable[[layout.Layout, argparse.Namespace], str]] = {
    "init": _run_init,
    "check": _run_check,
    "approve": _run_approve,
    "status": _run_status,
    "run": _run_run,
    "show": _run_show,
    "adopt": _run_adopt,
    "judge": _run_judge,
}
