"""テストで共有する偽物とデータの作り方。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import run_report
from gha_kit import proc
from gha_kit.proc import Result

EMPTY_OUTPUTS = {
    "yamllint": Result(0, "", ""),
    "actionlint": Result(0, "[]", ""),
    "shellcheck": Result(0, '{"comments": []}', ""),
    "zizmor": Result(0, "[]", ""),
}


class FakeApi:
    """URL ごとに決めた応答を返す REST API の偽物。呼ばれた (method, url, token, body) を calls に残す。"""

    def __init__(self, responses: Mapping[str, object], fail: Mapping[str, int] | None = None) -> None:
        self.responses = dict(responses)
        self.fail = dict(fail or {})
        self.calls: list[tuple[str, str, str, object | None]] = []

    def __call__(self, method: str, url: str, token: str, body: object | None) -> object:
        self.calls.append((method, url, token, body))
        if url in self.fail:
            raise run_report.ApiError(self.fail[url], url)
        if method == "GET":
            return self.responses.get(url, [])
        return {}


def job_payload(name: str, created: str, started: str, completed: str) -> dict[str, object]:
    """REST API のジョブ1件。ステップは1つで、ジョブと同じ時間がかかったものにする。"""
    return {
        "name": name,
        "status": "completed",
        "conclusion": "success",
        "html_url": f"https://example.test/{name}",
        "created_at": created,
        "started_at": started,
        "completed_at": completed,
        "steps": [
            {"number": 1, "name": "Run", "conclusion": "success", "started_at": started, "completed_at": completed}
        ],
    }


class FakeRunner:
    """外部の検査ツールの偽物。ツールの名前ごとに決めた出力を返し、引数を calls、場所を places に残す。

    出力を列で渡すと、呼ばれるたびに先頭から1つずつ返す（最後の1つは何度でも返す）。
    """

    def __init__(self, outputs: Mapping[str, Result | list[Result]] | None = None) -> None:
        merged = {**EMPTY_OUTPUTS, **(outputs or {})}
        self.outputs = {name: list(value) if isinstance(value, list) else [value] for name, value in merged.items()}
        self.calls: list[list[str]] = []
        self.places: list[tuple[Path, Path | None]] = []

    def __call__(self, args: Sequence[str], cwd: Path, extra_path: Path | None) -> Result:
        self.calls.append(list(args))
        self.places.append((cwd, extra_path))
        name = args[2] if list(args[1:2]) == ["-m"] else Path(args[0]).name
        queue = self.outputs[name]
        return queue.pop(0) if len(queue) > 1 else queue[0]


def write(root: Path, rel: str, text: str) -> None:
    """root の下に rel のファイルを書く（ディレクトリも作る）。"""
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


def git(root: Path, *args: str) -> None:
    """テスト用のリポジトリで git を動かす。コミットの作者は固定する。"""
    result = proc.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.test", *args], root)
    if result.code != 0:
        raise AssertionError(result.stderr)
