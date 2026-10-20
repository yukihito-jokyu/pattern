"""リリース済みの仕様との差分を分類し、期待する版を計算する（PROC-06）。"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

LEVELS = ["none", "patch", "minor", "major"]


class Diff:
    def __init__(self) -> None:
        self.changes: List[Tuple[str, str]] = []  # (level, 説明)

    def add(self, level: str, text: str) -> None:
        self.changes.append((level, text))

    @property
    def level(self) -> str:
        return max((c[0] for c in self.changes), key=LEVELS.index, default="none")

    def first(self, level: str) -> str:
        return next((text for lv, text in self.changes if lv == level), "")


def diff(old: Dict[str, Any], new: Dict[str, Any]) -> Diff:
    d = Diff()
    if old.get("name") != new.get("name"):
        d.add("major", f"name を {old.get('name')} から {new.get('name')} に変えた")
    if old.get("storage") != new.get("storage"):
        d.add("major", "storage を変えた")
    if old.get("summary") != new.get("summary"):
        d.add("patch", "CLI の summary を変えた")
    _by_name(d, "コマンド", _keyed(old.get("commands", []), "path"), _keyed(new.get("commands", []), "path"), _command)
    _by_name(d, "型", _keyed(old.get("types", [])), _keyed(new.get("types", [])), _type)
    _by_name(d, "環境変数", _keyed(old.get("env", [])), _keyed(new.get("env", [])), _env)
    return d


def _keyed(items: List[Dict[str, Any]], key: str = "name") -> Dict[str, Dict[str, Any]]:
    result = {}
    for item in items:
        value = item.get(key)
        result[" ".join(value) if isinstance(value, list) else str(value)] = item
    return result


def _by_name(d: Diff, label: str, old: Dict[str, Any], new: Dict[str, Any], compare, added_level=None) -> None:
    for name in old:
        if name not in new:
            d.add("major", f"{label} {name!r} を消した")
    for name in new:
        if name not in old:
            level = added_level(new[name]) if added_level else "minor"
            d.add(level, f"{label} {name!r} を足した")
        else:
            compare(d, f"{label} {name!r}", old[name], new[name])


def _summary(d: Diff, where: str, old: Dict[str, Any], new: Dict[str, Any]) -> None:
    if old.get("summary") != new.get("summary"):
        d.add("patch", f"{where} の summary を変えた")


def _values(d: Diff, where: str, old: Dict[str, Any], new: Dict[str, Any]) -> None:
    before, after = set(old.get("values", [])), set(new.get("values", []))
    if before - after:
        d.add("major", f"{where} の values から {sorted(before - after)} を消した")
    if after - before:
        d.add("minor", f"{where} の values に {sorted(after - before)} を足した")


def _fixed(d: Diff, where: str, old: Dict[str, Any], new: Dict[str, Any], keys: List[str]) -> None:
    for key in keys:
        if old.get(key) != new.get(key):
            d.add("major", f"{where} の {key} を {old.get(key)!r} から {new.get(key)!r} に変えた")


def _required_added(item: Dict[str, Any]) -> str:
    return "major" if item.get("required") else "minor"


def _command(d: Diff, where: str, old: Dict[str, Any], new: Dict[str, Any]) -> None:
    _summary(d, where, old, new)
    _fixed(d, where, old, new, ["output", "exit_codes"])
    _by_name(d, f"{where} の位置引数", _keyed(old.get("args", [])), _keyed(new.get("args", [])), _arg, _required_added)
    _by_name(d, f"{where} のオプション", _keyed(old.get("options", [])), _keyed(new.get("options", [])), _option,
             _required_added)


def _arg(d: Diff, where: str, old: Dict[str, Any], new: Dict[str, Any]) -> None:
    _summary(d, where, old, new)
    _fixed(d, where, old, new, ["type", "required", "variadic"])
    _values(d, where, old, new)


def _option(d: Diff, where: str, old: Dict[str, Any], new: Dict[str, Any]) -> None:
    _summary(d, where, old, new)
    _fixed(d, where, old, new, ["type", "default", "required", "repeatable"])
    _values(d, where, old, new)


def _type(d: Diff, where: str, old: Dict[str, Any], new: Dict[str, Any]) -> None:
    _by_name(d, f"{where} の項目", _keyed(old.get("fields", [])), _keyed(new.get("fields", [])), _field)


def _field(d: Diff, where: str, old: Dict[str, Any], new: Dict[str, Any]) -> None:
    _fixed(d, where, old, new, ["type", "list", "nullable"])
    _values(d, where, old, new)


def _env(d: Diff, where: str, old: Dict[str, Any], new: Dict[str, Any]) -> None:
    _summary(d, where, old, new)
    _fixed(d, where, old, new, ["type", "default"])
    _values(d, where, old, new)


def bump(version: Tuple[int, int, int], level: str) -> Tuple[int, int, int]:
    major, minor, patch = version
    if level == "major":
        return (major + 1, 0, 0)
    if level == "minor":
        return (major, minor + 1, 0)
    if level == "patch":
        return (major, minor, patch + 1)
    return version


def text(version: Tuple[int, int, int]) -> str:
    return ".".join(str(v) for v in version)
