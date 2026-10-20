"""仕様の検査。エラーは `<ルールID> <パス>:<行> <JSON の位置>: <説明>` の形で出す。

ルールの全文は docs/design/rules.md にある。関数は rules.md の節の順に並べてある。
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

import canon
import compat
import model
import vocab

PathT = Tuple[Any, ...]


class Finding(NamedTuple):
    rule: str
    file: str
    line: int
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.rule} {self.file}:{self.line} {self.where}: {self.message}"


class Ctx:
    """1つのファイルの検査の文脈。JSON の位置から行番号を引く。"""

    def __init__(self, root: Path, file: Path, data: Any, out: List[Finding]) -> None:
        self.file = file.relative_to(root).as_posix() if file.is_absolute() else file.as_posix()
        _, self.index = canon.render(data)
        self.out = out

    def err(self, rule: str, path: PathT, message: str) -> None:
        line = 1
        for n in range(len(path), -1, -1):
            if path[:n] in self.index:
                line = self.index[path[:n]]
                break
        self.out.append(Finding(rule, self.file, line, canon.pointer(path), message))


def check(root: Path, targets: List[str]) -> List[Finding]:
    out: List[Finding] = []
    whole = not targets or [t.rstrip("/") for t in targets] == [model.SPECS_DIR]
    if whole:
        check_specs_root(root, out)
    for spec_dir in model.iter_spec_dirs(root, targets):
        check_spec_dir(root, spec_dir, out)
    return out


# --- STR-01 配置 -------------------------------------------------------------

IGNORED_NAMES = {".DS_Store"}
ROOT_ENTRIES = ("AGENTS.md", "CLAUDE.md", "Makefile", "README.md", "ci.json", "docs", "specs", "tools")


def check_specs_root(root: Path, out: List[Finding]) -> None:
    for entry in sorted(root.iterdir()):
        if not entry.name.startswith(".") and entry.name not in ROOT_ENTRIES:
            out.append(Finding("STR-01", entry.name, 1, "(root)",
                               f"基盤の直下に置けるのは {'・'.join(ROOT_ENTRIES)} と . で始まる名前だけ（実装は基盤の外に置く）"))
    specs = root / model.SPECS_DIR
    if not specs.is_dir():
        out.append(Finding("STR-01", model.SPECS_DIR, 1, "(root)", "specs/ がありません"))
        return
    for entry in sorted(specs.iterdir()):
        if entry.name in IGNORED_NAMES:
            continue
        if not entry.is_dir():
            out.append(Finding("STR-01", f"{model.SPECS_DIR}/{entry.name}", 1, "(root)",
                               "specs/ の直下には CLI ごとのディレクトリだけを置く"))


def check_spec_dir(root: Path, spec_dir: Path, out: List[Finding]) -> None:
    rel = spec_dir.relative_to(root).as_posix()
    for entry in sorted(spec_dir.iterdir()):
        if entry.name in IGNORED_NAMES:
            continue
        if entry.name == model.RELEASED_DIR and entry.is_dir():
            for item in sorted(entry.iterdir()):
                if item.name in IGNORED_NAMES:
                    continue
                if not (item.is_file() and item.suffix == ".json" and vocab.VERSION.match(item.stem)):
                    out.append(Finding("STR-01", f"{rel}/{model.RELEASED_DIR}/{item.name}", 1, "(root)",
                                       "released/ に置けるのは <MAJOR>.<MINOR>.<PATCH>.json だけ"))
            continue
        if entry.name not in (model.SPEC_FILE, model.DOC_FILE) or not entry.is_file():
            out.append(Finding("STR-01", f"{rel}/{entry.name}", 1, "(root)",
                               "CLI のディレクトリに置けるのは cli.json・cli.md・released/ だけ"))
    spec_file = spec_dir / model.SPEC_FILE
    if not spec_file.is_file():
        out.append(Finding("STR-01", f"{rel}/{model.SPEC_FILE}", 1, "(root)", "cli.json がありません"))
        return
    try:
        spec = model.load(spec_file)
    except model.SpecError as exc:
        out.append(Finding("CODE-01", f"{rel}/{model.SPEC_FILE}", 1, "(root)", str(exc)))
        return
    ctx = Ctx(root, spec_file, spec, out)
    if not shape(ctx, spec, "spec", ()):
        return
    if spec["name"] != spec_dir.name:
        ctx.err("STR-01", ("name",), f"name {spec['name']!r} をディレクトリ名 {spec_dir.name!r} と同じにする")
    check_spec(ctx, spec)
    check_released(root, spec_dir, spec, ctx, out)


# --- CODE-01 キーの過不足と値の種類（DEP-01、TOOL-03 のキーを含む） ----------------

SCALAR = "scalar"
OPT_STR = "str-or-null"
SHAPES: Dict[str, Dict[str, Any]] = {
    "spec": {"name": str, "version": str, "summary": str, "storage": str, "commands": list, "types": list,
             "env": list},
    "command": {"path": list, "summary": str, "args": list, "options": list, "output": dict, "exit_codes": list},
    "arg": {"name": str, "type": str, "values": list, "required": bool, "variadic": bool, "summary": str},
    "option": {"name": str, "type": str, "values": list, "default": SCALAR, "required": bool, "repeatable": bool,
               "summary": str},
    "output": {"kind": str, "type": OPT_STR},
    "type": {"name": str, "fields": list},
    "field": {"name": str, "type": str, "values": list, "list": bool, "nullable": bool},
    "env": {"name": str, "type": str, "values": list, "default": SCALAR, "summary": str},
}
TYPE_LABEL = {str: "文字列", list: "配列", dict: "オブジェクト", bool: "真偽値"}


def unknown_key_rule(key: str) -> str:
    if key in ("$ref", "$schema", "extends"):
        return "DEP-01"
    if key.startswith(("$", "x-", "_")):
        return "TOOL-03"
    return "CODE-01"


def shape(ctx: Ctx, obj: Any, kind: str, path: PathT) -> bool:
    if not isinstance(obj, dict):
        ctx.err("CODE-01", path, f"{kind} はオブジェクトにする")
        return False
    ok = True
    expected = SHAPES[kind]
    for key in obj:
        if key not in expected:
            rule = unknown_key_rule(key)
            reason = {"DEP-01": "仕様の外を参照するキーを書かない",
                      "TOOL-03": "検査を黙らせるキー・注釈のキーを書かない"}.get(rule, "表に無いキーを書かない")
            ctx.err(rule, path + (key,), f"キー {key!r} は {kind} に無い（{reason}）")
            ok = False
    for key, want in expected.items():
        if key not in obj:
            ctx.err("CODE-01", path, f"{kind} にキー {key!r} がありません（キーは全部書く）")
            ok = False
            continue
        value = obj[key]
        if want is SCALAR:
            good = value is None or isinstance(value, (str, int, float, bool))
        elif want is OPT_STR:
            good = value is None or isinstance(value, str)
        elif want is bool:
            good = isinstance(value, bool)
        else:
            good = isinstance(value, want) and not isinstance(value, bool)
        if not good:
            label = {SCALAR: "スカラーか null", OPT_STR: "文字列か null"}.get(want) or TYPE_LABEL[want]
            ctx.err("CODE-01", path + (key,), f"{key} は{label}にする")
            ok = False
    if not ok:
        return False
    if kind == "command":
        if not all(isinstance(p, str) for p in obj["path"]):
            ctx.err("CODE-01", path + ("path",), "path は文字列の配列にする")
            ok = False
        if not all(isinstance(c, int) and not isinstance(c, bool) for c in obj["exit_codes"]):
            ctx.err("CODE-01", path + ("exit_codes",), "exit_codes は整数の配列にする")
            ok = False
        ok = shape(ctx, obj["output"], "output", path + ("output",)) and ok
    if "values" in obj and not all(isinstance(v, str) for v in obj["values"]):
        ctx.err("CODE-01", path + ("values",), "values は文字列の配列にする")
        ok = False
    for key, child in model.CHILDREN.items():
        if key in expected and key in obj:
            for i, item in enumerate(obj[key]):
                ok = shape(ctx, item, child, path + (key, i)) and ok
    return ok


# --- 仕様全体 -------------------------------------------------------------

def check_spec(ctx: Ctx, spec: Dict[str, Any]) -> None:
    check_structure(ctx, spec)
    check_names(ctx, spec)
    check_values(ctx, spec)
    check_texts(ctx, spec)
    check_exit_codes(ctx, spec)
    check_settings(ctx, spec)
    check_distribution(ctx, spec)


def each_command(spec):
    for i, command in enumerate(spec["commands"]):
        yield ("commands", i), command


def each_param(spec):
    """(位置, コマンド, 種類, 要素)。種類は arg か option。"""
    for cpath, command in each_command(spec):
        for j, arg in enumerate(command["args"]):
            yield cpath + ("args", j), command, "arg", arg
        for j, option in enumerate(command["options"]):
            yield cpath + ("options", j), command, "option", option


def each_field(spec):
    for i, type_ in enumerate(spec["types"]):
        for j, field in enumerate(type_["fields"]):
            yield ("types", i, "fields", j), type_, field


# --- STR-03、STR-05、DEP-01、OPS-04 構成と参照 ---------------------------------

def check_structure(ctx: Ctx, spec: Dict[str, Any]) -> None:
    commands = spec["commands"]
    paths = [c["path"] for c in commands]
    if not commands:
        ctx.err("STR-05", ("commands",), "コマンドが1つもありません")
    elif any(p == [] for p in paths):
        if len(commands) != 1:
            ctx.err("STR-05", ("commands",), "path が [] のコマンドは、操作が1つの CLI に1つだけ置く")
    else:
        if len(commands) < 2:
            ctx.err("STR-05", ("commands", 0, "path"), "操作が1つなら path を [] にする")
        for cpath, command in each_command(spec):
            if len(command["path"]) != 2:
                ctx.err("STR-05", cpath + ("path",), "サブコマンドは [\"<名詞>\", \"<動詞>\"] の2段にする")
    seen = set()
    for cpath, command in each_command(spec):
        key = tuple(command["path"])
        if key in seen:
            ctx.err("STR-05", cpath + ("path",), f"path {list(key)} が重複しています")
        seen.add(key)
    if len(model.nouns(spec)) > vocab.MAX_NOUNS:
        ctx.err("CODE-03", ("commands",), f"名詞は {vocab.MAX_NOUNS} 個以下にする")

    types = model.types_by_name(spec)
    names = [t["name"] for t in spec["types"]]
    for i, name in enumerate(names):
        if names.count(name) > 1 and names.index(name) == i:
            ctx.err("STR-03", ("types", i, "name"), f"型 {name!r} が重複しています")
    referenced = set()
    for cpath, command in each_command(spec):
        output = command["output"]
        kind, tname = output["kind"], output["type"]
        if kind not in vocab.OUTPUT_KINDS:
            ctx.err("OPS-04", cpath + ("output", "kind"), f"kind は {vocab.OUTPUT_KINDS} のどれかにする")
            continue
        if kind in ("object", "list"):
            if tname is None:
                ctx.err("OPS-04", cpath + ("output", "type"), f"kind が {kind} なら type に型の名前を書く")
            elif re.search(r"[/#.]", tname):
                ctx.err("DEP-01", cpath + ("output", "type"), "type には同じ仕様の types の名前だけを書く")
            elif tname not in types:
                ctx.err("STR-03", cpath + ("output", "type"), f"型 {tname!r} が types にありません")
            else:
                referenced.add(tname)
        elif tname is not None:
            ctx.err("OPS-04", cpath + ("output", "type"), f"kind が {kind} なら type は null にする")
    for i, name in enumerate(names):
        if name not in referenced:
            ctx.err("STR-03", ("types", i), f"型 {name!r} はどのコマンドの output からも参照されていません")
    for fpath, _, field in each_field(spec):
        if field["type"] in types:
            ctx.err("STR-03", fpath + ("type",), "項目の型に別の型を書かない（入れ子にしない）")
    for i, type_ in enumerate(spec["types"]):
        if len(type_["fields"]) > vocab.MAX_FIELDS:
            ctx.err("CODE-03", ("types", i, "fields"), f"項目は {vocab.MAX_FIELDS} 個以下にする")
        if not type_["fields"]:
            ctx.err("STR-03", ("types", i, "fields"), "項目が1つもありません")


# --- NAM 命名 --------------------------------------------------------------

def check_names(ctx: Ctx, spec: Dict[str, Any]) -> None:
    pre = model.prefix(spec["name"])
    if not vocab.CLI_NAME.match(spec["name"]) or not (
            vocab.CLI_NAME_LENGTH[0] <= len(spec["name"]) <= vocab.CLI_NAME_LENGTH[1]):
        ctx.err("NAM-01", ("name",), "CLI 名は英小文字で始まる kebab-case の2〜20文字にする")
    for cpath, command in each_command(spec):
        for k, word in enumerate(command["path"]):
            if not vocab.WORD.match(word):
                ctx.err("NAM-01", cpath + ("path", k), f"{word!r} は英小文字1語にする")
    for ppath, _, kind, param in each_param(spec):
        if not vocab.KEBAB.match(param["name"]) or len(param["name"]) < 2:
            ctx.err("NAM-01", ppath + ("name",), f"{param['name']!r} は2文字以上の kebab-case にする")
    for i, type_ in enumerate(spec["types"]):
        if not vocab.SNAKE.match(type_["name"]):
            ctx.err("NAM-01", ("types", i, "name"), f"{type_['name']!r} は snake_case にする")
    for fpath, _, field in each_field(spec):
        if not vocab.SNAKE.match(field["name"]):
            ctx.err("NAM-01", fpath + ("name",), f"{field['name']!r} は snake_case にする")
    for vpath, values in _each_values(spec):
        for k, value in enumerate(values):
            if not vocab.SNAKE.match(value):
                ctx.err("NAM-01", vpath + (k,), f"選択肢 {value!r} は snake_case にする")
    for i, env in enumerate(spec["env"]):
        name = env["name"]
        if not (name.startswith(pre + "_") and vocab.ENV_SUFFIX.match(name[len(pre) + 1:])):
            ctx.err("NAM-01", ("env", i, "name"), f"環境変数名は {pre}_ で始まる大文字の snake_case にする")

    check_roles(ctx, spec)
    check_standard_options(ctx, spec)
    check_verbs(ctx, spec)
    check_kinds_in_names(ctx, spec)
    check_abbreviations(ctx, spec)
    check_option_fields(ctx, spec)


def _each_values(spec):
    for ppath, _, _, param in each_param(spec):
        yield ppath + ("values",), param["values"]
    for fpath, _, field in each_field(spec):
        yield fpath + ("values",), field["values"]
    for i, env in enumerate(spec["env"]):
        yield ("env", i, "values"), env["values"]


def check_roles(ctx: Ctx, spec: Dict[str, Any]) -> None:
    """NAM-02 役割ごとの名前。"""
    types = model.types_by_name(spec)
    type_index = {t["name"]: i for i, t in enumerate(spec["types"])}
    for noun in model.nouns(spec):
        verbs = model.verbs_of(spec, noun)
        if not any(v in vocab.STANDARD_VERBS for v in verbs):
            continue
        type_ = types.get(noun)
        if type_ is None:
            ctx.err("NAM-02", ("types",), f"名詞 {noun!r} の型 {noun!r} がありません（型の名前は名詞と同じにする）")
            continue
        tpath = ("types", type_index[noun])
        key = model.key_field(type_)
        if key is None:
            ctx.err("NAM-02", tpath + ("fields",), "名詞の型の先頭に識別子の項目（id か name）を置く")
        elif key["type"] != vocab.KEY_FIELDS[key["name"]] or key["list"] or key["nullable"]:
            ctx.err("NAM-02", tpath + ("fields", 0),
                    f"識別子の項目 {key['name']} は {vocab.KEY_FIELDS[key['name']]} の、list と nullable が false の項目にする")
        fields = {f["name"]: f for f in type_["fields"]}
        for verb, fname in (("create", "created_at"), ("edit", "updated_at")):
            if verb in verbs:
                f = fields.get(fname)
                if f is None or f["type"] != "timestamp" or f["list"] or f["nullable"]:
                    ctx.err("NAM-02", tpath + ("fields",),
                            f"{verb} を持つ名詞の型には {fname}（timestamp、list と nullable は false）を置く")
    for fpath, _, field in each_field(spec):
        name, ftype = field["name"], field["type"]
        if ftype == "timestamp" and not name.endswith("_at"):
            ctx.err("NAM-02", fpath + ("name",), "timestamp の項目の名前は <意味>_at にする")
        if ftype != "timestamp" and name.endswith("_at"):
            ctx.err("NAM-02", fpath + ("name",), "_at で終わる名前は timestamp の項目だけに使う")
        if ftype == "date" and not name.endswith("_date"):
            ctx.err("NAM-02", fpath + ("name",), "date の項目の名前は <意味>_date にする")
        if ftype != "date" and name.endswith("_date"):
            ctx.err("NAM-02", fpath + ("name",), "_date で終わる名前は date の項目だけに使う")


def check_standard_options(ctx: Ctx, spec: Dict[str, Any]) -> None:
    """NAM-03 標準のオプション。"""
    forbidden = {w: std for std, (_, _, words) in vocab.STANDARD_OPTIONS.items() for w in words}
    for ppath, _, kind, param in each_param(spec):
        if kind != "option":
            continue
        name = param["name"]
        if name in vocab.IMPLICIT_OPTIONS:
            ctx.err("NAM-03", ppath + ("name",), f"--{name} は暗黙のオプションなので宣言しない")
        elif name in forbidden:
            ctx.err("NAM-03", ppath + ("name",), f"--{name} ではなく標準の --{forbidden[name]} を使う")
        elif name in vocab.STANDARD_OPTIONS and param["type"] != vocab.STANDARD_OPTIONS[name][1]:
            ctx.err("NAM-03", ppath + ("type",), f"--{name} の型は {vocab.STANDARD_OPTIONS[name][1]} にする")


def check_verbs(ctx: Ctx, spec: Dict[str, Any]) -> None:
    """NAM-04 動詞と、標準の動詞の位置引数・出力。NAM-02 の識別子の位置引数も見る。"""
    for cpath, command in each_command(spec):
        if len(command["path"]) != 2:
            continue
        noun, verb = command["path"]
        if verb in vocab.FORBIDDEN_VERBS:
            ctx.err("NAM-04", cpath + ("path", 1), f"動詞 {verb!r} ではなく標準の {vocab.FORBIDDEN_VERBS[verb]!r} を使う")
            continue
        if verb not in vocab.STANDARD_VERBS:
            continue
        arg_rule, kind, _ = vocab.STANDARD_VERBS[verb]
        output = command["output"]
        if output["kind"] != kind or (output["type"] is not None and output["type"] != noun):
            ctx.err("NAM-04", cpath + ("output",), f"{verb} の output は {{\"kind\": \"{kind}\", \"type\": \"{noun}\"}} にする")
        type_ = model.noun_type(spec, command)
        key = model.key_field(type_)
        args = command["args"]
        if arg_rule == "none":
            if args:
                ctx.err("NAM-04", cpath + ("args",), f"{verb} は位置引数を持たない")
        elif arg_rule == "key":
            if key is None:
                continue
            if len(args) != 1 or args[0]["name"] != key["name"] or args[0]["variadic"]:
                ctx.err("NAM-04", cpath + ("args",), f"{verb} の位置引数は識別子 {key['name']!r} の1つだけにする")
            elif args[0]["type"] != key["type"]:
                ctx.err("NAM-02", cpath + ("args", 0, "type"), f"識別子の位置引数の型は {key['type']} にする")
        elif arg_rule == "create" and key is not None:
            if key["name"] == "id":
                if args:
                    ctx.err("NAM-04", cpath + ("args",), "識別子が id の名詞の create は位置引数を持たない（値は全部オプションで受け取る）")
            elif len(args) != 1 or args[0]["name"] != "name" or args[0]["variadic"]:
                ctx.err("NAM-04", cpath + ("args",), "識別子が name の名詞の create は、位置引数を name の1つだけにする")


def check_kinds_in_names(ctx: Ctx, spec: Dict[str, Any]) -> None:
    """NAM-05 名前で値の種類が分かるようにする。"""
    for ppath, _, kind, param in each_param(spec):
        name = param["name"]
        if param["type"] == "boolean" and name.startswith(tuple(vocab.BOOLEAN_PREFIXES)):
            ctx.err("NAM-05", ppath + ("name",), "真偽値の名前を is-・has-・no- で始めない")
        if kind == "option" and param["repeatable"] and name.endswith("s"):
            ctx.err("NAM-05", ppath + ("name",), "繰り返すオプションの名前は単数形にする")
    for fpath, _, field in each_field(spec):
        name = field["name"]
        if field["type"] == "boolean" and name.startswith(tuple(vocab.BOOLEAN_PREFIXES)):
            ctx.err("NAM-05", fpath + ("name",), "真偽値の項目の名前を is_・has_ で始めない")
        if field["list"] and not name.endswith("s"):
            ctx.err("NAM-05", fpath + ("name",), "list が true の項目の名前は複数形にする")


def check_abbreviations(ctx: Ctx, spec: Dict[str, Any]) -> None:
    """NAM-06 略語。"""
    def words(path: PathT, name: str) -> None:
        for word in re.split(r"[-_]", name.lower()):
            if word in vocab.ABBREVIATIONS:
                ctx.err("NAM-06", path, f"略語 {word!r} を使わない（代わり: {vocab.ABBREVIATIONS[word]}）")
    words(("name",), spec["name"])
    for cpath, command in each_command(spec):
        for k, word in enumerate(command["path"]):
            words(cpath + ("path", k), word)
    for ppath, _, _, param in each_param(spec):
        words(ppath + ("name",), param["name"])
    for i, type_ in enumerate(spec["types"]):
        words(("types", i, "name"), type_["name"])
    for fpath, _, field in each_field(spec):
        words(fpath + ("name",), field["name"])
    pre = model.prefix(spec["name"])
    for i, env in enumerate(spec["env"]):
        words(("env", i, "name"), env["name"][len(pre) + 1:] if env["name"].startswith(pre + "_") else env["name"])


def check_option_fields(ctx: Ctx, spec: Dict[str, Any]) -> None:
    """NAM-07 標準の動詞のオプションを型の項目から作る。"""
    for cpath, command in each_command(spec):
        if len(command["path"]) != 2 or command["path"][1] not in vocab.STANDARD_VERBS:
            continue
        noun, verb = command["path"]
        type_ = model.noun_type(spec, command)
        if type_ is None:
            continue
        required, allowed = model.option_plan(type_, verb)
        names = [o["name"] for o in command["options"]]
        for name in required:
            if name not in names:
                ctx.err("NAM-07", cpath + ("options",), f"{verb} には --{name} を必ず置く（make command・make field が足す）")
        for name in names:
            for have, pair in (("-from", "-to"), ("-to", "-from")):
                if name.endswith(have) and allowed.get(name, ("",))[0] in ("from", "to"):
                    other = name[: -len(have)] + pair
                    if other not in names:
                        ctx.err("NAM-07", cpath + ("options",), f"--{name} と --{other} は2つ組で置く")
        for j, option in enumerate(command["options"]):
            opath = cpath + ("options", j)
            name = option["name"]
            if name in vocab.STANDARD_OPTIONS:
                continue
            if name not in allowed:
                hint = ("標準のオプションだけを置く" if verb in ("view", "delete")
                        else "項目名の _ を - に替えた名前（リストは単数形）にする")
                ctx.err("NAM-07", opath + ("name",), f"--{name} は型 {type_['name']} の項目に対応しない（{hint}）")
                continue
            kind, field = allowed[name]
            want = model.option_attributes(verb, kind, field, type_)
            for key in ("type", "values", "repeatable"):
                if option[key] != want[key]:
                    ctx.err("NAM-07", opath + (key,), f"--{name} の {key} を {want[key]!r} にする")
            if kind == "field" and verb == "create" and want["required"]:
                ok = (option["required"] is True and option["default"] is None) or (
                    option["required"] is False and option["default"] is not None)
                if not ok:
                    ctx.err("NAM-07", opath + ("required",), f"--{name} は required を true（default は null）にするか、"
                            "依頼が決めた既定値を default に書いて required を false にする")
            else:
                for key in ("required", "default"):
                    if option[key] != want[key]:
                        ctx.err("NAM-07", opath + (key,), f"--{name} の {key} を {want[key]!r} にする")


# --- CODE-02、CODE-03、CODE-05、OPS-03 値 --------------------------------------

def valid_value(type_: str, value: Any, values: List[str]) -> bool:
    if type_ == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_ == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_ == "boolean":
        return value is False
    if type_ == "enum":
        return value in values
    if type_ == "date":
        return isinstance(value, str) and valid_date(value)
    return isinstance(value, str)


def valid_date(text: str) -> bool:
    if not vocab.DATE.match(text):
        return False
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def check_values(ctx: Ctx, spec: Dict[str, Any]) -> None:
    places = {"arg": vocab.ARG_TYPES, "option": vocab.OPTION_TYPES}
    for cpath, command in each_command(spec):
        if len(command["args"]) > vocab.MAX_ARGS:
            ctx.err("CODE-03", cpath + ("args",), "位置引数は1つ以下にする（2つ目からはオプションにする）")
        if len(command["options"]) > vocab.MAX_OPTIONS:
            ctx.err("CODE-03", cpath + ("options",), f"オプションは {vocab.MAX_OPTIONS} 個以下にする")
    for ppath, _, kind, param in each_param(spec):
        _type_rules(ctx, ppath, param, places[kind], kind)
        if kind == "arg":
            if not param["variadic"] and not param["required"]:
                ctx.err("CODE-02", ppath + ("required",), "variadic が false の位置引数は required を true にする")
            continue
        if param["type"] == "boolean":
            if param["default"] is not False or param["required"] or param["repeatable"]:
                ctx.err("CODE-02", ppath, "boolean のオプションは default を false、required と repeatable を false にする")
        elif (param["required"] or param["repeatable"]) and param["default"] is not None:
            ctx.err("CODE-02", ppath + ("default",), "required か repeatable が true のオプションの default は null にする")
        elif param["default"] is not None and not valid_value(param["type"], param["default"], param["values"]):
            ctx.err("CODE-02", ppath + ("default",), f"default を型 {param['type']} に合う値にする")
        if param["required"] and param["repeatable"]:
            ctx.err("CODE-02", ppath, "required と repeatable を同時に true にしない")
    for fpath, _, field in each_field(spec):
        _type_rules(ctx, fpath, field, vocab.FIELD_TYPES, "field")
    for i, env in enumerate(spec["env"]):
        _type_rules(ctx, ("env", i), env, vocab.ENV_TYPES, "env")
        if env["default"] is not None and not valid_value(env["type"], env["default"], env["values"]):
            ctx.err("CODE-02", ("env", i, "default"), f"default を型 {env['type']} に合う値にする")
    for path, text in _each_string(spec):
        if not all(0x20 <= ord(ch) <= 0x7E for ch in text):
            ctx.err("OPS-03", path, "ASCII の文字だけで書く")


def _type_rules(ctx: Ctx, path: PathT, item: Dict[str, Any], allowed: List[str], kind: str) -> None:
    t = item["type"]
    if t not in allowed:
        ctx.err("CODE-02", path + ("type",), f"{kind} の型は {allowed} のどれかにする")
        return
    if t == "enum" and not item["values"]:
        ctx.err("CODE-02", path + ("values",), "enum は values に選択肢を書く")
    if t != "enum" and item["values"]:
        ctx.err("CODE-02", path + ("values",), "enum 以外の型は values を [] にする")
    if len(set(item["values"])) != len(item["values"]):
        ctx.err("CODE-02", path + ("values",), "選択肢が重複しています")


def _each_string(spec):
    yield ("name",), spec["name"]
    yield ("summary",), spec["summary"]
    for cpath, command in each_command(spec):
        yield cpath + ("summary",), command["summary"]
    for ppath, _, _, param in each_param(spec):
        yield ppath + ("summary",), param["summary"]
        if isinstance(param.get("default"), str):
            yield ppath + ("default",), param["default"]
    for i, env in enumerate(spec["env"]):
        yield ("env", i, "summary"), env["summary"]
        if isinstance(env["default"], str):
            yield ("env", i, "default"), env["default"]


# --- CODE-03、CODE-04、CODE-05 summary --------------------------------------------

def expected_summary(spec: Dict[str, Any], command: Dict[str, Any]) -> Optional[str]:
    if len(command["path"]) != 2:
        return None
    noun, verb = command["path"]
    templates = {"create": f"Create {model.article(noun)} {noun}", "list": f"List {model.plural(noun)}",
                 "view": f"View {model.article(noun)} {noun}", "edit": f"Edit {model.article(noun)} {noun}",
                 "delete": f"Delete {model.article(noun)} {noun}"}
    return templates.get(verb)


def cli_summary(nouns: List[str]) -> str:
    plurals = [model.plural(n) for n in nouns]
    if len(plurals) == 1:
        return f"Manage {plurals[0]}"
    if len(plurals) == 2:
        return f"Manage {plurals[0]} and {plurals[1]}"
    return "Manage " + ", ".join(plurals[:-1]) + f", and {plurals[-1]}"


def check_texts(ctx: Ctx, spec: Dict[str, Any]) -> None:
    for path, text in _each_summary(spec):
        if len(text) > vocab.MAX_SUMMARY:
            ctx.err("CODE-03", path, f"summary は {vocab.MAX_SUMMARY} 文字以下にする（{len(text)} 文字）")
        if not re.match(r"^[A-Z]", text) or text.endswith(".") or text != text.strip() or "  " in text:
            ctx.err("CODE-04", path, "summary は大文字で始め、ピリオドで終えず、前後と連続の空白を入れない")
        lowered = text.lower()
        for word in vocab.SUMMARY_FORBIDDEN:
            if re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", lowered):  # 語の一部（done of）は除く
                ctx.err("CODE-05", path, f"summary に {word!r} を書かない（default・values・required・repeatable で表す）")
                break
    single = model.is_single(spec)
    if single:
        command = spec["commands"][0]
        first = spec["name"].split("-")[0].capitalize()
        if not spec["summary"].startswith(first + " "):
            ctx.err("CODE-04", ("summary",), f"サブコマンドを持たない CLI の summary は {first!r} で始める")
        if command["summary"] != spec["summary"]:
            ctx.err("CODE-04", ("commands", 0, "summary"), "ルートのコマンドの summary は CLI の summary と同じにする")
    elif model.nouns(spec):
        want = cli_summary(model.nouns(spec))
        if spec["summary"] != want:
            ctx.err("CODE-04", ("summary",), f"summary を {want!r} にする")
    types = model.types_by_name(spec)
    for cpath, command in each_command(spec):
        if len(command["path"]) != 2:
            continue
        noun, verb = command["path"]
        want = expected_summary(spec, command)
        if want is not None and command["summary"] != want:
            ctx.err("CODE-04", cpath + ("summary",), f"summary を {want!r} にする")
        if want is None and not command["summary"].startswith(verb.capitalize() + " "):
            ctx.err("CODE-04", cpath + ("summary",), f"summary は {verb.capitalize()!r} で始める")
        type_ = types.get(noun)
        key = model.key_field(type_)
        for j, arg in enumerate(command["args"]):
            if key is not None and arg["name"] == key["name"]:
                want_arg = f"{'ID' if key['name'] == 'id' else 'Name'} of the {noun}"
                if arg["summary"] != want_arg:
                    ctx.err("CODE-04", cpath + ("args", j, "summary"), f"summary を {want_arg!r} にする")
        if type_ is None or verb not in vocab.STANDARD_VERBS:
            continue
        _, allowed = model.option_plan(type_, verb)
        for j, option in enumerate(command["options"]):
            if option["name"] in allowed and option["name"] not in vocab.STANDARD_OPTIONS:
                kind, field = allowed[option["name"]]
                want_opt = model.option_summary(noun, verb, kind, option["name"], field["type"] if field else None,
                                                field["name"] if field else "")
                if option["summary"] != want_opt:
                    ctx.err("CODE-04", cpath + ("options", j, "summary"), f"summary を {want_opt!r} にする")


def _each_summary(spec):
    yield ("summary",), spec["summary"]
    for cpath, command in each_command(spec):
        yield cpath + ("summary",), command["summary"]
    for ppath, _, _, param in each_param(spec):
        yield ppath + ("summary",), param["summary"]
    for i, env in enumerate(spec["env"]):
        yield ("env", i, "summary"), env["summary"]


# --- ERR-01 終了コード ---------------------------------------------------------

def expected_exit_codes(spec: Dict[str, Any], command: Dict[str, Any]) -> List[int]:
    codes = {0, 1, 2}
    verb = command["path"][1] if len(command["path"]) == 2 else None
    key = model.key_field(model.noun_type(spec, command))
    for arg in command["args"]:
        if arg["type"] in ("file", "directory"):
            codes.add(3)
        if key is not None and arg["name"] == key["name"] and verb != "create":
            codes.add(3)
    for option in command["options"]:
        if option["type"] in ("file", "directory") and option["name"] != "output":
            codes.add(3)
    if verb == "create" and key is not None and key["name"] == "name":
        codes.add(4)
    return sorted(codes)


def check_exit_codes(ctx: Ctx, spec: Dict[str, Any]) -> None:
    for cpath, command in each_command(spec):
        unknown = [c for c in command["exit_codes"] if c not in vocab.EXIT_CODES]
        if unknown:
            ctx.err("ERR-01", cpath + ("exit_codes",), f"終了コード {unknown} は使わない（0〜4 だけ）")
            continue
        want = expected_exit_codes(spec, command)
        if sorted(command["exit_codes"]) != want:
            ctx.err("ERR-01", cpath + ("exit_codes",), f"exit_codes を {want} にする")


# --- STATE-01、OPS-02 設定と秘密情報 ------------------------------------------------

def check_settings(ctx: Ctx, spec: Dict[str, Any]) -> None:
    pre = model.prefix(spec["name"])
    data_env = f"{pre}_DATA_DIR"
    if spec["storage"] not in vocab.STORAGE:
        ctx.err("STATE-01", ("storage",), f"storage は {vocab.STORAGE} のどちらかにする")
    envs = {e["name"]: (i, e) for i, e in enumerate(spec["env"])}
    want = {"name": data_env, "type": "directory", "values": [], "default": f"$XDG_DATA_HOME/{spec['name']}",
            "summary": vocab.DATA_DIR_SUMMARY}
    if spec["storage"] == "data":
        if data_env not in envs:
            ctx.err("STATE-01", ("env",), f"storage が data なら env に {want} を書く")
        elif envs[data_env][1] != want:
            ctx.err("STATE-01", ("env", envs[data_env][0]), f"{data_env} を {want} にする")
    elif data_env in envs:
        ctx.err("STATE-01", ("env", envs[data_env][0]), f"storage が data でないなら {data_env} を置かない")
    options = {}
    for _, _, kind, param in each_param(spec):
        if kind == "option":
            options.setdefault(param["name"], param)
    for name, (i, env) in envs.items():
        if name == data_env:
            continue
        option_name = name[len(pre) + 1:].lower().replace("_", "-") if name.startswith(pre + "_") else ""
        option = options.get(option_name)
        if option is None:
            ctx.err("STATE-01", ("env", i, "name"),
                    "環境変数は同じ名前のオプション（<PREFIX>_<オプション名>）の既定値を変えるものだけにする")
            continue
        for key in ("type", "values", "default"):
            if env[key] != option[key]:
                ctx.err("STATE-01", ("env", i, key), f"{key} をオプション --{option_name} と同じにする")
    for ppath, _, kind, param in each_param(spec):
        name = param["name"]
        if any(word in name for word in vocab.SECRET_WORDS):
            if kind == "arg" or not name.endswith("-file") or param["type"] != "file":
                ctx.err("OPS-02", ppath + ("name",), "秘密情報は <名前>-file（file）のオプションでファイルか stdin から読む")
    for i, env in enumerate(spec["env"]):
        upper = [w.upper().replace("-", "_") for w in vocab.SECRET_WORDS]
        if any(word in env["name"] for word in upper):
            ctx.err("OPS-02", ("env", i, "name"), "秘密情報を環境変数で受け取らない")


# --- OPS-06 配布 -----------------------------------------------------------

def check_distribution(ctx: Ctx, spec: Dict[str, Any]) -> None:
    name = spec["name"]
    if name in vocab.WINDOWS_RESERVED or vocab.GO_MAJOR_SUFFIX.match(name):
        ctx.err("OPS-06", ("name",), f"{name!r} は配布できない名前（Windows の予約名、v と数字だけ）")
    if not vocab.VERSION.match(spec["version"]):
        ctx.err("OPS-06", ("version",), "version は数字3つの <MAJOR>.<MINOR>.<PATCH> にする")


# --- STR-04、PROC-06 リリース済みの仕様と版 ---------------------------------------------

def check_released(root: Path, spec_dir: Path, spec: Dict[str, Any], ctx: Ctx, out: List[Finding]) -> None:
    releases = model.released_versions(spec_dir)
    latest: Optional[Tuple[Tuple[int, int, int], Dict[str, Any]]] = None
    for version, path in releases:
        try:
            data = model.load(path)
        except model.SpecError as exc:
            out.append(Finding("STR-04", path.relative_to(root).as_posix(), 1, "(root)", str(exc)))
            continue
        rctx = Ctx(root, path, data, out)
        if not shape(rctx, data, "spec", ()):
            continue
        if data["name"] != spec["name"] or data["version"] != path.stem:
            rctx.err("STR-04", ("version",), "リリース済みの仕様の name と version がファイル名と合いません")
        if path.read_text(encoding="utf-8") != canon.dumps(model.canonical(data)):
            rctx.err("STR-04", (), "リリース済みの仕様が正規の形ではありません（make release で作る）")
        latest = (version, data)
    if not vocab.VERSION.match(spec["version"]):
        return
    if latest is None:
        if spec["version"] != "1.0.0":
            ctx.err("PROC-06", ("version",), "リリース済みの仕様が無い間は version を \"1.0.0\" にする")
        return
    d = compat.diff(latest[1], spec)
    want = compat.text(compat.bump(latest[0], d.level))
    if spec["version"] != want:
        reason = d.first(d.level) if d.level != "none" else "リリース済みの最新版と差分が無い"
        ctx.err("PROC-06", ("version",),
                f"version を {want!r} にする（リリース済み {compat.text(latest[0])} から {d.level}: {reason}）")
