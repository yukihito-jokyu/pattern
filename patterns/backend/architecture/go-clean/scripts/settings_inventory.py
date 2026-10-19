"""設定ファイル・コード定数を読み、台帳との照合と元の書式を保った値の更新を行う。"""

import json
import re

try:
    import yaml
except ImportError as error:
    raise ImportError("setupの準備が必要です: python3 -m pip install -r requirements-setup.txt") from error

YAML_FILES = ["compose.yaml", ".golangci.yml", ".vscode/settings.json", ".vscode/extensions.json", ".claude/settings.json"]
CODE_FILES = ["cmd/api/main.go", "internal/infra/database/database.go", "internal/domain/user/user.go", "internal/adapter/handler/json.go", "internal/adapter/handler/error.go"]


def identity(file, path):
    return file + "::/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in path)


def yaml_nodes(text):
    def visit(node, path):
        if isinstance(node, yaml.MappingNode):
            for key, value in node.value:
                yield from visit(value, path + [key.value])
        elif isinstance(node, yaml.SequenceNode) and node.value and any(isinstance(n, (yaml.MappingNode, yaml.SequenceNode)) for n in node.value):
            for index, value in enumerate(node.value):
                yield from visit(value, path + [index])
        else:
            yield path, node
    yield from visit(yaml.compose(text), [])


def at(value, path):
    for key in path:
        value = value[key]
    return value


def discover(root):
    result = {}
    for file in YAML_FILES:
        text = (root / file).read_text()
        loaded = yaml.safe_load(text)
        for path, node in yaml_nodes(text):
            result[identity(file, path)] = {"source": file, "path": path, "adapter": "yaml", "value": at(loaded, path), "line": node.start_mark.line + 1}
    code_files = sorted(p.relative_to(root).as_posix() for directory in ["cmd", "internal"] for p in (root / directory).rglob("*.go") if not p.name.endswith("_test.go"))
    for file in code_files:
        text = (root / file).read_text()
        in_const = False
        for number, line in enumerate(text.splitlines(), 1):
            if re.match(r"^const \($", line):
                in_const = True
                continue
            if in_const and line == ")":
                in_const = False
                continue
            match = re.match(r"^\s*(?:const\s+)?(\w+)\s*=\s*(.+?)(?:\s+//.*)?$", line) if in_const or line.startswith("const ") else None
            if match:
                name, value = match.groups()
                result[identity(file, [name])] = {"source": file, "path": [name], "adapter": "constant", "value": value, "line": number}
    file = ".editorconfig"
    section = "global"
    for number, line in enumerate((root / file).read_text().splitlines(), 1):
        if line.startswith("["):
            section = line[1:-1]
        match = re.match(r"^(\w+)\s*=\s*(.+)$", line)
        if match:
            key, value = match.groups()
            result[identity(file, [section, key])] = {"source": file, "path": [section, key], "adapter": "editorconfig", "value": value, "line": number}
    for name in ["MIGRATIONS_DIR", "GOLANGCI_LINT_VERSION", "MIGRATE_VERSION"]:
        text = (root / "Makefile").read_text()
        match = re.search(rf"^{name} := (.+)$", text, re.M)
        result[identity("Makefile", [name])] = {"source": "Makefile", "path": [name], "adapter": "readonly", "value": match.group(1), "line": text[:match.start()].count("\n") + 1}
    text = (root / "go.mod").read_text()
    result["go.version"] = {"source": "go.mod", "path": ["go"], "adapter": "readonly", "value": re.search(r"^go (.+)$", text, re.M).group(1), "line": 3}
    result["go.dependencies"] = {"source": "go.mod", "path": ["require"], "adapter": "readonly", "value": [list(pair) for pair in re.findall(r"^\s+(\S+) (v\S+)", text, re.M)], "line": 5}
    for file in ["api/openapi.yaml", "db/migrations/000001_create_users.up.sql", "db/migrations/000001_create_users.down.sql", ".env.example", "requirements-setup.txt"]:
        result[identity(file, ["content"])] = {"source": file, "path": ["content"], "adapter": "readonly", "value": (root / file).read_text(), "line": 1}
    return result


def render(root, desired):
    """値が変わった箇所だけを置換し、未変更の設定・コメントを維持する。"""
    current = discover(root)
    edits = {}
    for key, value in desired.items():
        item = current[key]
        if value == item["value"]:
            continue
        file, path, adapter = item["source"], item["path"], item["adapter"]
        text = (root / file).read_text()
        if adapter == "yaml":
            node = next(node for actual, node in yaml_nodes(text) if actual == path)
            start, end = node.start_mark.index, node.end_mark.index
            replacement = json.dumps(value, ensure_ascii=False)
            if isinstance(node, (yaml.SequenceNode, yaml.MappingNode)) and node.end_mark.column < node.start_mark.column:
                replacement += "\n" + " " * node.end_mark.column
        elif adapter == "constant":
            match = re.search(rf"(?m)^(?:const\s+|\s+){re.escape(path[0])}\s*=\s*(.+?)(?:\s+//.*)?$", text)
            start, end = match.span(1)
            replacement = value
        elif adapter == "editorconfig":
            lines = text.splitlines(keepends=True)
            offset = sum(len(s) for s in lines[:item["line"] - 1])
            match = re.search(r"=\s*(.*?)(?:\n)?$", lines[item["line"] - 1])
            start, end = offset + match.start(1), offset + match.end(1)
            replacement = value
        else:
            raise ValueError(f"{key}は初期設定では変更できません")
        edits.setdefault(file, []).append((start, end, replacement))
    result = {}
    for file, operations in edits.items():
        text = (root / file).read_text()
        for start, end, replacement in sorted(operations, reverse=True):
            text = text[:start] + replacement + text[end:]
        if file in YAML_FILES:
            yaml.safe_load(text)
        result[file] = text.encode()
    return result
