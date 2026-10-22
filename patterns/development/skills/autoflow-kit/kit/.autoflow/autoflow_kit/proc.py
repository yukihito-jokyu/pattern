"""外部コマンド（検査コマンドと git）を起動し、出力を受け取る。外部コマンドと環境変数はここだけで扱う。

git への書き込み（ブランチの作成、index への追加、コミット）は、決まった関数だけで行う（OPS-05）。
"""

from __future__ import annotations

import os
import signal
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from autoflow_kit.errors import CommandError

TAIL_LINES = 40
TIMEOUT_EXIT = 124


@dataclass(frozen=True)
class Result:
    """検査コマンドの結果。output は標準出力と標準エラーをつないだもの。"""

    exit_code: int
    output: str
    timed_out: bool

    @property
    def tail(self) -> str:
        return "\n".join(self.output.rstrip().splitlines()[-TAIL_LINES:])


def shell(command: str, directory: Path, timeout_sec: int) -> Result:
    """検査コマンドをシェルで実行する。CI=1 を渡し、時間の上限を超えたら子のプロセスもまとめて止める。"""
    environment = dict(os.environ)
    environment["CI"] = "1"
    with subprocess.Popen(
        command,
        cwd=directory,
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=environment,
        start_new_session=True,
    ) as child:
        try:
            output, _ = child.communicate(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            output, _ = child.communicate()
            text = output.decode("utf-8", "replace") + f"\n[timeout] {timeout_sec} 秒で打ち切りました\n"
            return Result(TIMEOUT_EXIT, text, True)
    return Result(child.returncode, output.decode("utf-8", "replace"), False)


def _git(directory: Path, args: Sequence[str], *, stdin: str = "") -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=directory,
            input=stdin.encode("utf-8"),
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CommandError("git が見つかりません。git を入れてください") from exc
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", "replace").strip()
        raise CommandError(f"git {' '.join(args)} が失敗しました（{directory}）: {message}")
    return completed.stdout.decode("utf-8", "replace")


def git_toplevel(directory: Path) -> Path:
    return Path(_git(directory, ["rev-parse", "--show-toplevel"]).strip()).resolve()


def git_branch(directory: Path) -> str:
    return _git(directory, ["rev-parse", "--abbrev-ref", "HEAD"]).strip()


def git_head(directory: Path) -> str:
    return _git(directory, ["rev-parse", "HEAD"]).strip()


def git_status(directory: Path) -> tuple[str, ...]:
    """未コミットの変更と未追跡のファイル（.gitignore を反映）。きれいなら空。"""
    lines = _git(directory, ["status", "--porcelain", "--untracked-files=all"]).splitlines()
    return tuple(line for line in lines if line.strip())


def git_is_ignored(directory: Path, relative: str) -> bool:
    try:
        _git(directory, ["check-ignore", "-q", "--no-index", relative])
    except CommandError:
        return False
    return True


def git_user(directory: Path) -> str:
    """承認した人の記録に使う git の user.email。設定が無ければ空。"""
    try:
        return _git(directory, ["config", "user.email"]).strip()
    except CommandError:
        return ""


def git_stage_all(directory: Path) -> None:
    _git(directory, ["add", "-A"])


def git_write_tree(directory: Path) -> str:
    return _git(directory, ["write-tree"]).strip()


def git_diff_names(directory: Path, base: str, tree: str) -> tuple[str, ...]:
    names = _git(directory, ["diff", "--name-only", "--no-renames", "-z", base, tree])
    return tuple(sorted(name for name in names.split("\0") if name))


def git_numstat(directory: Path, base: str, tree: str) -> tuple[tuple[str, int, int], ...]:
    """(パス, 足した行, 消した行)。バイナリのファイルは行を 0 と数える。"""
    found = []
    for line in _git(directory, ["diff", "--numstat", "--no-renames", base, tree]).splitlines():
        added, deleted, path = line.split("\t", 2)
        found.append((path, int(added) if added.isdigit() else 0, int(deleted) if deleted.isdigit() else 0))
    return tuple(found)


def git_diff(directory: Path, base: str, tree: str) -> str:
    return _git(directory, ["diff", "--no-color", "--no-ext-diff", "--no-renames", base, tree])


def git_switch_new(directory: Path, branch: str) -> None:
    _git(directory, ["switch", "-c", branch])


def git_commit(directory: Path, message: str) -> str:
    """index の内容を、利用者の git の設定のままコミットし、コミットの id を返す。"""
    _git(directory, ["commit", "-q", "-F", "-"], stdin=message)
    return git_head(directory)
