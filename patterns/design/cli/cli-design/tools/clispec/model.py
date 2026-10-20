"""仕様（cli.json）の読み方：キーの順、並べ替え、仕様から導く値。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import vocab

SPECS_DIR = "specs"
SPEC_FILE = "cli.json"
DOC_FILE = "cli.md"
RELEASED_DIR = "released"

# CODE-01 キーの順
KEYS = {
    "spec": ["name", "version", "summary", "storage", "commands", "types", "env"],
    "command": ["path", "summary", "args", "options", "output", "exit_codes"],
    "arg": ["name", "type", "values", "required", "variadic", "summary"],
    "option": ["name", "type", "values", "default", "required", "repeatable", "summary"],
    "output": ["kind", "type"],
    "type": ["name", "fields"],
    "field": ["name", "type", "values", "list", "nullable"],
    "env": ["name", "type", "values", "default", "summary"],
}
CHILDREN = {"commands": "command", "args": "arg", "options": "option", "types": "type", "fields": "field", "env": "env"}


class SpecError(Exception):
    """仕様を JSON として読めない。"""


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SpecError(f"{path}: JSON として読めません: {exc}") from exc


# --- 正規の形（TOOL-01、CODE-01） ---------------------------------------------

def canonical(spec: Any) -> Any:
    """キーを表の順に、配列を表の並びにした写しを返す。表に無いキーは消さずに後ろへ置く。"""
    return _order(spec, "spec")


def _order(obj: Any, kind: str) -> Any:
    if not isinstance(obj, dict):
        return obj
    known = [k for k in KEYS[kind] if k in obj]
    rest = [k for k in obj if k not in KEYS[kind]]
    result = {}
    for key in known + rest:
        value = obj[key]
        if key in CHILDREN and isinstance(value, list) and kind in ("spec", "command", "type"):
            value = [_order(item, CHILDREN[key]) for item in value]
            value = _sort_children(key, value)
        elif key == "output" and kind == "command":
            value = _order(value, "output")
        elif key == "values" and _all_str(value):
            value = sorted(value)
        elif key == "exit_codes" and isinstance(value, list) and all(isinstance(v, int) for v in value):
            value = sorted(value)
        result[key] = value
    return result


def _all_str(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def _sort_children(key: str, items: List[Any]) -> List[Any]:
    if not all(isinstance(i, dict) for i in items):
        return items
    if key == "commands":
        if all(_all_str(i.get("path")) for i in items):
            return sorted(items, key=lambda i: i["path"])
        return items
    if key in ("options", "types", "env"):
        if all(isinstance(i.get("name"), str) for i in items):
            return sorted(items, key=lambda i: i["name"])
        return items
    if key == "fields":
        if all(isinstance(i.get("name"), str) for i in items):
            names = [i["name"] for i in items]
            first = "id" if "id" in names else ("name" if "name" in names else None)
            return sorted(items, key=lambda i: (i["name"] != first, i["name"]))
        return items
    return items


# --- 仕様から導く値 ---------------------------------------------------------

def prefix(name: str) -> str:
    """環境変数の接頭辞（count-words → COUNT_WORDS）。"""
    return name.upper().replace("-", "_")


def plural(noun: str) -> str:
    if noun.endswith(("s", "x", "z", "ch", "sh")):
        return noun + "es"
    if len(noun) > 1 and noun.endswith("y") and noun[-2] not in "aeiou":
        return noun[:-1] + "ies"
    return noun + "s"


def singular_of(word: str) -> Optional[str]:
    """plural(x) == word となる x（無ければ None）。"""
    candidates = []
    if word.endswith("ies"):
        candidates.append(word[:-3] + "y")
    if word.endswith("es"):
        candidates.append(word[:-2])
    if word.endswith("s"):
        candidates.append(word[:-1])
    for cand in candidates:
        if cand and plural(cand) == word:
            return cand
    return None


def article(noun: str) -> str:
    return "an" if noun[:1] in "aeiou" else "a"


def is_single(spec: Dict[str, Any]) -> bool:
    commands = spec.get("commands", [])
    return len(commands) == 1 and commands[0].get("path") == []


def nouns(spec: Dict[str, Any]) -> List[str]:
    return sorted({c["path"][0] for c in spec.get("commands", []) if len(c.get("path", [])) == 2})


def verbs_of(spec: Dict[str, Any], noun: str) -> List[str]:
    return [c["path"][1] for c in spec.get("commands", []) if len(c.get("path", [])) == 2 and c["path"][0] == noun]


def types_by_name(spec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {t["name"]: t for t in spec.get("types", []) if isinstance(t, dict) and isinstance(t.get("name"), str)}


def key_field(type_: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """識別子の項目（先頭の id か name）。"""
    if not type_ or not type_.get("fields"):
        return None
    first = type_["fields"][0]
    return first if first.get("name") in vocab.KEY_FIELDS else None


def noun_type(spec: Dict[str, Any], command: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    path = command.get("path", [])
    if len(path) != 2:
        return None
    return types_by_name(spec).get(path[0])


def program(spec: Dict[str, Any], command: Optional[Dict[str, Any]]) -> str:
    """ヘルプの Usage に書く呼び出し方（notes note create）。command が None ならルート。"""
    if command is None or not command.get("path"):
        return spec["name"]
    return " ".join([spec["name"]] + command["path"])


def implicit_options(spec: Dict[str, Any], command: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """暗黙のオプション。command が None なら、サブコマンドを持つ CLI のルート。"""
    root = command is None or command.get("path") == []
    result = [_implicit("help", "Show help")]
    if root:
        result.append(_implicit("version", "Show the version"))
    if command is not None and command.get("output", {}).get("kind") in ("object", "list"):
        result.append(_implicit("json", "Write the output as JSON"))
    return result


def _implicit(name: str, summary: str) -> Dict[str, Any]:
    return {"name": name, "type": "boolean", "values": [], "default": False, "required": False,
            "repeatable": False, "summary": summary}


# --- NAM-07 項目から作るオプション -------------------------------------------------

SYSTEM_FIELDS = ("created_at", "updated_at")
RANGE_TYPES = ("date", "integer", "number")


def settable_fields(type_: Dict[str, Any]) -> List[Dict[str, Any]]:
    """create・edit がオプションで受け取る項目（識別子・created_at・updated_at を除く）。"""
    key = key_field(type_)
    return [f for f in type_.get("fields", []) if f is not key and f.get("name") not in SYSTEM_FIELDS]


def field_option_name(field: Dict[str, Any]) -> str:
    base = field["name"]
    if field.get("list"):
        base = singular_of(base) or base
    return base.replace("_", "-")


def sort_values(type_: Dict[str, Any]) -> List[str]:
    return sorted(f["name"] for f in type_.get("fields", []) if not f.get("list"))


def option_plan(type_: Dict[str, Any], verb: str) -> Tuple[List[str], Dict[str, Tuple[str, Optional[Dict[str, Any]]]]]:
    """標準の動詞に置くオプション。(必ず置く名前, 名前 → (種類, 項目))。種類は field・file・clear・filter・from・to・limit・sort。"""
    required: List[str] = []
    allowed: Dict[str, Tuple[str, Optional[Dict[str, Any]]]] = {}
    if verb in ("create", "edit"):
        for f in settable_fields(type_):
            name = field_option_name(f)
            required.append(name)
            allowed[name] = ("field", f)
            allowed[name + "-file"] = ("file", f)
            if verb == "edit" and (f.get("nullable") or f.get("list") or f["type"] == "boolean"):
                clear = "clear-" + f["name"].replace("_", "-")
                required.append(clear)
                allowed[clear] = ("clear", f)
    elif verb == "list":
        required += ["limit", "sort"]
        allowed["limit"] = ("limit", None)
        allowed["sort"] = ("sort", None)
        for f in type_.get("fields", []):
            allowed.setdefault(field_option_name(f), ("filter", f))
            if f["type"] in RANGE_TYPES and not f.get("list"):
                allowed.setdefault(field_option_name(f) + "-from", ("from", f))
                allowed.setdefault(field_option_name(f) + "-to", ("to", f))
    return required, allowed


def option_attributes(verb: str, kind: str, field: Optional[Dict[str, Any]], type_: Dict[str, Any]) -> Dict[str, Any]:
    """NAM-07 の決定表の値（type・values・required・default・repeatable）。create の必須の項目は required を true にする。"""
    if kind == "limit":
        return {"type": "integer", "values": [], "required": False, "default": vocab.LIST_LIMIT_DEFAULT, "repeatable": False}
    if kind == "sort":
        key = key_field(type_)
        return {"type": "enum", "values": sort_values(type_), "required": False,
                "default": key["name"] if key else None, "repeatable": False}
    if kind == "file":
        return {"type": "file", "values": [], "required": False, "default": None, "repeatable": False}
    if kind == "clear":
        return {"type": "boolean", "values": [], "required": False, "default": False, "repeatable": False}
    attrs = {"type": field["type"], "values": list(field.get("values", [])), "required": False, "default": None,
             "repeatable": False}
    if field["type"] == "boolean":
        attrs["default"] = False
    elif field.get("list"):
        attrs["repeatable"] = True
    elif not field.get("nullable") and verb == "create":
        attrs["required"] = True
    return attrs


def acronyms(text: str) -> str:
    return " ".join(vocab.ACRONYMS.get(word, word) for word in text.split(" "))


def option_summary(noun: str, verb: str, kind: str, name: str, field_type: Optional[str] = None,
                   field_name: str = "") -> str:
    """CODE-04 項目から作るオプションの summary。"""
    nouns = plural(noun)
    suffix = {"file": "-file", "from": "-from", "to": "-to"}.get(kind, "")
    label = acronyms(name[: len(name) - len(suffix)].replace("-", " "))
    field_label = acronyms(field_name.replace("_", " "))
    if kind == "clear":
        return f"Clear the {field_label} of the {noun}"
    if kind in ("from", "to"):
        bound = {("from", True): "on or after", ("to", True): "on or before",
                 ("from", False): "of at least", ("to", False): "of at most"}[(kind, field_type == "date")]
        return f"Show only {nouns} with {label} {bound} this"
    if kind == "limit":
        return f"Maximum number of {nouns} to show"
    if kind == "sort":
        return f"Field to sort the {nouns} by"
    if kind == "file":
        return f"File to read the {label} of the {noun} from"
    if kind == "filter":
        return f"Show only {nouns} with this {label}"
    if verb == "edit":
        return f"New {label} of the {noun}"
    return f"{label[:1].upper()}{label[1:]} of the {noun}"


def make_option(noun: str, verb: str, name: str, kind: str, field: Optional[Dict[str, Any]],
                type_: Dict[str, Any]) -> Dict[str, Any]:
    attrs = option_attributes(verb, kind, field, type_)
    return {"name": name, "type": attrs["type"], "values": attrs["values"], "default": attrs["default"],
            "required": attrs["required"], "repeatable": attrs["repeatable"],
            "summary": option_summary(noun, verb, kind, name, field["type"] if field else None,
                                      field["name"] if field else "")}


def short_name(option_name: str) -> Optional[str]:
    if option_name == "help":
        return "h"
    entry = vocab.STANDARD_OPTIONS.get(option_name)
    return entry[0] if entry else None


def metavar(option_name: str) -> str:
    return option_name.upper().replace("-", "_")


def iter_spec_dirs(root: Path, targets: List[str]) -> List[Path]:
    """引数（specs、specs/<name>、specs/<name>/cli.json）を仕様のディレクトリの一覧にする。"""
    result: List[Path] = []
    for target in targets or [SPECS_DIR]:
        path = (root / target).resolve()
        if path.is_file():
            path = path.parent
        if path.name == RELEASED_DIR:
            path = path.parent
        if path == (root / SPECS_DIR).resolve():
            result += sorted(p for p in path.iterdir() if p.is_dir())
        elif path.is_dir():
            result.append(path)
    seen, unique = set(), []
    for p in result:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def released_versions(spec_dir: Path) -> List[Tuple[Tuple[int, int, int], Path]]:
    released = spec_dir / RELEASED_DIR
    if not released.is_dir():
        return []
    items = []
    for path in released.iterdir():
        match = vocab.VERSION.match(path.stem) if path.suffix == ".json" else None
        if match:
            items.append(((int(match.group(1)), int(match.group(2)), int(match.group(3))), path))
    return sorted(items)
