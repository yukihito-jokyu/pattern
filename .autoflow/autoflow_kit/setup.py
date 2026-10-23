"""準備の段（setup-new、setup-check、setup-approve）。プロファイルの案を作り、H0 で人の承認を記録する。"""

from __future__ import annotations

import re

from autoflow_kit import fsops, layout, proc, profile, render, shape, views, workspace
from autoflow_kit.errors import InvalidFileError, StageError
from autoflow_kit.layout import Layout
from autoflow_kit.profile import Command

PACKAGE_SCRIPTS = ("type-check", "typecheck", "lint", "test", "build")
MAKE_TARGETS = ("lint", "test", "build")
MAKE_TARGET = re.compile(r"^([A-Za-z0-9_.-]+):", re.MULTILINE)
TIMEOUT = profile.DEFAULT_TIMEOUT_SEC


def _make_commands(where: Layout) -> list[Command]:
    path = where.repo_path("Makefile")
    if not path.is_file():
        return []
    targets = set(MAKE_TARGET.findall(fsops.read_text(path)))
    if "check" in targets:
        return [Command("make-check", "make check", TIMEOUT)]
    return [Command(f"make-{name}", f"make {name}", TIMEOUT) for name in MAKE_TARGETS if name in targets]


def _package_commands(where: Layout) -> list[Command]:
    path = where.repo_path(layout.PACKAGE_FILE)
    if not path.is_file():
        return []
    scripts = workspace.load_scripts(path)
    runner = "npm run"
    if where.repo_path("pnpm-lock.yaml").is_file():
        runner = "pnpm"
    elif where.repo_path("yarn.lock").is_file():
        runner = "yarn"
    return [Command(f"npm-{name}", f"{runner} {name}", TIMEOUT) for name in PACKAGE_SCRIPTS if name in scripts]


def _language_commands(where: Layout) -> list[Command]:
    found = []
    if where.repo_path("go.mod").is_file():
        found += [
            Command("go-build", "go build ./...", TIMEOUT),
            Command("go-vet", "go vet ./...", TIMEOUT),
            Command("go-test", "go test ./...", TIMEOUT),
        ]
    if where.repo_path("Cargo.toml").is_file():
        found += [Command("cargo-build", "cargo build", TIMEOUT), Command("cargo-test", "cargo test", TIMEOUT)]
    pyproject = where.repo_path("pyproject.toml")
    if pyproject.is_file() and "pytest" in fsops.read_text(pyproject):
        found.append(Command("pytest", "python3 -m pytest -q", TIMEOUT))
    return found


def detect_commands(where: Layout) -> tuple[Command, ...]:
    """リポジトリのファイルから検査コマンドの案を作る。Makefile に check があれば、それだけにする。"""
    make = _make_commands(where)
    if make and make[0].id == "make-check":
        return tuple(make)
    return (*make, *_package_commands(where), *_language_commands(where))


def setup_new(where: Layout, *, force: bool) -> str:
    if where.profile_path.is_file() and not force:
        raise StageError(
            f"{where.relative(where.profile_path)} は既にあります。作り直すなら setup-new --force、"
            "確かめるなら setup-check を実行する"
        )
    commands = detect_commands(where)
    guides = tuple(name for name in layout.GUIDE_FILES if where.repo_path(name).is_file())
    draft = profile.make_profile(commands, guides)
    fsops.write_json(where.profile_path, shape.to_data(draft))
    lines = [f"書いた: {where.relative(where.profile_path)}", "", views.render_profile(draft)]
    if not commands:
        lines.append("WARN 検査コマンドが見つかりません。verify.commands に、テスト・lint・型検査のコマンドを書く")
    lines.append(f"次: {layout.CLI} setup-check")
    return "\n".join(lines)


def setup_check(where: Layout) -> str:
    settings = workspace.load_profile_file(where.profile_path)
    missing = [name for name in settings.review.guide_files if not where.repo_path(name).is_file()]
    lines = [views.render_profile(settings)]
    lines += [f"WARN review.guide_files の {name} がありません" for name in missing]
    lines.append(
        f"次: この内容を人に見せ、承認を得る（H0）。承認なら {layout.CLI} setup-approve --answer '<人の回答の原文>'"
    )
    return "\n".join(lines)


def _allow_rules(where: Layout, settings: profile.Profile) -> tuple[str, ...]:
    """検査コマンドを、確認なしで実行してよいコマンドとして .claude/settings.local.json に足す。"""
    current = workspace.load_settings(where.settings_local_path)
    problems: list[str] = []
    permissions = shape.as_object(current.get("permissions", {}), "permissions", problems)
    raw = permissions.get("allow", [])
    if not isinstance(raw, list):
        problems.append("permissions.allow は配列にしてください")
    if problems:
        raise InvalidFileError(str(where.settings_local_path), problems)
    allow = [rule for rule in raw if isinstance(rule, str)] if isinstance(raw, list) else []
    added = tuple(
        rule for rule in (f"Bash({command.run})" for command in settings.verify.commands) if rule not in allow
    )
    if added:
        updated = {**current, "permissions": {**permissions, "allow": [*allow, *added]}}
        fsops.write_json(where.settings_local_path, updated)
    return added


def setup_approve(where: Layout, answer: str, now: str, *, allow: bool) -> str:
    if not answer.strip():
        raise StageError("人の回答の原文を --answer に渡す。回答が無い・空・自動で閉じた質問は承認にしない")
    settings = workspace.load_profile_file(where.profile_path)
    approval = profile.Approval(
        sha256=profile.digest(fsops.read_text(where.profile_path)),
        who=proc.git_user(where.root),
        answer=answer,
        at=now,
    )
    fsops.write_json(where.approval_path, shape.to_data(approval))
    lines = [f"承認を記録した: {where.relative(where.approval_path)}（承認した人: {approval.who or render.MISSING}）"]
    if allow:
        added = _allow_rules(where, settings)
        lines += [f"足した許可（{where.relative(where.settings_local_path)}）:", render.bullets(added)]
    lines.append("次: /autoflow で依頼を渡す。未コミットの変更は保持し、開始後の差分と分けて扱う")
    return "\n".join(lines)
