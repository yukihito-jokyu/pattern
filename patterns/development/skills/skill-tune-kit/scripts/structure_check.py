"""構造検査。rules.md の structure のルールを照合し、違反を `<ルールID> <パス>:<行> <内容>` で出す。"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from tune_kit import checks, cli, contracts

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "kit" / ".tune" / "tune_kit"
TESTS = ROOT / "tests"
SKILL_DIR = ROOT / "kit" / "claude" / "skills" / "skill-tune"
AGENTS_DIR = ROOT / "kit" / "claude" / "agents"
PY_ROOTS = (ROOT / "kit", ROOT / "scripts", TESTS, ROOT / "install.py")
IGNORED_PARTS = frozenset({"__pycache__", ".mypy_cache", ".ruff_cache", ".DS_Store"})

# STR-01: kit/、scripts/、tests/ のファイルを置いてよい場所（ルートからの相対パスの正規表現）
LAYOUT = (
    r"kit/\.tune/tune\.py",
    r"kit/\.tune/tune_kit/[a-z_]+\.py",
    r"kit/\.tune/templates/prompts/[a-z]+\.md",
    r"kit/claude/skills/skill-tune/SKILL\.md",
    r"kit/claude/skills/skill-tune/references/[a-z-]+\.md",
    r"kit/claude/agents/tune-[a-z]+\.md",
    r"scripts/(structure_check|gen_docs)\.py",
    r"tests/(__init__|support)\.py",
    r"tests/test_[a-z_]+\.py",
    r"tests/fixtures/.+",
)

# DEP-01: モジュールごとに import してよい tune_kit のモジュール（architecture.md の依存の許可表と1対1）
SHARED: dict[str, frozenset[str]] = {
    "errors": frozenset(),
    "render": frozenset(),
    "splitting": frozenset(),
    "checks": frozenset(),
    "metrics": frozenset(),
    "layout": frozenset({"errors"}),
    "plan": frozenset({"checks", "layout"}),
    "contracts": frozenset({"layout", "plan"}),
    "fsops": frozenset({"errors"}),
    "proc": frozenset({"errors"}),
    "prompts": frozenset({"fsops", "layout", "errors"}),
    "workspace": frozenset({"contracts", "fsops", "layout", "metrics", "plan", "splitting", "errors"}),
    "evidence": frozenset({"contracts", "fsops", "layout", "plan", "render"}),
}
STAGES: dict[str, frozenset[str]] = {
    "planning": frozenset({"checks", "contracts", "fsops", "layout", "plan", "render", "workspace", "errors"}),
    "status": frozenset({"contracts", "layout", "plan", "render", "workspace"}),
    "evaluate": frozenset(
        {"checks", "contracts", "fsops", "layout", "plan", "proc", "prompts", "render", "workspace", "errors"}
    ),
    "learn": frozenset(
        {"contracts", "evidence", "fsops", "layout", "plan", "prompts", "render", "workspace", "errors"}
    ),
    "decide": frozenset({"contracts", "fsops", "layout", "metrics", "plan", "render", "workspace", "errors"}),
    "audit": frozenset(
        {"contracts", "evidence", "fsops", "layout", "plan", "prompts", "render", "workspace", "errors"}
    ),
    "report": frozenset({"contracts", "fsops", "layout", "metrics", "plan", "render", "workspace", "errors"}),
}
ENTRY: dict[str, frozenset[str]] = {"cli": frozenset({*STAGES, "layout", "errors"})}
ALLOWED = {**SHARED, **STAGES, **ENTRY}

# DEP-03: import してよい標準ライブラリ（先頭の名前）
STDLIB = frozenset(
    {
        "__future__",
        "argparse",
        "ast",
        "collections",
        "contextlib",
        "dataclasses",
        "datetime",
        "difflib",
        "fractions",
        "hashlib",
        "io",
        "json",
        "math",
        "os",
        "pathlib",
        "re",
        "shutil",
        "subprocess",
        "sys",
        "tempfile",
        "unicodedata",
        "unittest",
    }
)
# DEP-04、ASYNC-01、OPS-01: import の名前と、import してよい tune_kit のモジュール（空なら全部で禁止）
IMPORT_LIMITS: dict[str, tuple[str, frozenset[str]]] = {
    "shutil": ("DEP-04", frozenset({"fsops"})),
    "subprocess": ("DEP-04", frozenset({"proc"})),
    "datetime": ("DEP-04", frozenset({"cli"})),
    "time": ("DEP-04", frozenset({"cli"})),
    "threading": ("ASYNC-01", frozenset()),
    "concurrent": ("ASYNC-01", frozenset()),
    "asyncio": ("ASYNC-01", frozenset()),
    "multiprocessing": ("ASYNC-01", frozenset()),
    "logging": ("OPS-01", frozenset()),
}
# DEP-04、OPS-02、ERR-02: 属性と関数の名前と、使ってよいモジュール
ATTRIBUTE_LIMITS: dict[str, tuple[str, frozenset[str]]] = {
    "os.environ": ("OPS-02", frozenset({"proc"})),
    "os.getenv": ("OPS-02", frozenset({"proc"})),
    "fsops.read_json": ("ERR-02", frozenset({"workspace"})),
    "json.loads": ("ERR-02", frozenset({"fsops", "checks"})),
    "json.load": ("ERR-02", frozenset({"fsops", "checks"})),
    "sys.exit": ("DEP-04", frozenset({"cli"})),
}
CALL_LIMITS: dict[str, tuple[str, frozenset[str]]] = {
    "open": ("DEP-04", frozenset({"fsops"})),
    "print": ("DEP-04", frozenset({"cli"})),
}
# DEP-04: ファイルを書き換えるメソッドの名前（fsops 以外で呼ばない）
WRITE_METHODS = frozenset({"write_text", "write_bytes", "mkdir", "unlink", "rmtree", "rmdir", "touch"})
# NAM-02: 関数名の先頭の語
VERBS = frozenset(
    {
        "load",
        "read",
        "parse",
        "build",
        "render",
        "write",
        "copy",
        "remove",
        "run",
        "compute",
        "check",
        "evaluate",
        "find",
        "list",
        "is",
        "has",
        "main",
        "require",
    }
)
# NAM-03: 第2引数に JSON のキーを取る関数（plan.py と contracts.py の _read_*）
KEY_READERS = frozenset(
    {"_read_text", "_read_number", "_read_int", "_read_names", "_read_flag", "_read_items", "_read_rate"}
)
# NAM-03: dataclass のフィールドではないが、配列や入れ子を包むキー
WRAPPER_KEYS = frozenset({"cases", "grades", "ratios", "fix", "case", "check"})
# ERR-01: 投げてよい例外と、捕まえてよい例外（モジュールごと）
RAISABLE = frozenset({"KitError", "InvalidFileError", "StageError", "CommandError"})
CATCHABLE: dict[str, frozenset[str]] = {
    "cli": frozenset({"KitError"}),
    "fsops": frozenset({"OSError", "UnicodeDecodeError", "json.JSONDecodeError"}),
    "proc": frozenset({"OSError", "subprocess.TimeoutExpired"}),
    "plan": frozenset({"re.error", "ValueError", "json.JSONDecodeError"}),
    "checks": frozenset({"re.error", "ValueError", "json.JSONDecodeError"}),
}
# OPS-04: 公開関数の最初に承認済みの計画を読む段のモジュール
APPROVED_STAGES = frozenset({"evaluate", "learn", "decide", "audit", "report"})
STATE_READERS = ("read_", "list_", "compute_")
SKILL_LINE_LIMIT = 500
SKILL_FRONTMATTER = {
    "name": "skill-tune",
    "disable-model-invocation": "true",
    "allowed-tools": "Bash(python3 .tune/tune.py *)",
}
FILE_LITERAL = re.compile(r"[A-Za-z0-9_.-]+\.(json|md)")
SNAKE = re.compile(r"[a-z][a-z0-9_]*")


@dataclass(frozen=True)
class Problem:
    rule: str
    path: Path
    line: int
    message: str

    def render(self) -> str:
        return f"{self.rule} {self.path.relative_to(ROOT).as_posix()}:{self.line} {self.message}"


@dataclass(frozen=True)
class Source:
    path: Path
    tree: ast.Module

    @property
    def module(self) -> str:
        return self.path.stem

    @property
    def in_package(self) -> bool:
        return self.path.parent == PACKAGE


def list_files(base: Path) -> Iterator[Path]:
    if base.is_file():
        yield base
        return
    for path in sorted(base.rglob("*")):
        if path.is_file() and not IGNORED_PARTS & set(path.relative_to(ROOT).parts):
            yield path


def load_sources() -> list[Source]:
    sources = []
    for base in PY_ROOTS:
        for path in list_files(base):
            if path.suffix == ".py" and "fixtures" not in path.relative_to(ROOT).parts:
                sources.append(Source(path, ast.parse(path.read_text(encoding="utf-8"), str(path))))
    return sources


def check_layout() -> list[Problem]:
    """STR-01: 表に無い場所のファイル。"""
    problems = []
    for base in (ROOT / "kit", ROOT / "scripts", TESTS):
        for path in list_files(base):
            relative = path.relative_to(ROOT).as_posix()
            if not any(re.fullmatch(pattern, relative) for pattern in LAYOUT):
                problems.append(Problem("STR-01", path, 1, "置き場の表（LAYOUT）に無い場所です"))
    return problems


def check_registry() -> list[Problem]:
    """STR-02: モジュールの表への登録。"""
    names = {path.stem for path in PACKAGE.glob("*.py") if path.stem != "__init__"}
    problems = [
        Problem("STR-02", PACKAGE / f"{name}.py", 1, "SHARED・STAGES・ENTRY のどれにも無い")
        for name in names - set(ALLOWED)
    ]
    problems += [
        Problem("STR-02", PACKAGE, 1, f"表の {name} に対応するファイルがありません") for name in set(ALLOWED) - names
    ]
    groups = [set(SHARED), set(STAGES), set(ENTRY)]
    problems += [
        Problem("STR-02", PACKAGE, 1, f"{name} が2つ以上の表にあります")
        for name in ALLOWED
        if sum(name in g for g in groups) > 1
    ]
    return problems


def check_entry(source: Source) -> list[Problem]:
    """STR-03: __init__.py は docstring だけ、tune_kit に __main__ の判定を書かない。"""
    problems = []
    if source.module == "__init__" and (len(source.tree.body) != 1 or ast.get_docstring(source.tree) is None):
        problems.append(Problem("STR-03", source.path, 1, "__init__.py は docstring だけにしてください"))
    for node in ast.walk(source.tree):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "__name__":
            problems.append(
                Problem("STR-03", source.path, node.lineno, "tune_kit に __main__ の判定を書かないでください")
            )
    return problems


def read_frontmatter(path: Path) -> tuple[dict[str, str], int]:
    """frontmatter の key: value と、ファイルの行数。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    fields: dict[str, str] = {}
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields, len(lines)


def check_skill() -> list[Problem]:
    """STR-05: 配布するスキルの frontmatter と行数。"""
    path = SKILL_DIR / "SKILL.md"
    if not path.is_file():
        return [Problem("STR-05", SKILL_DIR, 1, "SKILL.md がありません")]
    fields, count = read_frontmatter(path)
    problems = [
        Problem("STR-05", path, 1, f"frontmatter の {key} は {value} にしてください")
        for key, value in SKILL_FRONTMATTER.items()
        if fields.get(key) != value
    ]
    problems += [
        Problem("STR-05", path, 1, f"frontmatter に {key} がありません")
        for key in ("description", "argument-hint")
        if not fields.get(key)
    ]
    if count > SKILL_LINE_LIMIT:
        problems.append(Problem("STR-05", path, count, f"SKILL.md は {SKILL_LINE_LIMIT} 行以内にしてください"))
    return problems


def check_agent(path: Path) -> list[Problem]:
    fields, _count = read_frontmatter(path)
    problems = [
        Problem("STR-05", path, 1, f"frontmatter に {key} がありません")
        for key in ("description", "tools")
        if not fields.get(key)
    ]
    if fields.get("name") != path.stem:
        problems.append(Problem("STR-05", path, 1, "frontmatter の name はファイル名と同じにしてください"))
    tools = {tool.strip() for tool in fields.get("tools", "").split(",")}
    problems += [
        Problem("STR-05", path, 1, f"tools に {tool} を入れないでください")
        for tool in ("Skill", "Agent")
        if tool in tools
    ]
    executor = path.stem == contracts.AGENTS["executor"]
    if executor and "omitClaudeMd" in fields:
        problems.append(Problem("STR-05", path, 1, "実行役には omitClaudeMd を書かないでください"))
    if not executor and fields.get("omitClaudeMd") != "true":
        problems.append(Problem("STR-05", path, 1, "omitClaudeMd: true にしてください"))
    return problems


def check_agents() -> list[Problem]:
    """STR-05: サブエージェントの frontmatter と、contracts.AGENTS との対応。"""
    paths = {path.stem: path for path in AGENTS_DIR.glob("*.md")}
    expected = set(contracts.AGENTS.values())
    problems = [
        Problem("STR-05", AGENTS_DIR, 1, f"{name}.md がありません（contracts.AGENTS にある）")
        for name in sorted(expected - set(paths))
    ]
    problems += [
        Problem("STR-05", paths[name], 1, "contracts.AGENTS にありません") for name in sorted(set(paths) - expected)
    ]
    for path in paths.values():
        problems += check_agent(path)
    return problems


def list_imports(source: Source) -> Iterator[tuple[ast.stmt, str, list[str]]]:
    """import の文、モジュールの名前、import した名前。"""
    for node in ast.walk(source.tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node, alias.name, []
        elif isinstance(node, ast.ImportFrom):
            yield node, ("." * node.level) + (node.module or ""), [alias.name for alias in node.names]


def check_package_import(source: Source, node: ast.stmt, module: str, names: list[str]) -> list[Problem]:
    """DEP-01、DEP-02、CODE-02: tune_kit の import。"""
    allowed = ALLOWED.get(source.module, frozenset()) if source.in_package else frozenset(ALLOWED)
    if module == "tune_kit" and isinstance(node, ast.ImportFrom):
        problems = [
            Problem("DEP-01", source.path, node.lineno, f"{name} は import の許可表にありません")
            for name in names
            if name not in allowed
        ]
        return problems
    if module == "tune_kit.errors" and isinstance(node, ast.ImportFrom):
        problems = [
            Problem("DEP-02", source.path, node.lineno, f"{name} は外から使えません")
            for name in names
            if name.startswith("_")
        ]
        if source.in_package and "errors" not in allowed:
            problems.append(Problem("DEP-01", source.path, node.lineno, "errors は import の許可表にありません"))
        return problems
    message = "tune_kit は from tune_kit import <モジュール> で import してください"
    return [Problem("CODE-02", source.path, node.lineno, message)]


def check_imports(source: Source) -> list[Problem]:
    """DEP-01〜03、DEP-04・ASYNC-01・OPS-01 の import、CODE-02、TEST-02。"""
    problems: list[Problem] = []
    for node, module, names in list_imports(source):
        top = module.split(".")[0]
        if module.startswith("."):
            problems.append(Problem("CODE-02", source.path, node.lineno, "相対 import は使わないでください"))
        elif top == "tune_kit":
            problems += check_package_import(source, node, module, names)
        elif module == "unittest.mock" or "mock" in names or top == "mock":
            problems.append(Problem("TEST-02", source.path, node.lineno, "モックを使わないでください"))
        elif top == "tests" and source.path.parent == TESTS:
            continue
        elif top not in STDLIB and top not in IMPORT_LIMITS:
            problems.append(Problem("DEP-03", source.path, node.lineno, f"{module} は STDLIB の表にありません"))
        if top in IMPORT_LIMITS and source.path.is_relative_to(ROOT / "kit"):
            rule, modules = IMPORT_LIMITS[top]
            if not (source.in_package and source.module in modules):
                problems.append(
                    Problem(
                        rule,
                        source.path,
                        node.lineno,
                        f"{top} を import してよいのは {sorted(modules) or 'どこにも無い'} だけです",
                    )
                )
    return problems


def check_future(source: Source) -> list[Problem]:
    """CODE-02: docstring の次の文を from __future__ import annotations にする。"""
    body = source.tree.body[1:] if ast.get_docstring(source.tree) is not None else source.tree.body
    if not body:
        return []
    first = body[0]
    if (
        isinstance(first, ast.ImportFrom)
        and first.module == "__future__"
        and [a.name for a in first.names] == ["annotations"]
    ):
        return []
    return [
        Problem(
            "CODE-02",
            source.path,
            first.lineno,
            "docstring の次の文を from __future__ import annotations にしてください",
        )
    ]


def build_dotted(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{build_dotted(node.value)}.{node.attr}"
    return ""


def list_attribute_problems(module: str, node: ast.Attribute) -> Iterator[tuple[str, str]]:
    """属性の参照の違反（ルールID、内容）。"""
    dotted = build_dotted(node)
    owner = build_dotted(node.value)
    if owner in ALLOWED and node.attr.startswith("_") and not node.attr.startswith("__"):
        yield "DEP-02", f"{dotted} は外から使えません"
    limited = ATTRIBUTE_LIMITS.get(dotted)
    if limited is not None and module not in limited[1]:
        yield limited[0], f"{dotted} を使ってよいのは {', '.join(sorted(limited[1]))} だけです"
    if module in ("workspace", "status") and owner == "fsops" and not node.attr.startswith(STATE_READERS):
        yield "STATE-01", f"{module} は fsops.{node.attr} を呼べません（読むだけ）"
    if node.attr in WRITE_METHODS and "fsops" not in (owner, module):
        yield "DEP-04", f".{node.attr} でファイルを書き換えてよいのは fsops だけです"


def check_side_effects(source: Source) -> list[Problem]:
    """DEP-04、OPS-02、ERR-02、STATE-01、DEP-02: 呼び出しと属性の参照。"""
    problems: list[Problem] = []
    for node in ast.walk(source.tree):
        if isinstance(node, ast.Attribute):
            found = list(list_attribute_problems(source.module, node))
            problems += [Problem(rule, source.path, node.lineno, message) for rule, message in found]
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in CALL_LIMITS:
            rule, modules = CALL_LIMITS[node.func.id]
            if source.module not in modules:
                message = f"{node.func.id} を使ってよいのは {', '.join(sorted(modules))} だけです"
                problems.append(Problem(rule, source.path, node.lineno, message))
    return problems


def check_names(source: Source) -> list[Problem]:
    """NAM-02: モジュールの関数名。段のモジュールの公開関数はサブコマンド名。"""
    commands = {name.replace("-", "_") for name in cli.COMMANDS}
    problems = []
    for node in source.tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        public = not node.name.startswith("_")
        if source.module in STAGES and public:
            if node.name not in commands:
                problems.append(
                    Problem(
                        "NAM-02",
                        source.path,
                        node.lineno,
                        f"段のモジュールの公開関数 {node.name} はサブコマンド名にしてください",
                    )
                )
            continue
        verb = node.name.lstrip("_").split("_")[0]
        if verb not in VERBS:
            problems.append(
                Problem("NAM-02", source.path, node.lineno, f"関数 {node.name} は動詞表の語で始めてください（{verb}）")
            )
    return problems


def list_fields(source: Source) -> set[str]:
    fields: set[str] = set()
    for node in source.tree.body:
        if isinstance(node, ast.ClassDef):
            fields |= {
                item.target.id
                for item in node.body
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
            }
    return fields


def list_json_keys(source: Source) -> Iterator[tuple[int, str]]:
    """JSON の辞書から読むキー（.get の第1引数、_read_* の第2引数、添字）。"""
    for node in ast.walk(source.tree):
        key: ast.expr | None = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
        ):
            key = node.args[0]
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in KEY_READERS
            and len(node.args) > 1
        ):
            key = node.args[1]
        elif isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load):
            key = node.slice if isinstance(node.slice, ast.Constant) else None
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            yield key.lineno, key.value


def check_json_keys(source: Source) -> list[Problem]:
    """NAM-03: plan.py と contracts.py が読む JSON のキー。"""
    if source.module not in ("plan", "contracts") or not source.in_package:
        return []
    allowed = list_fields(source) | WRAPPER_KEYS
    return [
        Problem("NAM-03", source.path, line, f"キー {key} は snake_case で、dataclass のフィールド名にしてください")
        for line, key in list_json_keys(source)
        if not SNAKE.fullmatch(key) or key not in allowed
    ]


def is_frozen_dataclass(node: ast.ClassDef) -> bool:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call) and build_dotted(decorator.func) == "dataclass":
            return any(
                k.arg == "frozen" and isinstance(k.value, ast.Constant) and k.value.value is True
                for k in decorator.keywords
            )
    return False


def check_classes(source: Source) -> list[Problem]:
    """CODE-01: クラスは基底の無い frozen の dataclass（errors.py の例外は除く）。"""
    if source.module == "errors":
        return []
    return [
        Problem(
            "CODE-01",
            source.path,
            node.lineno,
            f"クラス {node.name} は基底の無い @dataclass(frozen=True) にしてください",
        )
        for node in ast.walk(source.tree)
        if isinstance(node, ast.ClassDef) and (node.bases or not is_frozen_dataclass(node))
    ]


def check_literals(source: Source) -> list[Problem]:
    """CODE-06: ファイル名とエージェント名の文字列。"""
    problems = []
    for node in ast.walk(source.tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if source.module != "layout" and FILE_LITERAL.fullmatch(node.value):
            problems.append(
                Problem(
                    "CODE-06", source.path, node.lineno, f"ファイル名 {node.value} は layout の定数を使ってください"
                )
            )
        if source.module != "contracts" and node.value.startswith("tune-"):
            problems.append(
                Problem("CODE-06", source.path, node.lineno, "エージェント名は contracts.AGENTS を使ってください")
            )
    return problems


def list_handlers(source: Source) -> Iterator[tuple[ast.ExceptHandler, str]]:
    """except の節と、その節を含むモジュール直下の関数の名前。"""
    for function in source.tree.body:
        for node in ast.walk(function):
            if isinstance(node, ast.ExceptHandler):
                yield node, function.name if isinstance(function, ast.FunctionDef) else ""


def check_errors(source: Source) -> list[Problem]:
    """ERR-01: 投げる例外と捕まえる例外。"""
    problems = []
    for node in ast.walk(source.tree):
        if isinstance(node, ast.Raise) and node.exc is not None:
            target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            name = build_dotted(target).split(".")[-1]
            if name not in RAISABLE:
                problems.append(
                    Problem("ERR-01", source.path, node.lineno, f"{name} ではなく errors.py の例外を投げてください")
                )
    allowed = CATCHABLE.get(source.module, frozenset())
    for handler, function in list_handlers(source):
        types = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type] if handler.type else []
        names = [build_dotted(item) for item in types] or ["（すべて）"]
        outside = source.module == "cli" and function != "main"
        for name in names:
            if name not in allowed or outside:
                problems.append(
                    Problem("ERR-01", source.path, handler.lineno, f"{source.module} で {name} を捕まえないでください")
                )
    return problems


def is_approved_call(statement: ast.stmt) -> bool:
    value = statement.value if isinstance(statement, (ast.Assign, ast.Expr)) else None
    return isinstance(value, ast.Call) and build_dotted(value.func) == "workspace.load_approved"


def check_approved(source: Source) -> list[Problem]:
    """OPS-04: 評価を進める段の公開関数は、最初に workspace.load_approved を呼ぶ。"""
    if source.module not in APPROVED_STAGES or not source.in_package:
        return []
    problems = []
    for node in source.tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            body = node.body[1:] if ast.get_docstring(node) is not None else node.body
            if not body or not is_approved_call(body[0]):
                problems.append(
                    Problem(
                        "OPS-04",
                        source.path,
                        node.lineno,
                        f"{node.name} の最初の文で workspace.load_approved を呼んでください",
                    )
                )
    return problems


def check_tests() -> list[Problem]:
    """TEST-01、TEST-03: テストのファイル、クラス、決めた名前のテスト。"""
    problems = []
    for path in sorted(PACKAGE.glob("*.py")):
        if path.stem == "__init__":
            continue
        test_path = TESTS / f"test_{path.stem}.py"
        expected = "".join(part.capitalize() for part in path.stem.split("_")) + "Test"
        if not test_path.is_file():
            problems.append(Problem("TEST-01", path, 1, f"tests/test_{path.stem}.py がありません"))
            continue
        tree = ast.parse(test_path.read_text(encoding="utf-8"))
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == expected]
        if not classes or not any(build_dotted(base) == "unittest.TestCase" for base in classes[0].bases):
            problems.append(
                Problem("TEST-01", test_path, 1, f"unittest.TestCase を継承した {expected} クラスがありません")
            )
    problems += check_named_tests(TESTS / "test_checks.py", [f"test_kind_{kind}" for kind in checks.KINDS])
    problems += check_named_tests(
        TESTS / "test_cli.py", [f"test_command_{name.replace('-', '_')}" for name in cli.COMMANDS]
    )
    return problems


def check_named_tests(path: Path, names: list[str]) -> list[Problem]:
    if not path.is_file():
        return []
    defined = {
        node.name for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))) if isinstance(node, ast.FunctionDef)
    }
    return [Problem("TEST-03", path, 1, f"{name} がありません") for name in names if name not in defined]


def check_source(source: Source) -> list[Problem]:
    problems = check_imports(source) + check_future(source)
    if source.in_package:
        problems += check_entry(source) + check_side_effects(source) + check_names(source) + check_json_keys(source)
        problems += check_classes(source) + check_literals(source) + check_errors(source) + check_approved(source)
    else:
        problems += [p for p in check_side_effects(source) if p.rule == "DEP-02"]
    return problems


def main() -> int:
    problems = check_layout() + check_registry() + check_skill() + check_agents() + check_tests()
    for source in load_sources():
        problems += check_source(source)
    for problem in sorted(problems, key=lambda p: (p.path, p.line, p.rule)):
        print(problem.render())
    if problems:
        print(f"構造検査: {len(problems)} 件の違反")
        return 1
    print("構造検査: 違反なし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
