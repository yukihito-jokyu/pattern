"""ルールの表。docs/design/rules.md の表と1対1で対応させ、片方を変えたらもう片方も変える。"""

from __future__ import annotations

import re

# NAM-01 名前の形
CLI_NAME = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
CLI_NAME_LENGTH = (2, 20)
WORD = re.compile(r"^[a-z]+$")
KEBAB = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
SNAKE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
ENV_SUFFIX = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")

# OPS-06 配布
WINDOWS_RESERVED = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(1, 10)} | {f"lpt{i}" for i in range(1, 10)}
GO_MAJOR_SUFFIX = re.compile(r"^v[0-9]+$")
VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")

# CODE-02 値の型と使える場所
VALUE_TYPES = ["string", "integer", "number", "boolean", "enum", "date", "timestamp", "file", "directory"]
ARG_TYPES = ["string", "integer", "number", "enum", "date", "file", "directory"]
OPTION_TYPES = ["string", "integer", "number", "boolean", "enum", "date", "file", "directory"]
ENV_TYPES = ["string", "integer", "number", "enum", "date", "file", "directory"]
FIELD_TYPES = ["string", "integer", "number", "boolean", "enum", "date", "timestamp"]
DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
TIMESTAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")

# OPS-04 出力の種類
OUTPUT_KINDS = ["object", "list", "raw", "none"]
STORAGE = ["none", "data"]

# ERR-01 終了コード
EXIT_CODES = {
    0: "Success",
    1: "Unexpected failure, such as a file that cannot be read or written",
    2: "Invalid usage, such as an unknown option or a value of the wrong type",
    3: "The specified item, file, or directory does not exist",
    4: "An item with the same name already exists",
}

# NAM-03 標準のオプション: 名前 → (短い名前, 型, 使わない名前)
STANDARD_OPTIONS = {
    "all": ("a", "boolean", ["everything", "include-all"]),
    "debug": ("d", "boolean", ["verbose"]),
    "dry-run": ("n", "boolean", ["dryrun", "simulate", "noop"]),
    "force": ("f", "boolean", ["yes", "confirm", "assume-yes"]),
    "output": ("o", "file", ["out", "outfile", "output-file", "out-file"]),
    "port": ("p", "integer", []),
    "quiet": ("q", "boolean", ["silent"]),
    "user": ("u", "string", ["username", "login"]),
}
IMPLICIT_OPTIONS = ["help", "version", "json"]

# NAM-04 標準の動詞: 動詞 → (位置引数, output.kind, 使わない語)。位置引数 "key" は識別子、"create" は create の規則
STANDARD_VERBS = {
    "create": ("create", "object", ["add", "new", "make", "insert", "register"]),
    "list": ("none", "list", ["ls", "search", "find", "query", "filter"]),
    "view": ("key", "object", ["show", "get", "fetch", "read", "display", "describe", "inspect", "info"]),
    "edit": ("key", "object", ["update", "modify", "change", "set"]),
    "delete": ("key", "object", ["remove", "rm", "del", "destroy", "erase", "drop"]),
}
FORBIDDEN_VERBS = {word: verb for verb, (_, _, words) in STANDARD_VERBS.items() for word in words}
KEY_FIELDS = {"id": "integer", "name": "string"}

# NAM-06 略語: 使わない語 → 代わりの語
# CODE-04 summary の中で大文字にする語（NAM-06 で使ってよい略語のうち頭字語のもの）
ACRONYMS = {"id": "ID", "url": "URL", "json": "JSON"}

ABBREVIATIONS = {
    "num": "number", "no": "number", "cnt": "count", "desc": "description", "descr": "description",
    "msg": "message", "cfg": "(no config files)", "conf": "(no config files)", "tmp": "temporary",
    "str": "a word for the meaning", "val": "a word for the meaning", "obj": "a word for the meaning",
    "arr": "a word for the meaning", "len": "length", "idx": "index", "pwd": "password", "usr": "user",
    "src": "source", "dst": "destination", "dest": "destination", "ts": "_at", "dt": "_date",
    "qty": "quantity", "amt": "amount", "addr": "address", "info": "a word for the meaning",
}

# NAM-05 真偽値に付けない接頭辞
BOOLEAN_PREFIXES = ["is_", "has_", "is-", "has-", "no-"]

# NAM-07 list の --limit の既定値
LIST_LIMIT_DEFAULT = 20

# OPS-02 秘密情報を表す語
SECRET_WORDS = ["password", "passwd", "token", "secret", "credential", "api-key", "private-key"]

# CODE-03 大きさの上限
MAX_NOUNS = 8
MAX_ARGS = 1
MAX_OPTIONS = 10
MAX_FIELDS = 12
MAX_SUMMARY = 60

# CODE-05 summary に書かない語
SUMMARY_FORBIDDEN = ["default", "one of", "required", "optional", "repeatable", "e.g.", "("]

# STATE-01 データの置き場の環境変数
DATA_DIR_SUMMARY = "Directory for data files"
