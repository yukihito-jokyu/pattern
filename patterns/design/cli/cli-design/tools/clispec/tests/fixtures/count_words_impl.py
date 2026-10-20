"""見本の実装。specs/count-words/released/1.0.0.json を Python の標準ライブラリ（argparse）だけで実装したもの。

サブコマンドを持たない CLI の見本であり、notes_impl.py と同じく stdlib-mapping.md の Python の節を使う。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter

NAME = "count-words"
VERSION = "1.0.0"
FIELDS = ["count", "word"]

# specs/count-words/cli.md から写したヘルプの文面（OPS-05）
HELP = {
    (): """\
Usage: count-words [options] <file>...

Count words in files

Arguments:
  <file>...  File to read, or - to read stdin

Options:
  -h, --help                   Show help
      --json                   Write the output as JSON
      --limit LIMIT            Maximum number of words to show (default: 20)
      --min-length MIN_LENGTH  Minimum length of a word to count (default: 1)
  -o, --output OUTPUT          File to write the output to
      --version                Show the version
""",
}


class UsageError(Exception):
    """終了コード2（ERR-03）。"""


class NotFound(Exception):
    """終了コード3（ERR-01）。"""


class Parser(argparse.ArgumentParser):
    def error(self, message: str):  # usage を出さずに1行のエラーにする（ERR-02）
        raise UsageError(message)


def prescan(head: list) -> None:
    """1つのダッシュで始まる語は、標準の短い名前だけを受け付ける（DEP-03。-output を -o utput と読ませない）。"""
    for token in head:
        if token.startswith("-") and not token.startswith("--") and token != "-" and token not in {"-h", "-o"}:
            raise UsageError(f"unknown option: {token}")


def integer(text: str) -> int:
    if not re.fullmatch(r"-?[0-9]+", text):
        raise argparse.ArgumentTypeError(f"invalid integer: {text!r}")
    return int(text)


def build() -> Parser:
    p = Parser(prog=NAME, add_help=False, allow_abbrev=False)
    p.add_argument("file", nargs="+")
    p.add_argument("--limit", type=integer, default=20)
    p.add_argument("--min-length", type=integer)
    p.add_argument("-o", "--output")
    p.add_argument("--json", action="store_true")
    return p


def min_length(value) -> int:
    """オプション → 環境変数 → 既定値の順に決める（STATE-01）。"""
    if value is None:
        env = os.environ.get("COUNT_WORDS_MIN_LENGTH", "")
        if not env:
            return 1
        try:
            value = integer(env)
        except argparse.ArgumentTypeError:
            raise UsageError(f"COUNT_WORDS_MIN_LENGTH: invalid integer: {env!r}") from None
    return value


def read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        raise NotFound(f"{path} does not exist") from None


def count(a) -> list:
    shortest = min_length(a.min_length)
    if a.limit < 1 or shortest < 1:
        raise UsageError("--limit and --min-length must be 1 or more")
    counter: Counter = Counter()
    for path in a.file:
        counter.update(w for w in re.findall(r"[a-z0-9]+", read(path).lower()) if len(w) >= shortest)
    rows = sorted(counter.items(), key=lambda item: (-item[1], item[0]))[: a.limit]
    return [{"count": n, "word": w} for w, n in rows]


def cell(value) -> str:
    return "-" if value is None else str(value)


def table(rows: list) -> str:
    cells = [[f.upper() for f in FIELDS]] + [[cell(r[f]) for f in FIELDS] for r in rows]
    widths = [max(len(c[i]) for c in cells) for i in range(len(FIELDS))]
    lines = ["  ".join(v if i == len(FIELDS) - 1 else v.ljust(widths[i]) for i, v in enumerate(c)) for c in cells]
    return "\n".join(lines) + "\n"


def run(argv: list) -> int:
    head = argv[: argv.index("--")] if "--" in argv else argv
    if "-h" in head or "--help" in head:
        sys.stdout.write(HELP[()])
        return 0
    if argv == ["--version"]:
        sys.stdout.write(f"{NAME} {VERSION}\n")
        return 0
    prescan(head)
    args = build().parse_intermixed_args(argv)
    rows = count(args)
    text = json.dumps(rows, separators=(",", ":")) + "\n" if args.json else table(rows)
    if args.output and args.output != "-":
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    return 0


def main() -> int:
    try:
        return run(sys.argv[1:])
    except UsageError as exc:
        code, message = 2, str(exc)
    except NotFound as exc:
        code, message = 3, str(exc)
    except (OSError, ValueError) as exc:
        code, message = 1, str(exc)
    sys.stderr.write(f"{NAME}: {message}\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
