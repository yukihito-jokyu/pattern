"""ワークフローの実行の全ジョブ・全ステップの所要時間を、PR とジョブサマリーに書き、needs の結果で合否を決める。

run-report アクション（同じディレクトリの action.yml）から、GitHub ホストのランナーの python3 で呼ばれる。
標準ライブラリだけを使う。入力は環境変数で受け取る。

  GH_TOKEN      REST API のトークン。ジョブの取得に actions: read、PR へのコメントに pull-requests: write が要る
  NEEDS         呼び出し元のジョブの toJSON(needs)。合否の判定に使う
  GITHUB_*      ランナーが設定する既定の環境変数（リポジトリ、実行の ID、イベントなど）

所要時間の取得とコメントは失敗しても警告に留め、合否は needs の結果だけで決める。
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

PASSING = ("success", "skipped")
PER_PAGE = 100
COMMENT_LIMIT = 60000  # PR のコメントの上限（65536 文字）より小さくする。UTF-8 のバイト数で測る
SUMMARY_LIMIT = 1000000  # ジョブサマリーの上限（1 MiB）より小さくする。UTF-8 のバイト数で測る
SLOWEST = 5
BAR_WIDTH = 10
API_VERSION = "2026-03-10"
LABELS = {
    "success": "✅ 成功",
    "failure": "❌ 失敗",
    "cancelled": "⏹️ 中止",
    "skipped": "⏭️ スキップ",
    "timed_out": "⌛ 時間切れ",
    "action_required": "✋ 承認待ち",
    "neutral": "➖ 中立",
    "stale": "➖ 古い",
}

Transport = Callable[[str, str, str, "object | None"], object]


class ApiError(Exception):
    """REST API が 2xx 以外を返した。"""

    def __init__(self, status: int, url: str) -> None:
        super().__init__(f"HTTP {status}: {url}")
        self.status = status


@dataclass(frozen=True)
class Step:
    number: int
    name: str
    conclusion: str
    seconds: int


@dataclass(frozen=True)
class Job:
    name: str
    url: str
    conclusion: str
    offset: int  # 最初のジョブが作られてから、このジョブが始まるまでの秒数
    queued: int
    seconds: int
    steps: tuple[Step, ...]


@dataclass(frozen=True)
class Run:
    workflow: str
    url: str
    number: str
    attempt: str


def http_transport(method: str, url: str, token: str, body: object | None) -> object:
    """REST API を1回呼び、JSON の本文を返す。2xx 以外は ApiError にする。"""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("X-GitHub-Api-Version", API_VERSION)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise ApiError(exc.code, url) from exc
    return json.loads(text) if text else None


def seconds_between(start: str | None, end: str | None) -> int:
    if not start or not end:
        return 0
    return max(0, int((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()))


def list_jobs(transport: Transport, token: str, base: str) -> list[dict[str, object]]:
    """1回の試行の全ジョブを、ページを辿って返す。"""
    jobs: list[dict[str, object]] = []
    page = 1
    while True:
        payload = transport("GET", f"{base}?per_page={PER_PAGE}&page={page}", token, None)
        batch = payload.get("jobs", []) if isinstance(payload, dict) else []
        jobs += [job for job in batch if isinstance(job, dict)]
        if len(batch) < PER_PAGE:
            return jobs
        page += 1


def to_jobs(raw: Sequence[Mapping[str, object]]) -> list[Job]:
    """終わったジョブだけを Job にする（実行中のジョブには、この報告をしているジョブ自身が含まれる）。"""
    done = [job for job in raw if job.get("status") == "completed"]
    origin = min((str(job.get("created_at") or "") for job in done), default="")
    jobs = []
    for job in done:
        steps = tuple(
            Step(
                number=int(str(step.get("number", 0))),
                name=str(step.get("name", "")),
                conclusion=str(step.get("conclusion") or ""),
                seconds=seconds_between(_text(step, "started_at"), _text(step, "completed_at")),
            )
            for step in _dicts(job.get("steps"))
        )
        jobs.append(
            Job(
                name=str(job.get("name", "")),
                url=str(job.get("html_url", "")),
                conclusion=str(job.get("conclusion") or ""),
                offset=seconds_between(origin, _text(job, "started_at")),
                queued=seconds_between(_text(job, "created_at"), _text(job, "started_at")),
                seconds=seconds_between(_text(job, "started_at"), _text(job, "completed_at")),
                steps=steps,
            )
        )
    return sorted(jobs, key=lambda job: (job.offset, job.name))


def _text(mapping: Mapping[str, object], key: str) -> str | None:
    value = mapping.get(key)
    return value if isinstance(value, str) else None


def _dicts(value: object) -> list[Mapping[str, object]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}秒"
    minutes, rest = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}分{rest}秒"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}時間{minutes}分"


def label(conclusion: str) -> str:
    return LABELS.get(conclusion, conclusion or "不明")


def bar(seconds: int, longest: int) -> str:
    filled = round(BAR_WIDTH * seconds / longest) if longest else 0
    return "`" + "█" * filled + "·" * (BAR_WIDTH - filled) + "`"


def failed_needs(needs_json: str) -> list[str]:
    """needs のうち、結果が success でも skipped でもないジョブの ID を返す。"""
    needs = json.loads(needs_json or "{}")
    if not isinstance(needs, dict) or not needs:
        raise ValueError("NEEDS が空です。run-report を呼ぶジョブの needs に、ほかの全ジョブを書く")
    return sorted(
        name for name, need in needs.items() if not isinstance(need, dict) or need.get("result") not in PASSING
    )


def marker(workflow: str) -> str:
    return f"<!-- run-report:{workflow} -->"


def render(run: Run, jobs: Sequence[Job], failed: Sequence[str], with_steps: bool = True) -> str:
    verdict = (
        "✅ needs の全ジョブが成功かスキップで終わった" if not failed else f"❌ 失敗したジョブ: {', '.join(failed)}"
    )
    lines = [marker(run.workflow), f"### ⏱️ {run.workflow} の処理時間", "", verdict, ""]
    if not jobs:
        return "\n".join([*lines, "終わったジョブの記録を取得できなかった。", ""])
    elapsed = max(job.offset + job.seconds for job in jobs)
    lines += [
        f"[実行 #{run.number} の試行 {run.attempt}]({run.url})：経過 {duration(elapsed)}、"
        f"ジョブの実行の合計 {duration(sum(job.seconds for job in jobs))}、"
        f"待ちの合計 {duration(sum(job.queued for job in jobs))}",
        "",
        "| ジョブ | 結果 | 待ち | 実行 | 割合 |",
        "|---|---|---:|---:|---|",
    ]
    longest = max(job.seconds for job in jobs)
    lines += [
        f"| [{_cell(job.name)}]({job.url}) | {label(job.conclusion)} | {duration(job.queued)} | "
        f"{duration(job.seconds)} | {bar(job.seconds, longest)} |"
        for job in jobs
    ]
    lines += ["", *render_slowest(jobs), *render_timeline(jobs)]
    if with_steps:
        for job in jobs:
            lines += render_steps(job)
    return "\n".join(lines)


def render_slowest(jobs: Sequence[Job]) -> list[str]:
    steps = sorted(((step, job) for job in jobs for step in job.steps), key=lambda pair: -pair[0].seconds)[:SLOWEST]
    lines = [f"<details><summary>遅いステップ（上位 {SLOWEST} 件）</summary>", "", "| ステップ | ジョブ | 時間 |"]
    lines += ["|---|---|---:|"]
    lines += [f"| {_cell(step.name)} | {_cell(job.name)} | {duration(step.seconds)} |" for step, job in steps]
    return [*lines, "", "</details>", ""]


def render_timeline(jobs: Sequence[Job]) -> list[str]:
    lines = ["<details><summary>タイムライン</summary>", "", "```mermaid", "gantt", "    dateFormat X"]
    lines += ["    axisFormat %M:%S"]
    for index, job in enumerate(jobs, 1):
        if job.seconds == 0:
            continue
        tag = "done" if job.conclusion in PASSING else "crit"
        name = "".join(" " if char in ":#;" else char for char in job.name)
        lines.append(f"    {name} : {tag}, j{index}, {job.offset}, {job.offset + job.seconds}")
    return [*lines, "```", "", "</details>", ""]


def render_steps(job: Job) -> list[str]:
    lines = [f"<details><summary>{_cell(job.name)} のステップ（{duration(job.seconds)}）</summary>", ""]
    lines += ["| # | ステップ | 結果 | 時間 |", "|---:|---|---|---:|"]
    lines += [
        f"| {step.number} | {_cell(step.name)} | {label(step.conclusion)} | {duration(step.seconds)} |"
        for step in job.steps
    ]
    return [*lines, "", "</details>", ""]


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def fit(run: Run, jobs: Sequence[Job], failed: Sequence[str], limit: int) -> str:
    """上限を超えるなら、ステップの内訳を省いた版にする。"""
    body = render(run, jobs, failed)
    if len(body.encode("utf-8")) <= limit:
        return body
    return (
        render(run, jobs, failed, with_steps=False)
        + "ステップの内訳は、上限を超えるため省いた。各ジョブのログを見る。\n"
    )


def upsert_comment(transport: Transport, token: str, issue_api: str, body: str) -> str:
    """同じワークフローの以前の報告があれば書き換え、無ければ新しく書く。"""
    head = body.splitlines()[0]
    page = 1
    while True:
        comments = transport("GET", f"{issue_api}/comments?per_page={PER_PAGE}&page={page}", token, None)
        batch = comments if isinstance(comments, list) else []
        for comment in batch:
            if isinstance(comment, dict) and str(comment.get("body", "")).startswith(head):
                transport("PATCH", str(comment.get("url")), token, {"body": body})
                return "更新した"
        if len(batch) < PER_PAGE:
            break
        page += 1
    transport("POST", f"{issue_api}/comments", token, {"body": body})
    return "書いた"


def pull_request_number(env: Mapping[str, str]) -> int | None:
    if env.get("GITHUB_EVENT_NAME") != "pull_request" or not env.get("GITHUB_EVENT_PATH"):
        return None
    event = json.loads(Path(env["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    number = event.get("pull_request", {}).get("number") if isinstance(event, dict) else None
    return number if isinstance(number, int) else None


def collect(env: Mapping[str, str], transport: Transport) -> list[Job]:
    api = env.get("GITHUB_API_URL", "https://api.github.com")
    base = (
        f"{api}/repos/{env['GITHUB_REPOSITORY']}/actions/runs/{env['GITHUB_RUN_ID']}"
        f"/attempts/{env.get('GITHUB_RUN_ATTEMPT', '1')}/jobs"
    )
    try:
        return to_jobs(list_jobs(transport, env.get("GH_TOKEN", ""), base))
    except (ApiError, urllib.error.URLError, ValueError) as exc:
        print(f"::warning::ジョブの所要時間を取得できなかった: {exc}")
        return []


def publish(env: Mapping[str, str], transport: Transport, run: Run, jobs: Sequence[Job], failed: Sequence[str]) -> None:
    summary = env.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write(fit(run, jobs, failed, SUMMARY_LIMIT) + "\n")
    number = pull_request_number(env)
    if number is None:
        return
    api = env.get("GITHUB_API_URL", "https://api.github.com")
    issue_api = f"{api}/repos/{env['GITHUB_REPOSITORY']}/issues/{number}"
    try:
        result = upsert_comment(transport, env.get("GH_TOKEN", ""), issue_api, fit(run, jobs, failed, COMMENT_LIMIT))
        print(f"PR #{number} に処理時間の報告を{result}")
    except ApiError as exc:
        if exc.status not in (403, 404):
            raise
        print(f"::notice::PR にコメントできなかった（フォークからの PR ではトークンが読み取り専用になる）: {exc}")


def main(env: Mapping[str, str], transport: Transport = http_transport) -> int:
    try:
        failed = failed_needs(env.get("NEEDS", ""))
    except ValueError as exc:
        print(f"::error::{exc}")
        return 1
    server = env.get("GITHUB_SERVER_URL", "https://github.com")
    run = Run(
        workflow=env.get("GITHUB_WORKFLOW", ""),
        url=f"{server}/{env['GITHUB_REPOSITORY']}/actions/runs/{env['GITHUB_RUN_ID']}/attempts/"
        f"{env.get('GITHUB_RUN_ATTEMPT', '1')}",
        number=env.get("GITHUB_RUN_NUMBER", ""),
        attempt=env.get("GITHUB_RUN_ATTEMPT", "1"),
    )
    jobs = collect(env, transport)
    try:
        publish(env, transport, run, jobs, failed)
    except (ApiError, urllib.error.URLError) as exc:
        print(f"::warning::処理時間の報告を書けなかった: {exc}")
    for name in failed:
        print(f"::error::needs のジョブ {name} が成功でもスキップでもなく終わった")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(os.environ))
