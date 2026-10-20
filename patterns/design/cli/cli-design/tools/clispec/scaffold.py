"""生成器（STR-02）。新しい CLI、コマンド、項目を、ルールが決める値で作る。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import canon
import model
import vocab

TODO = "TODO"


def new_spec(name: str, single: bool) -> Dict[str, Any]:
    spec: Dict[str, Any] = {"name": name, "version": "1.0.0", "summary": TODO, "storage": "none",
                            "commands": [], "types": [], "env": []}
    if single:
        spec["commands"].append({"path": [], "summary": TODO, "args": [], "options": [],
                                 "output": {"kind": "none", "type": None}, "exit_codes": [0, 1, 2]})
    return spec


def add_command(spec: Dict[str, Any], noun: str, verb: str, key: str) -> Optional[str]:
    """コマンドを足す。足せなければ理由を返す。"""
    if model.is_single(spec):
        return "サブコマンドを持たない CLI にはコマンドを足せない（STR-05。足すなら操作が2つ以上の設計に作り直す）"
    if any(c["path"] == [noun, verb] for c in spec["commands"]):
        return f"{noun} {verb} は既にある"
    if verb in vocab.FORBIDDEN_VERBS:
        return f"動詞 {verb!r} ではなく {vocab.FORBIDDEN_VERBS[verb]!r} を使う（NAM-04）"
    command: Dict[str, Any] = {"path": [noun, verb], "summary": f"{verb.capitalize()} {TODO}", "args": [],
                               "options": [], "output": {"kind": "none", "type": None}, "exit_codes": [0, 1, 2]}
    spec["commands"].append(command)
    if verb in vocab.STANDARD_VERBS:
        type_ = model.types_by_name(spec).get(noun)
        if type_ is None:
            type_ = {"name": noun, "fields": [_field(key, vocab.KEY_FIELDS[key])]}
            spec["types"].append(type_)
        if verb in ("create", "edit", "delete"):
            _ensure_storage(spec)
        key_name = model.key_field(type_)["name"] if model.key_field(type_) else key
        arg_rule, kind, _ = vocab.STANDARD_VERBS[verb]
        command["output"] = {"kind": kind, "type": noun}
        command["summary"] = _summary(noun, verb)
        if arg_rule == "key" or (arg_rule == "create" and key_name == "name"):
            label = "ID" if key_name == "id" else "Name"
            command["args"] = [_arg(key_name, vocab.KEY_FIELDS[key_name], f"{label} of the {noun}")]
        command["exit_codes"] = _exit_codes(verb, key_name)
        sync_noun(spec, noun)
    spec["summary"] = _cli_summary(spec)
    return None


def add_field(spec: Dict[str, Any], noun: str, name: str, type_name: str, is_list: bool, nullable: bool,
              values: List[str]) -> Optional[str]:
    """名詞の型に項目を足し、create・edit・list のオプションを合わせる。足せなければ理由を返す。"""
    type_ = model.types_by_name(spec).get(noun)
    if type_ is None:
        return f"型 {noun!r} がありません（先に make command で {noun} の標準の動詞を足す）"
    if any(f["name"] == name for f in type_["fields"]):
        return f"項目 {name!r} は既にある"
    if type_name not in vocab.FIELD_TYPES:
        return f"項目の型は {vocab.FIELD_TYPES} のどれかにする（CODE-02）"
    if (type_name == "enum") != bool(values):
        return "enum の項目には VALUES を書き、enum 以外には書かない（CODE-02）"
    type_["fields"].append({"name": name, "type": type_name, "values": sorted(values), "list": is_list,
                            "nullable": nullable})
    sync_noun(spec, noun)
    return None


def sync_noun(spec: Dict[str, Any], noun: str) -> None:
    """NAM-07 の必ず置くオプションのうち、無いものを足し、list の --sort の選択肢を項目に合わせる。"""
    type_ = model.types_by_name(spec)[noun]
    verbs = set(model.verbs_of(spec, noun))
    names = [f["name"] for f in type_["fields"]]
    if "create" in verbs and "created_at" not in names:
        type_["fields"].append(_field("created_at", "timestamp"))
    if "edit" in verbs and "updated_at" not in names:
        type_["fields"].append(_field("updated_at", "timestamp"))
    for command in spec["commands"]:
        if command["path"][:1] != [noun] or command["path"][1] not in vocab.STANDARD_VERBS:
            continue
        verb = command["path"][1]
        required, allowed = model.option_plan(type_, verb)
        existing = {o["name"]: o for o in command["options"]}
        for name in required:
            kind, field = allowed[name]
            if name not in existing:
                command["options"].append(model.make_option(noun, verb, name, kind, field, type_))
            elif kind == "sort":
                existing[name]["values"] = model.sort_values(type_)


def _exit_codes(verb: str, key_name: str) -> List[int]:
    if vocab.STANDARD_VERBS[verb][0] == "key":
        return [0, 1, 2, 3]
    if verb == "create" and key_name == "name":
        return [0, 1, 2, 4]
    return [0, 1, 2]


def _summary(noun: str, verb: str) -> str:
    art = model.article(noun)
    return {"create": f"Create {art} {noun}", "list": f"List {model.plural(noun)}", "view": f"View {art} {noun}",
            "edit": f"Edit {art} {noun}", "delete": f"Delete {art} {noun}"}[verb]


def _cli_summary(spec: Dict[str, Any]) -> str:
    plurals = [model.plural(n) for n in model.nouns(spec)]
    if len(plurals) == 1:
        return f"Manage {plurals[0]}"
    if len(plurals) == 2:
        return f"Manage {plurals[0]} and {plurals[1]}"
    return "Manage " + ", ".join(plurals[:-1]) + f", and {plurals[-1]}"


def _ensure_storage(spec: Dict[str, Any]) -> None:
    """STATE-01 データを書き換える動詞があれば、データの置き場を持たせる。"""
    spec["storage"] = "data"
    env_name = f"{model.prefix(spec['name'])}_DATA_DIR"
    if not any(e["name"] == env_name for e in spec["env"]):
        spec["env"].append({"name": env_name, "type": "directory", "values": [],
                            "default": f"$XDG_DATA_HOME/{spec['name']}", "summary": vocab.DATA_DIR_SUMMARY})


def _field(name: str, type_: str) -> Dict[str, Any]:
    return {"name": name, "type": type_, "values": [], "list": False, "nullable": False}


def _arg(name: str, type_: str, summary: str) -> Dict[str, Any]:
    return {"name": name, "type": type_, "values": [], "required": True, "variadic": False, "summary": summary}


def write(path: Path, spec: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canon.dumps(model.canonical(spec)), encoding="utf-8")
