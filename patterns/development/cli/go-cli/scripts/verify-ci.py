"""ZIP内の全検査、実プロセスの入出力と保存、代表的な違反の検出を確認する。"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import tempfile


def require(condition: bool, message: str) -> None:
    """期待結果と異なる場合は検証を停止する。"""
    if not condition:
        raise RuntimeError(message)


def check_cli(binary: Path, work: Path) -> None:
    """一時ディレクトリでビルド済みCLIの公開面と保存結果を確認する。"""
    data = work / "data"
    env = {**os.environ, "GOCLI_DATA_DIR": str(data)}

    def no_file_writes() -> None:
        """子プロセスのファイルサイズを制限し、保存時の書き込みを失敗させる。"""
        signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))

    def run(*args: str, code: int = 0, data_dir: Path | None = None,
            fail_save: bool = False):
        """CLIを別プロセスとして実行し、終了コードと出力先を確認する。"""
        current = {**env, "GOCLI_DATA_DIR": str(data_dir or data)}
        result = subprocess.run([str(binary), *args], env=current, text=True,
                                capture_output=True, timeout=30, check=False,
                                preexec_fn=no_file_writes if fail_save else None)
        require(result.returncode == code,
                f"{args}: exit={result.returncode}, want={code}: {result.stderr}")
        if code == 0:
            require(result.stderr == "", f"{args}: unexpected stderr: {result.stderr}")
        else:
            require(result.stdout == "", f"{args}: failure wrote to stdout")
            require(result.stderr.startswith("go-cli: "), f"{args}: missing error prefix")
        return result

    require("task" in run("--help").stdout, "root help has no task group")
    require("--json" in run("task", "add", "--help").stdout, "command help has no JSON flag")
    require(run("task", "list", "--json").stdout.strip() == '{\n  "tasks": []\n}',
            "empty list must be an array in a JSON object")
    require(not data.exists(), "help and empty list must not create a data directory")
    require(run("task", "add", "  Buy milk  ").stdout == "Added task 1: Buy milk\n",
            "text output or title trimming differs")
    added = json.loads(run("task", "add", "--json", "Read book").stdout)
    item = added["task"]
    require(set(item) == {"id", "title", "done", "created_at"}, "unexpected JSON fields")
    require(item["id"] == 2 and item["title"] == "Read book" and item["done"] is False,
            "added task differs")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", item["created_at"]) is not None,
            "timestamp must have UTC second precision")
    require(run("task", "complete", "1").stdout == "Completed task 1: Buy milk\n",
            "completion text differs")
    completed = json.loads(run("task", "complete", "1", "--json").stdout)["task"]
    require(completed["id"] == 1 and completed["done"] is True, "completion is not idempotent")
    require([t["id"] for t in json.loads(run("task", "list", "--json").stdout)["tasks"]] == [2],
            "default list must exclude completed tasks")
    all_tasks = json.loads(run("task", "list", "--all", "--json").stdout)["tasks"]
    require([t["id"] for t in all_tasks] == [1, 2], "all tasks must keep ID order")
    table = run("task", "list", "--all").stdout
    require(table.splitlines()[0].split() == ["ID", "STATUS", "TITLE"] and
            "done" in table and "Buy milk" in table and "Read book" in table,
            "text table differs")
    persisted = json.loads((data / "tasks.json").read_text())
    require(persisted == {"version": 1, "tasks": all_tasks}, "saved records differ from CLI output")
    require((data.stat().st_mode & 0o777) == 0o700 and
            ((data / "tasks.json").stat().st_mode & 0o777) == 0o600,
            "private data permissions differ")
    require(not list(data.glob(".tmp-*")), "temporary save file was left behind")
    for args in [("task", "add", ""), ("task", "add", "x" * 101),
                 ("task", "complete", "one"), ("task", "list", "--unknown"),
                 ("task", "add")]:
        result = run(*args, code=2)
        require("--help" in result.stderr, "invalid input has no help hint")
    require("task 999" in run("task", "complete", "999", code=3).stderr,
            "missing task has no ID in error")
    require(json.loads((data / "tasks.json").read_text()) == persisted,
            "failed commands changed saved data")
    broken = work / "broken"
    broken.mkdir()
    (broken / "tasks.json").write_text("{broken")
    require("load tasks" in run("task", "list", data_dir=broken, code=1).stderr,
            "corrupt data was not reported")
    blocked = work / "blocked"
    blocked.write_text("a file cannot be a data directory")
    require("load tasks" in run("task", "add", "Blocked", data_dir=blocked, code=1).stderr,
            "unusable data directory was not reported")
    save_error = work / "save-error"
    save_error.mkdir()
    (save_error / "tasks.json").write_text('{"version":1,"tasks":[]}')
    result = run("task", "add", "Cannot save", data_dir=save_error, code=1, fail_save=True)
    require("save tasks" in result.stderr, "save failure was not reported")
    require(json.loads((save_error / "tasks.json").read_text()) == {"version": 1, "tasks": []},
            "save failure changed existing data")
    require(not list(save_error.glob(".tmp-*")), "save failure left a temporary file")
    require(run("task", "add", "--", "--json", data_dir=work / "literal").stdout ==
            "Added task 1: --json\n", "-- must terminate flag parsing")
    print("CLI: 成功・JSON・永続化・終了コード0/1/2/3・入力制約・権限・--を確認", flush=True)


def main() -> None:
    """準備から順に実行し、失敗した段階で後続を停止する。"""
    root = Path(__file__).resolve().parents[1]
    for executable in ["go", "make", "python3"]:
        subprocess.run([executable, "--version" if executable != "go" else "version"],
                       cwd=root, check=True)
    subprocess.run(["make", "check"], cwd=root, check=True)
    with tempfile.TemporaryDirectory(prefix="go-cli-verify-") as directory:
        work = Path(directory)
        binary = work / "go-cli"
        subprocess.run(["go", "build", "-o", str(binary), "."], cwd=root, check=True)
        check_cli(binary, work)
    subprocess.run(["python3", ".foundation/bin/violation_probe.py", "--root", ".",
                    "--only", "DEP-01-a,STR-04-a,TOOL-03-a"], cwd=root, check=True)
    print("ZIP検証: 全検査・CLI操作・代表的な違反3件の検出に成功", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.SubprocessError, OSError, KeyError, ValueError) as error:
        print(f"ZIP検証: 失敗: {error}", file=sys.stderr)
        sys.exit(1)
