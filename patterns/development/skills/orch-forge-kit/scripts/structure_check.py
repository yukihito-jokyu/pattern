"""構造検査。ルール（docs/design/rules.md）のうち、ファイルの置き場・import・字面で判定できるものを確かめる。

違反は `<ルールID> <パス>:<行> <説明>` の形で出し、1件でもあれば終了コード1で終わる。
表（SHARED・STAGES・ENTRY）は docs/design/architecture.md の許可表と1対1で対応させる。片方を変えたら、もう片方も変える。
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from forge_kit import bundle, contracts, layout

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "kit"
FORGE = KIT / ".forge"
PACKAGE = FORGE / "forge_kit"
TESTS = ROOT / "tests"
CACHE = "__pycache__"

# DEP-01: モジュールごとに import してよい forge_kit のモジュール。表に無いモジュールは STR-02 で落ちる
SHARED = {
    "__init__": set(),
    "errors": set(),
    "layout": {"errors"},
    "catalog": set(),
    "metrics": set(),
    "render": set(),
    "shape": set(),
    "charter": {"catalog", "shape", "errors"},
    "design": {"bundle", "shape", "errors"},
    "trace": {"render"},
    "contracts": {"shape", "errors"},
    "fsops": {"errors"},
    "proc": {"errors"},
    "prompts": {"fsops", "errors"},
    "bundle": {"fsops", "layout", "errors"},
    "views": {"charter", "design", "render"},
    "workspace": {"charter", "contracts", "design", "fsops", "layout", "trace", "errors"},
}
STAGES = {
    "goals": {"catalog", "charter", "fsops", "layout", "render", "views", "workspace", "errors"},
    "status": {"bundle", "charter", "contracts", "layout", "render", "workspace", "errors"},
    "designing": {
        "charter",
        "contracts",
        "design",
        "fsops",
        "layout",
        "prompts",
        "render",
        "views",
        "workspace",
        "errors",
    },
    "building": {
        "bundle",
        "charter",
        "contracts",
        "design",
        "fsops",
        "layout",
        "prompts",
        "render",
        "views",
        "workspace",
        "errors",
    },
    "prepare": {"bundle", "charter", "contracts", "fsops", "layout", "proc", "prompts", "workspace", "errors"},
    "execute": {"charter", "contracts", "fsops", "layout", "proc", "workspace", "errors"},
    "collect": {
        "bundle",
        "charter",
        "contracts",
        "fsops",
        "layout",
        "proc",
        "prompts",
        "render",
        "trace",
        "workspace",
        "errors",
    },
    "score": {"catalog", "charter", "contracts", "fsops", "layout", "metrics", "render", "workspace", "errors"},
    "analyze": {
        "bundle",
        "charter",
        "contracts",
        "fsops",
        "layout",
        "prompts",
        "render",
        "views",
        "workspace",
        "errors",
    },
    "compare": {"contracts", "fsops", "layout", "metrics", "render", "workspace", "errors"},
    "decide": {"bundle", "contracts", "fsops", "layout", "workspace", "errors"},
    "report": {"charter", "contracts", "fsops", "layout", "render", "workspace", "errors"},
}
ENTRY = {"cli": {*STAGES, "layout", "proc", "errors"}}
ALLOWED_IMPORTS = {**SHARED, **STAGES, **ENTRY}

# DEP-03: 使ってよい標準ライブラリ。足すときはこの表と research.md を一緒に変える
STDLIB = {
    "__future__",
    "argparse",
    "ast",
    "collections",
    "concurrent",
    "contextlib",
    "dataclasses",
    "datetime",
    "difflib",
    "filecmp",
    "fnmatch",
    "hashlib",
    "io",
    "itertools",
    "json",
    "os",
    "pathlib",
    "re",
    "shutil",
    "signal",
    "subprocess",
    "sys",
    "tempfile",
    "typing",
    "unittest",
}
LOCAL = {"forge_kit", "tests", "install"}

# DEP-04・ASYNC-01・OPS-01・OPS-02: 副作用に触れてよいモジュール
FS_WRITERS = {"write_text", "write_bytes", "mkdir", "unlink", "rmdir", "rename", "symlink_to", "touch", "chmod"}
ONLY_IN = {
    "subprocess": {"proc"},
    "signal": {"proc"},
    "tempfile": {"proc"},
    "shutil": {"fsops", "proc"},
    "datetime": {"cli"},
    "time": {"cli"},
    "threading": {"proc"},
    "asyncio": {"proc"},
    "multiprocessing": {"proc"},
    "concurrent": {"proc"},
}
IMPORT_RULES = {
    "subprocess": "DEP-04",
    "signal": "DEP-04",
    "tempfile": "DEP-04",
    "shutil": "DEP-04",
    "datetime": "DEP-04",
    "time": "DEP-04",
    "threading": "ASYNC-01",
    "asyncio": "ASYNC-01",
    "multiprocessing": "ASYNC-01",
    "concurrent": "ASYNC-01",
}
STREAMS = {"stdout", "stderr", "exit"}
ENVIRON = {"environ", "getenv", "putenv"}

# ERR-01・ERR-02: 投げてよい例外と、検証前の JSON を読んでよいモジュール
KIT_ERRORS = {"KitError", "InvalidFileError", "StageError", "CommandError"}
RAW_JSON_READERS = {"fsops", "workspace"}

# NAM-03: JSON のキーを書くモジュールと、キーを受け取る shape の関数
KEY_MODULES = {"charter", "design", "contracts"}
KEY_FUNCTIONS = {"text", "filled", "integer", "real", "boolean", "choice", "texts", "objects"}
SNAKE_KEY = re.compile(r"^[a-z][a-z0-9_]*$")

# CODE-06・STR-06・OPS-05: 決まった文字列を書いてよいモジュール
FILE_NAME = re.compile(r"^[A-Za-z0-9_.-]+\.(json|jsonl|md|patch|txt)$")
FILE_NAME_OWNERS = {"layout", "prompts"}
AGENT_NAME = re.compile(r"^forge-(designer|builder|grader|analyst)$")
AGENT_NAME_OWNERS = {"contracts"}
RULE_ID = re.compile(r"^B[0-9]{2}$")
RULE_ID_OWNERS = {"bundle"}
# CODE-06: ディレクトリにつなぐのを layout.py だけに限るファイル名の定数。バンドルの中の SKILL.md は除く
FILE_CONSTANTS = {key for key, value in vars(layout).items() if isinstance(value, str) and FILE_NAME.match(value)}
BUNDLE_FILES = {"SKILL_FILE"}
PRINT_FLAG = "-p"
PRINT_FLAG_OWNERS = {"execute"}
FORBIDDEN_IN_KIT = ("bypassPermissions", "--dangerously-skip-permissions", "--bare")

# OPS-04: 評価と構築を進める段の入口。最初の文で承認済みの charter を読む
ENTRIES = {
    ("designing", "design_new"),
    ("designing", "design_check"),
    ("designing", "design_approve"),
    ("building", "build"),
    ("building", "bundle_check"),
    ("building", "install"),
    ("prepare", "prepare"),
    ("execute", "execute"),
    ("collect", "collect"),
    ("score", "score"),
    ("analyze", "analyze"),
    ("analyze", "propose"),
    ("compare", "compare"),
    ("decide", "decide"),
    ("report", "report"),
}
# OPS-04: 対象のリポジトリの .claude/ に書く関数と、呼んでよいモジュール
PLACE_CALLERS = {"building", "decide"}

# STR-01: 配布物のディレクトリに置いてよいもの
KIT_LAYOUT = {
    KIT: {".forge", "claude"},
    FORGE: {"forge.py", "forge_kit", "templates"},
    FORGE / "templates": {"prompts"},
    KIT / "claude": {"skills", "agents"},
}

# STR-05・PROC-07: 配布するスキルとサブエージェントの書式
SKILL_PREFIX = "forge-"
SKILL_MAX_LINES = 500
SKILL_ALLOWED_TOOLS = "Bash(python3 .forge/forge.py *)"
SKILL_LINK = re.compile(r"\]\(([^)#]+)\)")
HUMAN_GATE = "## 人に確かめること"
FORBIDDEN_AGENT_TOOLS = {"Skill", "Agent"}
NO_CLAUDE_MD = {contracts.AGENTS["grader"], contracts.AGENTS["analyst"]}
# NAM-02: 語彙表の動詞と同じ意味の別名
SYNONYM_VERBS = ("get_", "fetch_", "format_", "create_", "validate_", "save_")


@dataclass(frozen=True)
class Violation:
    rule: str
    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.rule} {self.path.relative_to(ROOT)}:{self.line} {self.message}"


def has_files(directory: Path) -> bool:
    """__pycache__ 以外のファイルがあるか。空のディレクトリは git が追わないので、無いものとして扱う。"""
    return any(path.is_file() and CACHE not in path.parts for path in directory.rglob("*"))


def modules() -> dict[str, Path]:
    return {path.stem: path for path in sorted(PACKAGE.glob("*.py"))}


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def kit_imports(tree: ast.Module) -> Iterator[tuple[str, int]]:
    """forge_kit のモジュールの import（`from forge_kit import x`、`from forge_kit.x import y`）。"""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "forge_kit":
            for alias in node.names:
                yield alias.name, node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("forge_kit."):
            yield node.module.split(".")[1], node.lineno


def top_imports(tree: ast.Module) -> Iterator[tuple[str, int]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0], node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module.split(".")[0], node.lineno


def check_layout() -> Iterator[Violation]:
    for directory, allowed in KIT_LAYOUT.items():
        for entry in sorted(directory.iterdir()):
            if entry.name not in allowed and entry.name != CACHE:
                yield Violation("STR-01", entry, 1, f"{directory.relative_to(ROOT)} に置けるのは {sorted(allowed)}")
    for entry in sorted(PACKAGE.iterdir()):
        if entry.is_dir() and has_files(entry):
            yield Violation("STR-01", entry, 1, "forge_kit にサブパッケージを作らない（モジュールは平らに並べる）")
    for entry in sorted((FORGE / "templates" / "prompts").iterdir()):
        if entry.suffix != ".md":
            yield Violation("STR-01", entry, 1, "templates/prompts に置けるのはプロンプトのひな形（.md）だけ")


def check_module_table(found: dict[str, Path]) -> Iterator[Violation]:
    for name, path in found.items():
        if name not in ALLOWED_IMPORTS:
            yield Violation("STR-02", path, 1, "モジュールの表に無い。structure_check.py と architecture.md の表に足す")
    for name in sorted(set(ALLOWED_IMPORTS) - set(found)):
        yield Violation("STR-02", PACKAGE / f"{name}.py", 1, "表にあるモジュールが無い。表から消す")


def check_init(found: dict[str, Path]) -> Iterator[Violation]:
    body = parse(found["__init__"]).body
    docstring_only = len(body) == 1 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
    if not docstring_only:
        yield Violation("STR-03", found["__init__"], 1, "__init__.py には docstring だけを書く")


def check_dependencies(name: str, path: Path, tree: ast.Module) -> Iterator[Violation]:
    allowed = ALLOWED_IMPORTS.get(name, set())
    for imported, line in kit_imports(tree):
        if imported not in allowed:
            yield Violation("DEP-01", path, line, f"{name} から {imported} を import しない（許可: {sorted(allowed)}）")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("forge_kit"):
            for alias in node.names:
                if alias.name.startswith("_"):
                    yield Violation("DEP-02", path, node.lineno, f"非公開の名前 {alias.name} を外から import しない")
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in ALLOWED_IMPORTS
            and node.attr.startswith("_")
            and not node.attr.startswith("__")
        ):
            yield Violation("DEP-02", path, node.lineno, f"非公開の名前 {node.value.id}.{node.attr} を外から使わない")


def check_names(path: Path, tree: ast.Module) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.lstrip("_").startswith(
            SYNONYM_VERBS
        ):
            yield Violation(
                "NAM-02",
                path,
                node.lineno,
                f"{node.name} は語彙表の動詞で始める（{'、'.join(SYNONYM_VERBS)} は使わない）",
            )


def check_stdlib(path: Path, tree: ast.Module) -> Iterator[Violation]:
    for imported, line in top_imports(tree):
        if imported not in STDLIB | LOCAL:
            yield Violation("DEP-03", path, line, f"{imported} は使ってよい標準ライブラリの表に無い")


def check_side_effects(name: str, path: Path, tree: ast.Module) -> Iterator[Violation]:
    for imported, line in top_imports(tree):
        owners = ONLY_IN.get(imported)
        if owners is not None and name not in owners:
            yield Violation(IMPORT_RULES[imported], path, line, f"{imported} を使えるのは {sorted(owners)} だけ")
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "open"
            and name != "fsops"
        ):
            yield Violation("DEP-04", path, node.lineno, "ファイルを開けるのは fsops.py だけ")
        if isinstance(node, ast.Attribute):
            if node.attr in FS_WRITERS and name != "fsops" and not _is_name(node.value, "fsops"):
                yield Violation("DEP-04", path, node.lineno, f"{node.attr} でファイルを書けるのは fsops.py だけ")
            if _is_name(node.value, "sys") and node.attr in STREAMS and name != "cli":
                yield Violation("OPS-01", path, node.lineno, f"sys.{node.attr} を使えるのは cli.py だけ")
            if _is_name(node.value, "os") and node.attr in ENVIRON and name != "proc":
                yield Violation("OPS-02", path, node.lineno, f"os.{node.attr} を使えるのは proc.py だけ")


def _is_name(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def check_classes(name: str, path: Path, tree: ast.Module) -> Iterator[Violation]:
    if name == "errors":
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        frozen = any(
            isinstance(item, ast.Call)
            and _is_name(item.func, "dataclass")
            and any(k.arg == "frozen" and isinstance(k.value, ast.Constant) and k.value.value for k in item.keywords)
            for item in node.decorator_list
        )
        if not frozen or node.bases:
            yield Violation("CODE-01", path, node.lineno, f"{node.name} は継承しない @dataclass(frozen=True) にする")


def check_literals(name: str, path: Path, tree: ast.Module) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if FILE_NAME.match(node.value) and name not in FILE_NAME_OWNERS:
            yield Violation("CODE-06", path, node.lineno, f"ファイル名 {node.value!r} は layout.py の定数を使う")
        if AGENT_NAME.match(node.value) and name not in AGENT_NAME_OWNERS:
            yield Violation("CODE-06", path, node.lineno, f"{node.value!r} は contracts.AGENTS を使う")
        if RULE_ID.match(node.value) and name not in RULE_ID_OWNERS:
            yield Violation(
                "STR-06", path, node.lineno, f"バンドルの決まりの id {node.value!r} は bundle.RULES だけに書く"
            )
        if node.value == PRINT_FLAG and name not in PRINT_FLAG_OWNERS:
            yield Violation("OPS-05", path, node.lineno, "claude -p の引数は execute.command だけで組み立てる")


def check_paths(name: str, path: Path, tree: ast.Module) -> Iterator[Violation]:
    if name == "layout":
        return
    for node in ast.walk(tree):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
            continue
        right = node.right
        if (
            isinstance(right, ast.Attribute)
            and _is_name(right.value, "layout")
            and right.attr in FILE_CONSTANTS - BUNDLE_FILES
        ):
            yield Violation(
                "CODE-06", path, node.lineno, f"layout.{right.attr} をつながず、Layout のメソッドで受け取る"
            )


def check_forbidden() -> Iterator[Violation]:
    """kit/ の全ファイルに、権限を広げる文字列が無いか（OPS-05）。"""
    for path in sorted(p for p in KIT.rglob("*") if p.is_file() and CACHE not in p.parts):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for word in FORBIDDEN_IN_KIT:
                if word in line:
                    yield Violation("OPS-05", path, number, f"{word} を配布物に書かない（権限を広げない）")


def check_errors(name: str, path: Path, tree: ast.Module) -> Iterator[Violation]:
    for node in ast.walk(tree):
        raised = _raised_name(node)
        if isinstance(node, ast.Raise) and raised is not None and raised not in KIT_ERRORS:
            yield Violation("ERR-01", path, node.lineno, f"{raised} ではなく errors.py の例外を投げる")
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "read_json"
            and _is_name(node.value, "fsops")
            and name not in RAW_JSON_READERS
        ):
            yield Violation("ERR-02", path, node.lineno, "JSON は workspace の load_* で検証して読む")


def _raised_name(node: ast.AST) -> str | None:
    """`raise Name(...)` と `raise Name` の Name。それ以外（再送出など）は None。"""
    if not isinstance(node, ast.Raise) or node.exc is None:
        return None
    target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
    return target.id if isinstance(target, ast.Name) else None


def check_json_keys(name: str, path: Path, tree: ast.Module) -> Iterator[Violation]:
    if name not in KEY_MODULES:
        return
    for node in ast.walk(tree):
        keys: list[ast.expr] = []
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and _is_name(node.func.value, "shape"):
            if node.func.attr in KEY_FUNCTIONS and len(node.args) >= 2:
                keys.append(node.args[1])
            if node.func.attr == "unknown_keys" and len(node.args) >= 2 and isinstance(node.args[1], ast.Tuple):
                keys += node.args[1].elts
        for key in keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str) and not SNAKE_KEY.match(key.value):
                yield Violation("NAM-03", path, key.lineno, f"JSON のキー {key.value!r} は snake_case にする")


def check_calls(name: str, path: Path, tree: ast.Module) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "place"
            and _is_name(node.value, "bundle")
            and name not in PLACE_CALLERS
        ):
            yield Violation("OPS-04", path, node.lineno, f"bundle.place を呼べるのは {sorted(PLACE_CALLERS)} だけ")


def check_entries(found: dict[str, Path]) -> Iterator[Violation]:
    for module, function in sorted(ENTRIES):
        tree = parse(found[module])
        node = next(
            (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function),
            None,
        )
        if node is None:
            yield Violation("OPS-04", found[module], 1, f"入口 {function} が無い。表を直す")
            continue
        body = [n for n in node.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
        if not body or "approved_charter" not in ast.dump(body[0]):
            yield Violation("OPS-04", found[module], node.lineno, f"{function} の最初の文で approved_charter を呼ぶ")


def check_tests(found: dict[str, Path]) -> Iterator[Violation]:
    expected = {name: name for name in found if name not in ("__init__", "errors")}
    expected["install"] = "install"
    for name in sorted(expected):
        path = TESTS / f"test_{name}.py"
        class_name = "".join(part.title() for part in name.split("_")) + "Test"
        if not path.is_file():
            yield Violation("TEST-01", path, 1, f"{name} のテストが無い")
        elif not any(isinstance(n, ast.ClassDef) and n.name == class_name for n in parse(path).body):
            yield Violation("TEST-01", path, 1, f"テストのクラスは {class_name} にする")
    for path in sorted(TESTS.glob("test_*.py")):
        if path.stem[len("test_") :] not in expected:
            yield Violation("TEST-01", path, 1, "対応するモジュールの無いテスト。tests/test_<モジュール>.py にする")
        for imported, line in _all_imports(parse(path)):
            if imported in ("unittest.mock", "mock"):
                yield Violation("TEST-02", path, line, "モックを使わない。tests/support.py の部品と本物の git を使う")


def _all_imports(tree: ast.Module) -> Iterator[tuple[str, int]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from ((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module, node.lineno
            yield from ((f"{node.module}.{alias.name}", node.lineno) for alias in node.names)


def check_skills() -> Iterator[Violation]:
    for directory in sorted(p for p in (KIT / "claude" / "skills").iterdir() if p.is_dir() and has_files(p)):
        path = directory / "SKILL.md"
        if not path.is_file():
            yield Violation("STR-05", directory, 1, "SKILL.md が無い")
            continue
        text = path.read_text(encoding="utf-8")
        fields = bundle.frontmatter(text)
        if not directory.name.startswith(SKILL_PREFIX) or fields.get("name") != directory.name:
            yield Violation("STR-05", path, 1, f"ディレクトリ名と name を同じ {SKILL_PREFIX}<名前> にする")
        if not fields.get("description"):
            yield Violation("STR-05", path, 1, "description を書く")
        if fields.get("disable-model-invocation") != "true":
            yield Violation("STR-05", path, 1, "disable-model-invocation: true にする（人が明示して呼ぶ）")
        if fields.get("allowed-tools") != SKILL_ALLOWED_TOOLS or "context" in fields:
            yield Violation("STR-05", path, 1, f"allowed-tools を {SKILL_ALLOWED_TOOLS} にし、context を書かない")
        if len(text.splitlines()) > SKILL_MAX_LINES:
            yield Violation("STR-05", path, 1, f"SKILL.md は {SKILL_MAX_LINES} 行以内にする")
        yield from _check_references(directory, path, text)
        if HUMAN_GATE not in text.splitlines() or "AskUserQuestion" not in text:
            yield Violation("PROC-07", path, 1, f"「{HUMAN_GATE}」の節と、AskUserQuestion で聞く手順を書く")


def _check_references(directory: Path, path: Path, text: str) -> Iterator[Violation]:
    linked = set()
    for number, line in enumerate(text.splitlines(), 1):
        for target in SKILL_LINK.findall(line):
            if "://" in target:
                continue
            parts = target.split("/")
            if len(parts) != 2 or parts[0] != "references" or not (directory / target).is_file():
                yield Violation(
                    "STR-05", path, number, f"参照 {target} は references/<ファイル> の実在するファイルにする"
                )
            linked.add(target)
    references = directory / "references"
    for file in sorted(references.glob("*")) if references.is_dir() else []:
        if f"references/{file.name}" not in linked:
            yield Violation("STR-05", file, 1, "SKILL.md から参照されていない")


def check_agents() -> Iterator[Violation]:
    agents_dir = KIT / "claude" / "agents"
    names = {path.stem for path in agents_dir.glob("*.md")}
    for name in sorted(set(contracts.AGENTS.values()) ^ names):
        yield Violation("STR-05", agents_dir / f"{name}.md", 1, "contracts.AGENTS とエージェントの定義をそろえる")
    for path in sorted(agents_dir.glob("*.md")):
        fields = bundle.frontmatter(path.read_text(encoding="utf-8"))
        if fields.get("name") != path.stem or not fields.get("description"):
            yield Violation("STR-05", path, 1, "name をファイル名と同じにし、description を書く")
        tools = {tool.strip() for tool in fields.get("tools", "").split(",") if tool.strip()}
        if not tools or tools & FORBIDDEN_AGENT_TOOLS:
            yield Violation("STR-05", path, 1, f"tools を列挙し、{sorted(FORBIDDEN_AGENT_TOOLS)} を入れない")
        if path.stem in NO_CLAUDE_MD and fields.get("omitClaudeMd") != "true":
            yield Violation("STR-05", path, 1, "採点役と分析役には omitClaudeMd: true を書く")


def python_files() -> list[Path]:
    files = [*sorted(PACKAGE.glob("*.py")), FORGE / "forge.py", ROOT / "install.py"]
    files += sorted((ROOT / "scripts").glob("*.py"))
    files += sorted(TESTS.glob("*.py"))
    return files


def run() -> list[Violation]:
    found = modules()
    violations = [*check_layout(), *check_module_table(found), *check_init(found)]
    for name, path in found.items():
        tree = parse(path)
        for check in (
            check_dependencies,
            check_side_effects,
            check_classes,
            check_literals,
            check_paths,
            check_errors,
            check_json_keys,
            check_calls,
        ):
            violations += check(name, path, tree)
    for path in python_files():
        tree = parse(path)
        violations += [*check_stdlib(path, tree), *check_names(path, tree)]
    violations += [*check_entries(found), *check_forbidden(), *check_tests(found), *check_skills(), *check_agents()]
    return violations


def main() -> int:
    violations = run()
    for violation in violations:
        print(violation)
    if violations:
        print(f"構造検査: {len(violations)} 件の違反")
        return 1
    print("構造検査: 違反なし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
