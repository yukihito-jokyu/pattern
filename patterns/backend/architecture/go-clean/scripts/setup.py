"""Goパターンの初期設定。PyYAMLで設定を照合し、DBや外部サービスは操作しない。"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import subprocess

from settings_inventory import discover, render
from urllib.parse import urlsplit, unquote

LEVELS = {"important": 0, "normal": 1, "advanced": 2}
ROOT = Path(__file__).resolve().parent.parent
ENV_KEYS = {"APP_ADDR", "DB_PORT", "DATABASE_URL", "LOG_LEVEL", "API_BASE_URL"}


def catalog(root):
    entries = json.loads((root / "setup/settings.catalog.json").read_text())
    config = (root / "internal/infra/config/config.go").read_text()
    found_env = set(re.findall(r'(?:getenv|os.Get?env)\("([A-Z_]+)"', config))
    found_env |= set(re.findall(r'os.environ.get\("([A-Z_]+)"', (root / "scripts/verify-api.py").read_text()))
    if found_env | {"DB_PORT"} != ENV_KEYS:
        raise ValueError("環境変数と設定台帳の項目が一致しません")
    expected = set(discover(root)) | ENV_KEYS | {"module"}
    coverage = json.loads((root / "setup/coverage.json").read_text())
    if {e["key"] for e in entries} != expected or len(entries) != len(expected) or set(coverage["keys"]) != expected:
        raise ValueError("設定台帳の項目が不足または重複しています")
    for entry in entries:
        if entry["importance"] not in LEVELS or not entry["importanceReason"] or not entry.get("meaning") or "editable" not in entry:
            raise ValueError("設定台帳の重要度・分類理由が不正です")
    return entries


def env_text(root):
    path = root / ".env"
    if path.is_symlink():
        raise ValueError(".envにシンボリックリンクは使えません")
    return (path if path.exists() else root / ".env.example").read_text()


def read_settings(root):
    module = re.search(r"^module (\S+)$", (root / "go.mod").read_text(), re.M)
    if not module:
        raise ValueError("go.modのmoduleを読めません")
    settings = dict.fromkeys(ENV_KEYS)
    for line in env_text(root).splitlines():
        match = re.match(r"^(" + "|".join(sorted(ENV_KEYS)) + r")=(.*)$", line)
        if match:
            key, value = match.groups()
            if settings[key] is not None:
                raise ValueError(f".envの{key}が重複しています")
            settings[key] = value
        elif re.match(r"^\s*(?:export\s+)?(?:APP_ADDR|DB_PORT|DATABASE_URL|LOG_LEVEL|API_BASE_URL)\b", line):
            raise ValueError(".envの対象設定は引用符なしのKEY=value形式にしてください")
    return {"module": module.group(1), **settings, **{key: item["value"] for key, item in discover(root).items()}}


def module_files(root, module):
    result = {}
    for directory, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {".git", "bin", "__pycache__", ".venv"}]
        if Path(directory) == root:
            dirs[:] = [d for d in dirs if d in {"internal", "cmd", "docs", ".claude", ".agents", ".vscode"}]
        for name in files:
            path = Path(directory) / name
            if path.suffix not in {".go", ".mod", ".md", ".yaml", ".yml", ".json"}:
                continue
            if Path(directory) == root and name not in {"go.mod", "AGENTS.md", "CLAUDE.md", "README.md", "CONTRIBUTING.md", ".golangci.yml"}:
                continue
            if path.is_symlink():
                raise ValueError("設定対象にシンボリックリンクは使えません")
            if module in path.read_text():
                result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def snapshot(root):
    settings = read_settings(root)
    files = module_files(root, settings["module"])
    sources = {item["source"] for item in discover(root).values()}
    for name in sorted(sources | {".env", ".env.example", "setup/settings.catalog.json", "setup/coverage.json", "go.mod", "internal/infra/config/config.go", "internal/infra/logger/logger.go", "scripts/verify-api.py"}):
        path = root / name
        if path.is_symlink():
            raise ValueError("設定対象にシンボリックリンクは使えません")
        files[name] = path.read_bytes() if path.exists() else None
    return {name: hashlib.sha256(value).hexdigest() if value is not None else None
            for name, value in sorted(files.items())}


def init(root, level, output):
    settings = read_settings(root)
    answer = {"version": 2, "questionLevel": level, "databaseTarget": "unanswered", "baseline": settings,
              "snapshot": snapshot(root), "settings": settings.copy(), "reviews": {}}
    for entry in catalog(root):
        key = entry["key"]
        status = "unanswered" if entry["editable"] and LEVELS[entry["importance"]] <= LEVELS[level] else "retained"
        answer["reviews"][key] = {"status": status, "value": settings[key]}
    with open(output, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
        json.dump(answer, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def validate_values(settings):
    if not ENV_KEYS | {"module"} <= set(settings):
        raise ValueError("settingsの項目が不足または未知のキーがあります")
    module = settings["module"]
    if not isinstance(module, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]*(?:/[A-Za-z0-9._~-]+)+", module):
        raise ValueError("moduleはexample.org/team/appのようなモジュールパスにしてください")
    if any(part in {".", ".."} for part in module.split("/")):
        raise ValueError("moduleに相対パスは使えません")
    for key in ENV_KEYS:
        value = settings[key]
        if value in {None, ""} and key != "DATABASE_URL":
            continue
        if not isinstance(value, str) or not value or not re.fullmatch(r"[A-Za-z0-9:/@?=&%._~+\[\],-]+", value):
            raise ValueError(f"{key}は空でない値を指定してください。空白・引用符・シェル展開文字は使えません")
    if settings["DB_PORT"] not in {None, ""}:
        port = settings["DB_PORT"]
        if not port.isascii() or not port.isdigit() or not 1 <= int(port) <= 65535:
            raise ValueError("DB_PORTは1〜65535の数字です")
    addr = settings["APP_ADDR"]
    if addr not in {None, ""}:
        match = re.fullmatch(r"(?:[A-Za-z0-9.-]*|\[[0-9A-Fa-f:]+\]):([0-9]+)", addr)
        if not match or not 1 <= int(match.group(1)) <= 65535:
            raise ValueError("APP_ADDRはhost:portまたは:port形式で指定してください")
    if settings["LOG_LEVEL"] not in {None, "", "debug", "info", "warn", "error"}:
        raise ValueError("LOG_LEVELはdebug/info/warn/errorです")
    if settings.get("API_BASE_URL"):
        api = urlsplit(settings["API_BASE_URL"])
        if api.scheme not in {"http", "https"} or not api.hostname or api.username or api.password:
            raise ValueError("API_BASE_URLは資格情報を含まないHTTP(S) URLです")
    url = urlsplit(settings["DATABASE_URL"])
    if url.scheme not in {"postgres", "postgresql"} or not url.hostname or url.path in {"", "/"}:
        raise ValueError("DATABASE_URLはDB名を含むPostgreSQLのURLです")
    if url.port is not None and not 1 <= url.port <= 65535:
        raise ValueError("DATABASE_URLのポートが不正です")



def validate_extended(root, settings):
    entries = {entry["key"]: entry for entry in catalog(root)}
    actual = discover(root)
    for key, item in actual.items():
        if key not in settings:
            raise ValueError("設定項目が不足しています: " + key)
        value, entry = settings[key], entries[key]
        expected = type(item["value"])
        if type(value) is not expected:
            raise ValueError(key + "の型が不正です")
        if isinstance(value, list) and value and all(isinstance(v, str) for v in item["value"]):
            if not all(isinstance(v, str) for v in value):
                raise ValueError(key + "は文字列の配列です")
        if not entry["editable"] and value != item["value"]:
            raise ValueError(key + "は初期設定では変更できません")
        if item["adapter"] == "constant" and entry["editable"]:
            name = item["path"][0]
            pattern = r"[0-9]+ \* time\.(Second|Minute|Hour)" if "Timeout" in name or name == "connMaxLifetime" else r"[0-9]+(?: << [0-9]+)?"
            if not re.fullmatch(pattern, value):
                raise ValueError(key + "は正の数値または既定値と同じ単位のGo定数式です")
            if int(value.split()[0]) == 0 and name not in {"maxIdleConns", "maxOpenConns"}:
                raise ValueError(key + "は0より大きい値にしてください")
        if item["source"] == ".editorconfig" and ("\n" in value or "\r" in value):
            raise ValueError("EditorConfigの値に改行は使えません")
        if item["source"] == "compose.yaml" and "environment" in item["path"]:
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
                raise ValueError(key + "は英数字・アンダースコア・ピリオド・ハイフンで指定してください")
    lint = ".golangci.yml::/"
    if not {"depguard", "forbidigo"} <= set(settings[lint + "linters/enable"]):
        raise ValueError("依存方向を検査するdepguard/forbidigoは無効化できません")
    if settings[lint + "linters/settings/lll/line-length"] != settings[lint + "formatters/settings/golines/max-len"]:
        raise ValueError("lllの行長とgolinesの整形幅をそろえてください")
    if settings[lint + "linters/settings/lll/tab-width"] != settings[lint + "formatters/settings/golines/tab-len"]:
        raise ValueError("lllとgolinesのタブ幅をそろえてください")
    db = "internal/infra/database/database.go::/"
    maximum, idle = int(settings[db + "maxOpenConns"]), int(settings[db + "maxIdleConns"])
    if maximum > 0 and idle > maximum:
        raise ValueError("maxIdleConnsはmaxOpenConns以下にしてください")


def validate(root, answer):
    entries = catalog(root)
    level = answer.get("questionLevel")
    if answer.get("version") != 2 or level not in LEVELS:
        raise ValueError("回答ファイルの形式または質問範囲が不正です")
    if answer.get("baseline") != read_settings(root) or answer.get("snapshot") != snapshot(root):
        raise ValueError("回答作成後に対象ファイルが変わっています。現在値から別名の回答ファイルを作り直してください")
    settings = answer["settings"]
    if answer.get("databaseTarget") not in {"local", "external"}:
        raise ValueError("databaseTargetが未回答です。同梱DB(local)か既存DB(external)かを確認してください")
    validate_values(settings)
    validate_extended(root, settings)
    if set(settings) != {e["key"] for e in entries}:
        raise ValueError("settingsと台帳の項目が一致しません")
    if answer["databaseTarget"] == "local":
        url = urlsplit(settings["DATABASE_URL"])
        compose = "compose.yaml::/services/db/"
        user = settings[compose + "environment/POSTGRES_USER"]
        password = settings[compose + "environment/POSTGRES_PASSWORD"]
        database = settings[compose + "environment/POSTGRES_DB"]
        if (url.hostname not in {"localhost", "127.0.0.1", "::1"} or
            (url.port or 5432) != int(settings["DB_PORT"] or "5432") or
            unquote(url.username or "") != user or unquote(url.password or "") != password or
            unquote(url.path.lstrip("/")) != database):
            raise ValueError("同梱DBの接続URLとComposeのポート・ユーザー・パスワード・DB名をそろえてください")
        test = settings[compose + "healthcheck/test"]
        if test != ["CMD-SHELL", f"pg_isready -U {user} -d {database}"]:
            raise ValueError("同梱DBのhealthcheck.testもユーザー・DB名に合わせてください")
    if set(answer.get("reviews", {})) != {e["key"] for e in entries}:
        raise ValueError("reviewsの項目が不足または未知のキーがあります")
    for entry in entries:
        key = entry["key"]
        review = answer["reviews"][key]
        if not entry["editable"] and settings[key] != answer["baseline"][key]:
            raise ValueError(f"{key}は初期設定では変更できません")
        if answer["databaseTarget"] == "external" and (key == "DB_PORT" or entry["source"] == "compose.yaml"):
            if settings[key] != answer["baseline"][key]:
                raise ValueError("既存DBを使う場合、同梱Composeの設定は変更しません")
            if (review.get("status") == "not-applicable" and review.get("value") == settings[key]
                    and isinstance(review.get("reason"), str) and review["reason"].strip()):
                continue
        selected = entry["editable"] and LEVELS[entry["importance"]] <= LEVELS[level]
        if review == {"status": "confirmed", "value": settings[key]}:
            continue
        if (not selected and review == {"status": "retained", "value": settings[key]}
                and settings[key] == answer["baseline"][key]):
            continue
        raise ValueError(f"{key}が未回答、確認後に変更、または範囲外で未確認の変更です")


def changes(root, answer):
    validate(root, answer)
    before, after = answer["baseline"], answer["settings"]
    updates = render(root, {key: value for key, value in after.items() if key not in ENV_KEYS | {"module"}})
    if before["module"] != after["module"]:
        for name, content in module_files(root, before["module"]).items():
            updates[name] = updates.get(name, content).replace(before["module"].encode(), after["module"].encode())
    text = env_text(root)
    for key in sorted(ENV_KEYS):
        if before[key] == after[key]:
            continue
        pattern = rf"^{key}=.*(?:\n|$)"
        line = "" if after[key] is None else f"{key}={after[key]}\n"
        if re.search(pattern, text, re.M):
            text = re.sub(pattern, lambda _: line, text, flags=re.M)
        elif line:
            text = text.rstrip("\n") + "\n" + line
    if not (root / ".env").exists() or text != (root / ".env").read_text():
        updates[".env"] = text.encode()
    return updates


def apply(root, answer):
    updates = changes(root, answer)
    originals = {name: (root / name).read_bytes() if (root / name).exists() else None for name in updates}
    modes = {name: (root / name).stat().st_mode & 0o777 if (root / name).exists() else 0o600 for name in updates}
    written = []
    try:
        for name, data in updates.items():
            path = root / name
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                try:
                    stream.write(data)
                    stream.flush()
                    os.chmod(temporary, modes[name])
                    os.replace(temporary, path)
                finally:
                    temporary.unlink(missing_ok=True)
            written.append(name)
        for name in updates:
            if name.endswith(".go"):
                subprocess.run(["gofmt", "-w", str(root / name)], check=True, capture_output=True)
    except Exception:
        for name in reversed(written):
            path = root / name
            if originals[name] is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(originals[name])
        raise
    return sorted(updates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "list", "validate", "plan", "apply", "check"])
    parser.add_argument("--level", choices=LEVELS)
    parser.add_argument("--out", default="setup-answers.json")
    parser.add_argument("--answers")
    parser.add_argument("--group", choices=["runtime", "database", "server", "lint", "editor", "contract", "verification"])
    args = parser.parse_args()
    if args.command == "init":
        init(ROOT, args.level or "important", args.out)
        print(json.dumps({"created": args.out}, ensure_ascii=False))
        return
    answer = json.loads(Path(args.answers).read_text()) if args.answers else None
    if args.command in {"validate", "plan", "apply"}:
        if answer is None:
            parser.error("--answersが必要です")
        validate(ROOT, answer)
        if args.command == "validate":
            result = {"ok": True}
        elif args.command == "apply":
            result = {"changed": apply(ROOT, answer)}
        else:
            result = {"files": sorted(changes(ROOT, answer)), "settings": [
                {"key": key, "before": "[非表示]" if key in {e["key"] for e in catalog(ROOT) if e.get("sensitive")} else answer["baseline"][key],
                 "after": "[非表示]" if key in {e["key"] for e in catalog(ROOT) if e.get("sensitive")} else value}
                for key, value in answer["settings"].items() if value != answer["baseline"][key]],
                "retained": [key for key, review in answer["reviews"].items() if review["status"] == "retained"]}
    elif args.command == "list":
        level = args.level or (answer["questionLevel"] if answer else "important")
        settings = answer["settings"] if answer else read_settings(ROOT)
        result = [{**{k: v for k, v in entry.items() if k != "sample"}, "current": "[非表示]" if entry.get("sensitive") else settings[entry["key"]]}
                  for entry in catalog(ROOT) if LEVELS[entry["importance"]] <= LEVELS[level] and (not args.group or entry["group"] == args.group)
                  and not (answer and answer.get("databaseTarget") == "external" and entry["editable"]
                           and (entry["key"] == "DB_PORT" or entry["source"] == "compose.yaml"))]
    else:
        catalog(ROOT)
        validate_values(read_settings(ROOT))
        validate_extended(ROOT, read_settings(ROOT))
        result = {"ok": True, "catalogItems": len(catalog(ROOT)), "envSource": ".env" if (ROOT / ".env").exists() else ".env.example"}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f"setup: {error}", file=sys.stderr)
        sys.exit(1)
