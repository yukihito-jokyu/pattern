"""キット自身の構造の検査（KIT-01、KIT-02、KIT-05、KIT-06）。標準ライブラリだけを使う。

指摘は `<ルールID> <パス>:<行> <説明>` の形で出し、1件でもあれば終了コード 1 を返す。
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / ".gha" / "gha_kit"
REPORT = ROOT / ".github" / "actions" / "run-report"
TESTS = ROOT / "tests"
STDLIB = sys.stdlib_module_names

# architecture.md の 3.1 の表。モジュール → import してよい gha_kit のモジュール
RULE_MODULES = {"findings", "layout", "walk", "yamlnode"}
ALLOWED: dict[str, set[str]] = {
    "__init__": set(),
    "errors": set(),
    "layout": set(),
    "findings": set(),
    "rulemap": set(),
    "proc": {"errors"},
    "yamlnode": set(),
    "targets": {"layout"},
    "pins": set(),
    "gitref": {"errors", "proc"},
    "walk": {"findings", "layout", "targets", "yamlnode"},
    "intent": {"yamlnode"},
    "tools": {"errors", "findings", "layout", "proc", "rulemap"},
    "rules_str": RULE_MODULES,
    "rules_dep": RULE_MODULES,
    "rules_nam": RULE_MODULES,
    "rules_code": RULE_MODULES,
    "rules_flow": RULE_MODULES,
    "rules_ops": RULE_MODULES,
    "policy": {
        "findings",
        "targets",
        "walk",
        "yamlnode",
        *(f"rules_{part}" for part in ("str", "dep", "nam", "code", "flow", "ops")),
    },
    "checks": {"findings", "layout", "policy", "proc", "targets", "tools", "yamlnode"},
    "ratchet": {"checks", "findings", "gitref", "layout", "proc"},
    "cli": {"checks", "errors", "findings", "gitref", "intent", "pins", "proc", "ratchet", "targets", "yamlnode"},
}
THIRD_PARTY = {"yamlnode": {"yaml"}}
STDLIB_ONLY_IN = {"subprocess": {"proc"}}
FORBIDDEN_STDLIB = {"urllib", "http"}
NO_TESTS = {"__init__", "errors", "layout", "policy", "walk"}
TEST_NAME = re.compile(r"^test_[a-z0-9]+(_[a-z0-9]+)*$")
PYYAML = re.compile(r"(?<![\w-])pyyaml==([0-9.]+)", re.IGNORECASE)


def main() -> int:
    problems = [*check_layout(), *check_imports(), *check_tests(), *check_versions()]
    for problem in problems:
        print(problem)
    print(f"structure: 指摘 {len(problems)} 件")
    return 1 if problems else 0


def check_layout() -> Iterator[str]:
    """KIT-01: gha_kit はサブディレクトリを持たず、run-report は2ファイル、tests は決まった名前だけ。"""
    for path in sorted(KIT.iterdir()):
        if path.is_dir() and path.name != "__pycache__":
            yield _problem("KIT-01", path, 1, "gha_kit にサブディレクトリを作らない（モジュールは gha_kit/<名前>.py）")
        if path.is_file() and path.suffix != ".py":
            yield _problem("KIT-01", path, 1, "gha_kit には Python のモジュールだけを置く")
    for path in sorted(REPORT.iterdir()):
        if path.name not in ("action.yml", "run_report.py", "__pycache__"):
            yield _problem("KIT-01", path, 1, "run-report は action.yml と run_report.py の2ファイルにする")
    for path in sorted(TESTS.glob("*.py")):
        if path.name not in ("__init__.py", "support.py") and not path.name.startswith("test_"):
            yield _problem("KIT-01", path, 1, "tests の Python は test_<モジュール名>.py と support.py だけにする")
    for path in sorted(TESTS.rglob("*.py")):
        if path.parent != TESTS:
            yield _problem(
                "KIT-01", path, 1, "テストのデータは tests/fixtures/<題材>/ に YAML で置く（Python を置かない）"
            )


def check_imports() -> Iterator[str]:
    """KIT-02: architecture.md の依存の許可表と、外部の依存の制限。"""
    for path in sorted(KIT.glob("*.py")):
        module = path.stem
        if module not in ALLOWED:
            yield _problem("KIT-02", path, 1, f"{module} を architecture.md の依存の許可表と ALLOWED に足す")
            continue
        for line, name in _imports(path):
            yield from _check_kit_import(path, module, line, name)
    for path in [REPORT / "run_report.py", ROOT / "install.py", *sorted((ROOT / "scripts").glob("*.py"))]:
        for line, name in _imports(path):
            if name.split(".")[0] not in STDLIB:
                yield _problem("KIT-02", path, line, f"{name} を import しない（標準ライブラリだけを使う）")
    for line, name in _imports(ROOT / ".gha" / "gha.py"):
        if name not in ("sys", "gha_kit.cli"):
            yield _problem("KIT-02", ROOT / ".gha" / "gha.py", line, "gha.py は gha_kit.cli だけを import する")


def _check_kit_import(path: Path, module: str, line: int, name: str) -> Iterator[str]:
    top = name.split(".", maxsplit=1)[0]
    if top == "gha_kit":
        target = name.split(".")[1] if "." in name else ""
        if target not in ALLOWED[module]:
            yield _problem(
                "KIT-02", path, line, f"{module} から {target or name} を import しない（architecture.md の 3.1）"
            )
    elif top in STDLIB_ONLY_IN and module not in STDLIB_ONLY_IN[top]:
        yield _problem("KIT-02", path, line, f"{top} は {', '.join(sorted(STDLIB_ONLY_IN[top]))} だけで使う")
    elif top in FORBIDDEN_STDLIB:
        yield _problem("KIT-02", path, line, f"{top} を gha_kit で使わない（ネットワークは git ls-remote だけ）")
    elif top not in STDLIB and top not in THIRD_PARTY.get(module, set()) and top != "__future__":
        yield _problem(
            "KIT-02", path, line, f"{top} を import しない（gha_kit の外部の依存は yamlnode の PyYAML だけ）"
        )


def _imports(path: Path) -> Iterator[tuple[int, str]]:
    """import 文の (行, モジュール名)。`from gha_kit import a, b` は gha_kit.a と gha_kit.b に分ける。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "gha_kit":
                for alias in node.names:
                    yield node.lineno, f"gha_kit.{alias.name}"
            else:
                yield node.lineno, node.module


def check_tests() -> Iterator[str]:
    """KIT-05: テストを置くモジュールと置かないモジュール、テストの名前。"""
    modules = {path.stem for path in KIT.glob("*.py")} | {"run_report", "install"}
    needs_test = {name for name in modules if name not in NO_TESTS and not name.startswith("rules_")}
    tests = {path.stem.removeprefix("test_"): path for path in TESTS.glob("test_*.py")}
    for name in sorted(needs_test - tests.keys()):
        yield _problem("KIT-05", TESTS / f"test_{name}.py", 1, f"{name} のテストを tests/test_{name}.py に置く")
    for name, path in sorted(tests.items()):
        if name not in needs_test:
            yield _problem("KIT-05", path, 1, f"{name} は KIT-05 の表でテストを置かないモジュール（または存在しない）")
        yield from _test_names(path)


def _test_names(path: Path) -> Iterator[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test") and not TEST_NAME.match(node.name):
            yield _problem("KIT-05", path, node.lineno, f"テストの名前 {node.name} を test_<英語の snake_case> にする")


def check_versions() -> Iterator[str]:
    """KIT-06: PyYAML の版を pyproject.toml と .gha/gha.py で同じにする。"""
    script = PYYAML.findall((ROOT / ".gha" / "gha.py").read_text(encoding="utf-8"))
    project = PYYAML.findall((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if len(script) != 1 or script != project:
        yield _problem(
            "KIT-06", ROOT / ".gha" / "gha.py", 1, f"PyYAML の版を pyproject.toml（{project}）と同じにする（{script}）"
        )


def _problem(rule: str, path: Path, line: int, message: str) -> str:
    return f"{rule} {path.relative_to(ROOT).as_posix()}:{line} {message}"


if __name__ == "__main__":
    sys.exit(main())
