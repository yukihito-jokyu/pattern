"""一時環境を準備し、ZIP内の仕様・見本・生成手順と違反検出を確かめる。"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import venv


def run(command: list[str], root: Path, env: dict[str, str]) -> None:
    """失敗した段階で後続を停止する。"""
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=root, env=env, check=True)


def check_new_spec(root: Path, work: Path, env: dict[str, str]) -> None:
    """READMEの生成手順をコピーで実行し、生成された仕様とヘルプを照合する。"""
    project = work / "new-spec"
    shutil.copytree(root, project, ignore=shutil.ignore_patterns("__pycache__", ".venv", ".git"))
    run(["make", "new", "NAME=bookmarks"], project, env)
    for verb in ["create", "list", "view", "edit", "delete"]:
        run(["make", "command", "NAME=bookmarks", "NOUN=bookmark", f"VERB={verb}"], project, env)
    run(["make", "field", "NAME=bookmarks", "NOUN=bookmark", "FIELD=url", "TYPE=string"], project, env)
    run(["make", "fix"], project, env)
    run(["make", "check"], project, env)
    spec = json.loads((project / "specs/bookmarks/cli.json").read_text())
    expected = [["bookmark", verb] for verb in ["create", "delete", "edit", "list", "view"]]
    if ([c["path"] for c in spec["commands"]] != expected or spec["version"] != "1.0.0"
            or spec["env"][0]["name"] != "BOOKMARKS_DATA_DIR"):
        raise RuntimeError("生成したコマンド・版・環境変数がREADMEの期待結果と異なる")
    create = next(c for c in spec["commands"] if c["path"] == ["bookmark", "create"])
    url = next(o for o in create["options"] if o["name"] == "url")
    if create["args"] != [] or not url["required"] or "--url" not in (project / "specs/bookmarks/cli.md").read_text():
        raise RuntimeError("生成したcreateの引数・必須URL・ヘルプが期待結果と異なる")
    print("新規仕様: 5操作・必須URL・版・環境変数・ヘルプを確認", flush=True)


def main() -> None:
    """環境準備、全検査、適合テスト、違反検出、新規仕様生成の順で確認する。"""
    if sys.platform not in ("darwin", "linux"):
        raise RuntimeError("ZIPの検証はmacOS/Linuxに対応する")
    if sys.version_info[:2] != (3, 14):
        raise RuntimeError("python3 .ci/verify.pyはPython 3.14で起動する")
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="cli-design-verify-") as directory:
        work = Path(directory)
        environment = work / "environment"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / "bin/python"
        env = {**os.environ, "PATH": str(environment / "bin") + os.pathsep + os.environ.get("PATH", ""),
               "UV_CACHE_DIR": str(work / "uv-cache"), "UV_PYTHON": sys.executable,
               "PIP_CACHE_DIR": str(work / "pip-cache")}
        run([str(python), "-m", "pip", "--disable-pip-version-check", "--no-input",
             "install", "uv==0.13.3"], root, env)
        run(["uv", "--version"], root, env)
        run(["make", "--version"], root, env)
        run(["make", "check"], root, env)
        for name, implementation in [("notes", "notes_impl.py"), ("count-words", "count_words_impl.py")]:
            # MakefileがCMDをシェルで起動するため、空白のある展開先も引用する。
            command = shlex.join([sys.executable, str(root / "tools/clispec/tests/fixtures" / implementation)])
            run(["make", "conform", f"SPEC=specs/{name}/cli.json", f"CMD={command}"], root, env)
        run([sys.executable, ".foundation/bin/violation_probe.py", "--root", ".", "--only",
             "STR-01-d,STR-04-a,NAM-04-a,OPS-05-a"], root, env)
        check_new_spec(root, work, env)
    print("ZIP検証: 全検査・見本2種類・違反4件・新規仕様生成に成功", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.SubprocessError, OSError, KeyError, ValueError, StopIteration) as error:
        print(f"ZIP検証: 失敗: {error}", file=sys.stderr)
        sys.exit(1)
