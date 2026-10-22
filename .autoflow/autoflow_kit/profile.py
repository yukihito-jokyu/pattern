"""プロファイル（.autoflow/profile.json）の型・既定値・検証と、承認の記録の型を定義する。

プロファイルは H0 で人が承認する。形を変えたら SCHEMA_VERSION を上げる（PROC-06）。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from autoflow_kit import shape

SCHEMA_VERSION = 1
COMMAND_ID = r"[a-z0-9]+(-[a-z0-9]+)*"
DEFAULT_TIMEOUT_SEC = 600
MAX_TIMEOUT_SEC = 3600
MAX_LIMIT = 100_000


@dataclass(frozen=True)
class Command:
    id: str
    run: str
    timeout_sec: int


@dataclass(frozen=True)
class Verify:
    commands: tuple[Command, ...]


@dataclass(frozen=True)
class Paths:
    tests: tuple[str, ...]


@dataclass(frozen=True)
class Risk:
    always_human: tuple[str, ...]
    high: tuple[str, ...]
    low: tuple[str, ...]


@dataclass(frozen=True)
class Review:
    guide_files: tuple[str, ...]
    skip: tuple[str, ...]


@dataclass(frozen=True)
class Limits:
    fix_attempts: int
    review_rounds: int
    max_scope_files: int
    large_diff_lines: int
    huge_diff_lines: int


@dataclass(frozen=True)
class Commit:
    trailers: tuple[str, ...]


@dataclass(frozen=True)
class Profile:
    schema_version: int
    verify: Verify
    paths: Paths
    risk: Risk
    review: Review
    limits: Limits
    commit: Commit


@dataclass(frozen=True)
class Approval:
    """profile-approval.json。承認したプロファイルの sha256 と、人の回答の原文。"""

    sha256: str
    who: str
    answer: str
    at: str


@dataclass(frozen=True)
class Field:
    """profile-schema.md に載せる項目の説明。"""

    key: str
    kind: str
    meaning: str


DEFAULT_TESTS = (
    "tests/**",
    "test/**",
    "**/__tests__/**",
    "**/*_test.go",
    "**/*.test.*",
    "**/*.spec.*",
    "**/test_*.py",
)
DEFAULT_RISK = Risk(
    always_human=(
        ".github/workflows/**",
        ".gitlab-ci.yml",
        ".circleci/**",
        "Jenkinsfile",
        "**/auth/**",
        "**/billing/**",
        "**/payment*/**",
        "**/migrations/**",
        "**/.env*",
        "**/*secret*",
        "**/*.pem",
        "**/*.key",
        ".autoflow/**",
        ".claude/**",
        "**/CLAUDE.md",
        "**/AGENTS.md",
        "**/REVIEW.md",
    ),
    high=(
        "**/package.json",
        "**/package-lock.json",
        "**/pnpm-lock.yaml",
        "**/yarn.lock",
        "**/go.mod",
        "**/go.sum",
        "**/pyproject.toml",
        "**/requirements*.txt",
        "**/poetry.lock",
        "**/uv.lock",
        "**/Cargo.toml",
        "**/Cargo.lock",
        "**/Gemfile*",
        "**/Dockerfile*",
        "**/docker-compose*.yml",
        "**/*.tf",
    ),
    low=("docs/**", "**/*.md"),
)
DEFAULT_REVIEW = Review(
    guide_files=(),
    skip=("**/*.lock", "**/package-lock.json", "**/pnpm-lock.yaml", "**/dist/**", "**/vendor/**", "**/*.min.js"),
)
DEFAULT_LIMITS = Limits(fix_attempts=3, review_rounds=3, max_scope_files=20, large_diff_lines=400, huge_diff_lines=1000)
FIELDS = (
    Field("schema_version", "整数", f"プロファイルの形の版。今は {SCHEMA_VERSION}"),
    Field("verify.commands[].id", "文字列", "検査の名前（kebab-case）。証拠のログのファイル名になる"),
    Field("verify.commands[].run", "文字列", "リポジトリのルートで実行するシェルのコマンド。CI=1 を付けて実行する"),
    Field("verify.commands[].timeout_sec", "整数", f"時間の上限（秒、1〜{MAX_TIMEOUT_SEC}）"),
    Field("paths.tests", "glob の配列", "テストのファイル。不具合の修正で、最初に再現のテストだけを書く範囲"),
    Field("risk.always_human", "glob の配列", "常に人が差分を読むパス。計画で触ると H1、変更に含むと H3 で全文を読む"),
    Field("risk.high", "glob の配列", "変更に含むとリスクの段を high にするパス"),
    Field("risk.low", "glob の配列", "変更がこれとテストだけなら、リスクの段を low にするパス"),
    Field("review.guide_files", "パスの配列", "探索役と検証役に渡すレビューの指示（開始時の版を写す）"),
    Field("review.skip", "glob の配列", "レビューで指摘しないパス（生成物、lockfile）"),
    Field("limits.fix_attempts", "整数", "検査の失敗がこの回数続いたら H2"),
    Field("limits.review_rounds", "整数", "Important が残るレビューがこの回数続いたら H2"),
    Field("limits.max_scope_files", "整数", "計画の範囲がこのファイル数を超えたら H1"),
    Field("limits.large_diff_lines", "整数", "差分の行数がこれを超えたら、リスクの段を少なくとも medium にする"),
    Field("limits.huge_diff_lines", "整数", "差分の行数がこれを超えたら、リスクの段を high にする"),
    Field("commit.trailers", "文字列の配列", "コミットの文の最後に足す行（Co-Authored-By など）"),
)


def make_profile(commands: tuple[Command, ...], guide_files: tuple[str, ...]) -> Profile:
    """setup が検出した値と既定値から、承認の前の案を作る。"""
    return Profile(
        schema_version=SCHEMA_VERSION,
        verify=Verify(commands),
        paths=Paths(DEFAULT_TESTS),
        risk=DEFAULT_RISK,
        review=Review(guide_files, DEFAULT_REVIEW.skip),
        limits=DEFAULT_LIMITS,
        commit=Commit(()),
    )


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse(value: object, problems: list[str]) -> Profile:
    data = shape.as_object(value, "", problems)
    shape.unknown_keys(data, ("schema_version", "verify", "paths", "risk", "review", "limits", "commit"), "", problems)
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        problems.append(f"schema_version が {version!r} です。今の版は {SCHEMA_VERSION}。setup-new --force で作り直す")
    return Profile(
        schema_version=SCHEMA_VERSION,
        verify=_parse_verify(shape.as_object(data.get("verify"), "verify", problems), problems),
        paths=Paths(_globs(data, "paths", ("tests",), problems)[0]),
        risk=Risk(*_globs(data, "risk", ("always_human", "high", "low"), problems)),
        review=Review(*_globs(data, "review", ("guide_files", "skip"), problems)),
        limits=_parse_limits(shape.as_object(data.get("limits"), "limits", problems), problems),
        commit=Commit(*_globs(data, "commit", ("trailers",), problems)),
    )


def _parse_verify(data: dict[str, object], problems: list[str]) -> Verify:
    shape.unknown_keys(data, ("commands",), "verify", problems)
    commands = []
    for where, item in shape.objects(data, "commands", "verify", problems):
        shape.unknown_keys(item, ("id", "run", "timeout_sec"), where, problems)
        commands.append(
            Command(
                id=shape.text(item, "id", where, problems, pattern=COMMAND_ID),
                run=shape.filled(item, "run", where, problems),
                timeout_sec=shape.integer(item, "timeout_sec", where, problems, bounds=(1, MAX_TIMEOUT_SEC)),
            )
        )
    if not commands:
        problems.append("verify.commands が空です。検査コマンドが無いと証拠を作れない。1つ以上書く")
    for repeated in shape.duplicates(command.id for command in commands):
        problems.append(f"verify.commands の id {repeated!r} が重なっています")
    return Verify(tuple(commands))


def _globs(
    data: dict[str, object], key: str, names: tuple[str, ...], problems: list[str]
) -> tuple[tuple[str, ...], ...]:
    section = shape.as_object(data.get(key), key, problems)
    shape.unknown_keys(section, names, key, problems)
    return tuple(shape.texts(section, name, key, problems) for name in names)


def _parse_limits(data: dict[str, object], problems: list[str]) -> Limits:
    keys = ("fix_attempts", "review_rounds", "max_scope_files", "large_diff_lines", "huge_diff_lines")
    shape.unknown_keys(data, keys, "limits", problems)
    values = [shape.integer(data, key, "limits", problems, bounds=(1, MAX_LIMIT)) for key in keys]
    limits = Limits(*values)
    if limits.large_diff_lines > limits.huge_diff_lines:
        problems.append("limits.large_diff_lines は limits.huge_diff_lines 以下にする")
    return limits


def parse_approval(value: object, problems: list[str]) -> Approval:
    data = shape.as_object(value, "", problems)
    shape.unknown_keys(data, ("sha256", "who", "answer", "at"), "", problems)
    return Approval(
        sha256=shape.text(data, "sha256", "", problems, pattern=r"[0-9a-f]{64}"),
        who=shape.text(data, "who", "", problems),
        answer=shape.filled(data, "answer", "", problems),
        at=shape.filled(data, "at", "", problems),
    )
