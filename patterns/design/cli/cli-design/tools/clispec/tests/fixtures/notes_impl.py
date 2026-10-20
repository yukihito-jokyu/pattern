"""見本の実装。specs/notes/released/1.0.0.json を Python の標準ライブラリ（argparse）だけで実装したもの。

適合テスト（tools/clispec conform）の対象であり、.claude/skills/cli-design/references/stdlib-mapping.md の
Python の節をそのまま使う。ヘルプの文面は specs/notes/cli.md から1文字も変えずに写す（OPS-05）。
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

NAME = "notes"
VERSION = "1.0.0"
NOTE_FIELDS = ["id", "created_at", "tags", "title", "updated_at"]
TAG_FIELDS = ["name", "color", "created_at"]
COLORS = ["blue", "green", "red"]

# specs/notes/cli.md から写したヘルプの文面（OPS-05）
HELP = {
    (): """\
Usage: notes <noun> <verb> [options]

Manage notes and tags

Commands:
  note create  Create a note
  note delete  Delete a note
  note edit    Edit a note
  note list    List notes
  note view    View a note
  tag create   Create a tag
  tag delete   Delete a tag
  tag list     List tags

Options:
  -h, --help     Show help
      --version  Show the version
""",
    ('note', 'create'): """\
Usage: notes note create [options]

Create a note

Options:
  -h, --help         Show help
      --json         Write the output as JSON
      --tag TAG      Tag of the note (repeatable)
      --title TITLE  Title of the note (required)
""",
    ('note', 'delete'): """\
Usage: notes note delete [options] <id>

Delete a note

Arguments:
  <id>  ID of the note

Options:
  -h, --help  Show help
      --json  Write the output as JSON
""",
    ('note', 'edit'): """\
Usage: notes note edit [options] <id>

Edit a note

Arguments:
  <id>  ID of the note

Options:
      --clear-tags   Clear the tags of the note
  -h, --help         Show help
      --json         Write the output as JSON
      --tag TAG      New tag of the note (repeatable)
      --title TITLE  New title of the note
""",
    ('note', 'list'): """\
Usage: notes note list [options]

List notes

Options:
  -h, --help         Show help
      --json         Write the output as JSON
      --limit LIMIT  Maximum number of notes to show (default: 20)
      --sort SORT    Field to sort the notes by (one of: created_at, id, title, updated_at; default: id)
      --tag TAG      Show only notes with this tag (repeatable)
""",
    ('note', 'view'): """\
Usage: notes note view [options] <id>

View a note

Arguments:
  <id>  ID of the note

Options:
  -h, --help  Show help
      --json  Write the output as JSON
""",
    ('tag', 'create'): """\
Usage: notes tag create [options] <name>

Create a tag

Arguments:
  <name>  Name of the tag

Options:
      --color COLOR  Color of the tag (one of: blue, green, red)
  -h, --help         Show help
      --json         Write the output as JSON
""",
    ('tag', 'delete'): """\
Usage: notes tag delete [options] <name>

Delete a tag

Arguments:
  <name>  Name of the tag

Options:
  -h, --help  Show help
      --json  Write the output as JSON
""",
    ('tag', 'list'): """\
Usage: notes tag list [options]

List tags

Options:
  -h, --help         Show help
      --json         Write the output as JSON
      --limit LIMIT  Maximum number of tags to show (default: 20)
      --sort SORT    Field to sort the tags by (one of: color, created_at, name; default: name)
""",
}


class UsageError(Exception):
    """終了コード2（ERR-03）。"""


class NotFound(Exception):
    """終了コード3（ERR-01）。"""


class Conflict(Exception):
    """終了コード4（ERR-01）。"""


class Parser(argparse.ArgumentParser):
    def error(self, message: str):  # usage を出さずに1行のエラーにする（ERR-02）
        raise UsageError(message)


def prescan(head: list) -> None:
    """1つのダッシュで始まる語は、標準の短い名前だけを受け付ける（DEP-03。-output を -o utput と読ませない）。"""
    for token in head:
        if token.startswith("-") and not token.startswith("--") and token != "-" and token not in {"-h"}:
            raise UsageError(f"unknown option: {token}")


def integer(text: str) -> int:
    if not re.fullmatch(r"-?[0-9]+", text):
        raise argparse.ArgumentTypeError(f"invalid integer: {text!r}")
    return int(text)


def build(path: tuple) -> Parser:
    p = Parser(prog=" ".join((NAME,) + path), add_help=False, allow_abbrev=False)
    if path == ("note", "create"):
        p.add_argument("--tag", action="append", default=[])
        p.add_argument("--title", required=True)
    if path in (("note", "view"), ("note", "edit"), ("note", "delete")):
        p.add_argument("id", type=integer)
    if path == ("note", "edit"):
        p.add_argument("--clear-tags", action="store_true")
        p.add_argument("--tag", action="append")
        p.add_argument("--title")
    if path in (("tag", "create"), ("tag", "delete")):
        p.add_argument("name")
    if path == ("tag", "create"):
        p.add_argument("--color", choices=COLORS)
    if path[1] == "list":
        p.add_argument("--limit", type=integer, default=20)
    if path == ("note", "list"):
        p.add_argument("--sort", choices=["created_at", "id", "title", "updated_at"], default="id")
        p.add_argument("--tag", action="append", default=[])
    if path == ("tag", "list"):
        p.add_argument("--sort", choices=["color", "created_at", "name"], default="name")
    p.add_argument("--json", action="store_true")
    return p


# --- データの置き場（STATE-01） ---------------------------------------------------

def data_file() -> Path:
    env = os.environ.get("NOTES_DATA_DIR", "")
    if env and os.path.isabs(env):
        directory = Path(env)
    elif os.name == "nt":
        directory = Path(os.environ["LOCALAPPDATA"]) / NAME
    elif os.environ.get("XDG_DATA_HOME", "") and os.path.isabs(os.environ["XDG_DATA_HOME"]):
        directory = Path(os.environ["XDG_DATA_HOME"]) / NAME
    else:
        directory = Path.home() / ".local" / "share" / NAME
    return directory / "notes.json"


def load() -> dict:
    path = data_file()
    if not path.exists():
        return {"next_id": 1, "notes": [], "tags": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save(data: dict) -> None:
    path = data_file()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    tmp.replace(path)


def now() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def find(items: list, key: str, value, noun: str) -> dict:
    for item in items:
        if item[key] == value:
            return item
    raise NotFound(f"{noun} {value} does not exist")


def nonempty(name: str, value: str) -> str:
    if not value:
        raise UsageError(f"{name} must not be empty")
    return value


def sort_rows(rows: list, field: str, key: str, limit: int) -> list:
    if limit < 1:
        raise UsageError("--limit must be 1 or more")
    rows.sort(key=lambda r: (r[field] is None, "" if r[field] is None else r[field], r[key]))  # STATE-02
    return rows[:limit]


# --- コマンド --------------------------------------------------------------------

def note_create(a) -> dict:
    data = load()
    stamp = now()
    note = {"id": data["next_id"], "created_at": stamp, "tags": sorted({nonempty("--tag", t) for t in a.tag}),
            "title": nonempty("--title", a.title), "updated_at": stamp}
    data["next_id"] += 1
    data["notes"].append(note)
    save(data)
    return note


def note_list(a) -> list:
    wanted = [nonempty("--tag", t) for t in a.tag]
    notes = [n for n in load()["notes"] if all(t in n["tags"] for t in wanted)]  # 繰り返しは AND（STATE-02）
    return sort_rows(notes, a.sort, "id", a.limit)


def note_view(a) -> dict:
    return find(load()["notes"], "id", a.id, "note")


def note_edit(a) -> dict:
    if a.title is None and a.tag is None and not a.clear_tags:
        raise UsageError("give --title, --tag, or --clear-tags")
    if a.clear_tags and a.tag is not None:
        raise UsageError("--clear-tags cannot be used with --tag")
    data = load()
    note = find(data["notes"], "id", a.id, "note")
    if a.title is not None:
        note["title"] = nonempty("--title", a.title)
    if a.tag is not None:
        note["tags"] = sorted({nonempty("--tag", t) for t in a.tag})
    if a.clear_tags:
        note["tags"] = []
    note["updated_at"] = now()
    save(data)
    return note


def note_delete(a) -> dict:
    data = load()
    note = find(data["notes"], "id", a.id, "note")
    data["notes"].remove(note)
    save(data)
    return note


def tag_create(a) -> dict:
    data = load()
    if any(t["name"] == a.name for t in data["tags"]):
        raise Conflict(f"tag {a.name} already exists")
    tag = {"name": nonempty("name", a.name), "color": a.color, "created_at": now()}
    data["tags"].append(tag)
    save(data)
    return tag


def tag_delete(a) -> dict:
    data = load()
    tag = find(data["tags"], "name", a.name, "tag")
    data["tags"].remove(tag)
    save(data)
    return tag


def tag_list(a) -> list:
    return sort_rows(load()["tags"], a.sort, "name", a.limit)


COMMANDS = {
    ("note", "create"): (note_create, NOTE_FIELDS),
    ("note", "delete"): (note_delete, NOTE_FIELDS),
    ("note", "edit"): (note_edit, NOTE_FIELDS),
    ("note", "list"): (note_list, NOTE_FIELDS),
    ("note", "view"): (note_view, NOTE_FIELDS),
    ("tag", "create"): (tag_create, TAG_FIELDS),
    ("tag", "delete"): (tag_delete, TAG_FIELDS),
    ("tag", "list"): (tag_list, TAG_FIELDS),
}


# --- 出力（OPS-04） ------------------------------------------------------------------

def cell(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ",".join(cell(v) for v in value) if value else "-"
    return str(value)


def table(fields: list, rows: list) -> str:
    cells = [[f.upper() for f in fields]] + [[cell(r[f]) for f in fields] for r in rows]
    widths = [max(len(c[i]) for c in cells) for i in range(len(fields))]
    lines = ["  ".join(v if i == len(fields) - 1 else v.ljust(widths[i]) for i, v in enumerate(c)) for c in cells]
    return "\n".join(lines) + "\n"


def write(result, fields: list, as_json: bool) -> None:
    rows = result if isinstance(result, list) else [result]
    rows = [{f: r[f] for f in fields} for r in rows]
    if as_json:
        value = rows if isinstance(result, list) else rows[0]
        sys.stdout.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    else:
        sys.stdout.write(table(fields, rows))


# --- 入口 --------------------------------------------------------------------------

def run(argv: list) -> int:
    head = argv[: argv.index("--")] if "--" in argv else argv
    path = tuple(argv[:2])
    if path not in COMMANDS:
        if argv[:1] in (["-h"], ["--help"]):
            sys.stdout.write(HELP[()])
            return 0
        if argv == ["--version"]:
            sys.stdout.write(f"{NAME} {VERSION}\n")
            return 0
        raise UsageError("a command is required" if not argv else f"unknown command: {' '.join(argv[:2])}")
    if "-h" in head or "--help" in head:  # ヘルプは他の誤りより先に出す
        sys.stdout.write(HELP[path])
        return 0
    prescan(head)
    args = build(path).parse_intermixed_args(argv[2:])
    func, fields = COMMANDS[path]
    write(func(args), fields, args.json)
    return 0


def main() -> int:
    try:
        return run(sys.argv[1:])
    except UsageError as exc:
        code, message = 2, str(exc)
    except NotFound as exc:
        code, message = 3, str(exc)
    except Conflict as exc:
        code, message = 4, str(exc)
    except (OSError, ValueError) as exc:
        code, message = 1, str(exc)
    sys.stderr.write(f"{NAME}: {message}\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
