"""ヘルプの文面（OPS-05）とテキストの表の見出し（OPS-04）を仕様から作る。

gen（リファレンス）と conform（適合テスト）が同じ関数を使うので、両者の文面は食い違わない。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import model


def usage(spec: Dict[str, Any], command: Optional[Dict[str, Any]]) -> str:
    if command is None:
        return f"Usage: {spec['name']} <noun> <verb> [options]"
    text = f"Usage: {model.program(spec, command)} [options]"
    for arg in command.get("args", []):
        text += " " + arg_placeholder(arg)
    return text


def arg_placeholder(arg: Dict[str, Any]) -> str:
    name = f"<{arg['name']}>"
    if arg.get("variadic"):
        return f"{name}..." if arg.get("required") else f"[{name}...]"
    return name


def option_left(option: Dict[str, Any]) -> str:
    short = model.short_name(option["name"])
    left = (f"-{short}, " if short else "    ") + f"--{option['name']}"
    if option.get("type") != "boolean":
        left += " " + model.metavar(option["name"])
    return left


def option_notes(option: Dict[str, Any]) -> List[str]:
    notes = []
    if option.get("type") == "enum":
        notes.append("one of: " + ", ".join(option.get("values", [])))
    default = option.get("default")
    if default is not None and option.get("type") != "boolean":
        notes.append(f"default: {format_value(default)}")
    if option.get("required"):
        notes.append("required")
    if option.get("repeatable"):
        notes.append("repeatable")
    return notes


def describe(summary: str, notes: List[str]) -> str:
    return summary + (f" ({'; '.join(notes)})" if notes else "")


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _columns(rows: List[Tuple[str, str]]) -> List[str]:
    width = max(len(left) for left, _ in rows)
    return [f"  {left.ljust(width)}  {right}" for left, right in rows]


def command_help(spec: Dict[str, Any], command: Optional[Dict[str, Any]]) -> str:
    """1つのコマンド（None ならサブコマンドを持つ CLI のルート）のヘルプの文面。末尾に改行を付ける。"""
    lines = [usage(spec, command), ""]
    if command is None:
        lines += [spec["summary"], "", "Commands:"]
        lines += _columns([(" ".join(c["path"]), c["summary"]) for c in spec["commands"]])
    else:
        lines.append(command["summary"])
        if command.get("args"):
            lines += ["", "Arguments:"]
            lines += _columns([(arg_placeholder(a), describe(a["summary"], _arg_notes(a))) for a in command["args"]])
    options = list(command.get("options", []) if command else []) + model.implicit_options(spec, command)
    options.sort(key=lambda o: o["name"])
    lines += ["", "Options:"]
    lines += _columns([(option_left(o), describe(o["summary"], option_notes(o))) for o in options])
    return "\n".join(lines) + "\n"


def _arg_notes(arg: Dict[str, Any]) -> List[str]:
    if arg.get("type") == "enum":
        return ["one of: " + ", ".join(arg.get("values", []))]
    return []


def all_helps(spec: Dict[str, Any]) -> List[Tuple[List[str], str]]:
    """(コマンドの path, ヘルプの文面) の一覧。サブコマンドを持つ CLI はルートを先頭に置く。"""
    if model.is_single(spec):
        return [([], command_help(spec, spec["commands"][0]))]
    result = [([], command_help(spec, None))]
    result += [(c["path"], command_help(spec, c)) for c in spec["commands"]]
    return result


def table_header(type_: Dict[str, Any]) -> List[str]:
    return [f["name"].upper() for f in type_.get("fields", [])]


def table(type_: Dict[str, Any], rows: List[Dict[str, Any]]) -> str:
    """テキストの表（OPS-04）。リファレンスの例に使う。"""
    header = table_header(type_)
    cells = [header] + [[cell(row.get(f["name"])) for f in type_["fields"]] for row in rows]
    widths = [max(len(r[i]) for r in cells) for i in range(len(header))]
    lines = []
    for r in cells:
        parts = [value.ljust(widths[i]) if i < len(r) - 1 else value for i, value in enumerate(r)]
        lines.append("  ".join(parts))
    return "\n".join(lines) + "\n"


def cell(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, list):
        return ",".join(cell(v) for v in value) if value else "-"
    return format_value(value)
