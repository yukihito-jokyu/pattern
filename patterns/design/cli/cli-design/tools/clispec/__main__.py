"""検査ツールの入口。作者は Makefile のターゲットから起動する（TOOL-04）。"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import sys
from pathlib import Path
from typing import List

import canon
import check
import compat
import conform
import gen
import model
import scaffold
import vocab

ROOT = Path(__file__).resolve().parents[2]


def spec_files(targets: List[str]) -> List[Path]:
    return [d / model.SPEC_FILE for d in model.iter_spec_dirs(ROOT, targets) if (d / model.SPEC_FILE).is_file()]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def cmd_check(args: argparse.Namespace) -> int:
    findings = check.check(ROOT, args.targets)
    for f in findings:
        print(f)
    if findings:
        print(f"check: {len(findings)} 件のエラー", file=sys.stderr)
        return 1
    return 0


def cmd_fmt(args: argparse.Namespace) -> int:
    bad = 0
    for path in spec_files(args.targets):
        text = path.read_text(encoding="utf-8")
        try:
            data = model.load(path)
        except model.SpecError as exc:
            print(f"CODE-01 {rel(path)}:1 (root): {exc}")
            bad += 1
            continue
        if not args.check:
            data = apply_version(path, data)
        want = canon.dumps(model.canonical(data))
        if text == want:
            continue
        if args.check:
            print(f"TOOL-01 {rel(path)}:1 (root): 正規の形ではありません（make fix で直す）")
            bad += 1
        else:
            path.write_text(want, encoding="utf-8")
            print(f"fmt: {rel(path)}")
    return 1 if bad else 0


def apply_version(path: Path, data: object) -> object:
    """PROC-06 リリース済みの最新版との差分から版を書く。メジャーは承認が要るので書かない。"""
    if not isinstance(data, dict) or not isinstance(data.get("version"), str):
        return data
    releases = model.released_versions(path.parent)
    if not releases:
        want = "1.0.0"
    else:
        try:
            d = compat.diff(model.load(releases[-1][1]), data)
        except (model.SpecError, AttributeError, KeyError, TypeError):
            return data
        want = compat.text(compat.bump(releases[-1][0], d.level))
        if d.level == "major":
            if data["version"] != want:
                print(f"PROC-06 {rel(path)}: メジャーを上げる差分です（{d.first('major')}）。"
                      f"ユーザーの承認を ADR に書いてから version を {want!r} にする", file=sys.stderr)
            return data
    if data["version"] != want:
        print(f"fmt: {rel(path)} の version を {want} にしました（PROC-06）")
        data["version"] = want
    return data


def cmd_gen(args: argparse.Namespace) -> int:
    bad = 0
    for path in spec_files(args.targets):
        doc = path.with_name(model.DOC_FILE)
        try:
            data = model.load(path)
            want = gen.render(model.canonical(data))
        except (model.SpecError, KeyError, TypeError, AttributeError, IndexError) as exc:
            if args.check:
                continue  # 仕様の形の誤りは check が報告する
            print(f"STR-04 {rel(path)}:1 (root): 仕様の形が誤っていて cli.md を作れません: {exc!r}")
            bad += 1
            continue
        current = doc.read_text(encoding="utf-8") if doc.is_file() else None
        if current == want:
            continue
        if args.check:
            print(f"STR-04 {rel(doc)}:1 (root): cli.json と合っていません（make fix で作り直す。手で直さない）")
            bad += 1
        else:
            doc.write_text(want, encoding="utf-8")
            print(f"gen: {rel(doc)}")
    return 1 if bad else 0


def cmd_new(args: argparse.Namespace) -> int:
    name = args.name
    if not vocab.CLI_NAME.match(name):
        print(f"new: 名前 {name!r} は ^[a-z][a-z0-9]*(-[a-z0-9]+)*$ に合いません（NAM-01）", file=sys.stderr)
        return 2
    spec_dir = ROOT / model.SPECS_DIR / name
    if spec_dir.exists():
        print(f"new: {rel(spec_dir)} は既にあります", file=sys.stderr)
        return 1
    path = spec_dir / model.SPEC_FILE
    scaffold.write(path, scaffold.new_spec(name, args.single))
    print(f"new: {rel(path)}（TODO を埋め、make command でコマンドを足す）")
    return 0


def cmd_command(args: argparse.Namespace) -> int:
    path = ROOT / model.SPECS_DIR / args.name / model.SPEC_FILE
    if not path.is_file():
        print(f"command: {rel(path)} がありません（先に make new NAME={args.name}）", file=sys.stderr)
        return 1
    for word in (args.noun, args.verb):
        if not vocab.WORD.match(word):
            print(f"command: {word!r} は英小文字の1語にする（NAM-01）", file=sys.stderr)
            return 2
    spec = model.canonical(model.load(path))
    reason = scaffold.add_command(spec, args.noun, args.verb, args.key)
    if reason:
        print(f"command: {reason}", file=sys.stderr)
        return 1
    scaffold.write(path, spec)
    todo = "（TODO を埋める）" if "TODO" in json.dumps(spec) else ""
    print(f"command: {args.noun} {args.verb} を {rel(path)} に足しました{todo}")
    return 0


def cmd_field(args: argparse.Namespace) -> int:
    path = ROOT / model.SPECS_DIR / args.name / model.SPEC_FILE
    if not path.is_file():
        print(f"field: {rel(path)} がありません（先に make new NAME={args.name}）", file=sys.stderr)
        return 1
    values = [v for v in (args.values or "").split(",") if v]
    spec = model.canonical(model.load(path))
    reason = scaffold.add_field(spec, args.noun, args.field, args.type, args.list, args.nullable, values)
    if reason:
        print(f"field: {reason}", file=sys.stderr)
        return 1
    scaffold.write(path, spec)
    print(f"field: {args.noun} に {args.field} を足し、create・edit・list のオプションを合わせました（{rel(path)}）")
    return 0


def cmd_release(args: argparse.Namespace) -> int:
    spec_dir = ROOT / model.SPECS_DIR / args.name
    findings = check.check(ROOT, [rel(spec_dir)])
    if findings:
        for f in findings:
            print(f)
        print("release: 検査が通らない仕様はリリースしない", file=sys.stderr)
        return 1
    spec = model.load(spec_dir / model.SPEC_FILE)
    releases = model.released_versions(spec_dir)
    if releases and compat.diff(model.load(releases[-1][1]), spec).level == "none":
        print(f"release: {compat.text(releases[-1][0])} から変わっていません", file=sys.stderr)
        return 1
    target = spec_dir / model.RELEASED_DIR / f"{spec['version']}.json"
    if target.exists():
        print(f"release: {rel(target)} は既にあります（version を上げる）", file=sys.stderr)
        return 1
    target.parent.mkdir(exist_ok=True)
    shutil.copyfile(spec_dir / model.SPEC_FILE, target)
    print(f"release: {rel(target)}")
    return 0


def cmd_conform(args: argparse.Namespace) -> int:
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if len(command) == 1:
        command = shlex.split(command[0])
    if not command:
        print("conform: 実装を起動するコマンドを渡す（make conform SPEC=... CMD=\"...\"）", file=sys.stderr)
        return 2
    spec_path = Path(args.spec)
    findings = check.check(ROOT, [rel(spec_path.resolve().parent)])
    if findings:
        for f in findings:
            print(f)
        print("conform: 仕様の検査が通っていません", file=sys.stderr)
        return 1
    results = conform.run(model.load(spec_path), command)
    for line in results:
        print(line)
    return 1 if len(results) > 1 else 0


def cmd_after_edit(args: argparse.Namespace) -> int:
    """hooks から呼ぶ（TOOL-02）。整形し、cli.md を作り直し、その仕様だけを検査する。"""
    target = [args.file]
    fmt_ok = cmd_fmt(argparse.Namespace(targets=target, check=False)) == 0
    gen_ok = cmd_gen(argparse.Namespace(targets=target, check=False)) == 0
    return 0 if fmt_ok and gen_ok and cmd_check(argparse.Namespace(targets=target)) == 0 else 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="clispec", description="CLI の仕様（specs/<name>/cli.json）の検査ツール")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("check", help="仕様を検査する")
    s.add_argument("targets", nargs="*")
    s.set_defaults(func=cmd_check)
    s = sub.add_parser("fmt", help="仕様を正規の形にする")
    s.add_argument("--check", action="store_true", help="書き換えずに差分の有無だけを調べる")
    s.add_argument("targets", nargs="*")
    s.set_defaults(func=cmd_fmt)
    s = sub.add_parser("gen", help="cli.md を作る")
    s.add_argument("--check", action="store_true", help="書き換えずに差分の有無だけを調べる")
    s.add_argument("targets", nargs="*")
    s.set_defaults(func=cmd_gen)
    s = sub.add_parser("new", help="新しい CLI の仕様を作る")
    s.add_argument("name")
    s.add_argument("--single", action="store_true", help="サブコマンドを持たない CLI にする")
    s.set_defaults(func=cmd_new)
    s = sub.add_parser("command", help="コマンドを足す")
    s.add_argument("name")
    s.add_argument("noun")
    s.add_argument("verb")
    s.add_argument("--key", choices=sorted(vocab.KEY_FIELDS), default="id", help="型を新しく作るときの識別子")
    s.set_defaults(func=cmd_command)
    s = sub.add_parser("field", help="名詞の型に項目を足す")
    s.add_argument("name")
    s.add_argument("noun")
    s.add_argument("field")
    s.add_argument("type")
    s.add_argument("--list", action="store_true", help="値のリストにする")
    s.add_argument("--nullable", action="store_true", help="null を許す")
    s.add_argument("--values", help="enum の選択肢（カンマ区切り）")
    s.set_defaults(func=cmd_field)
    s = sub.add_parser("release", help="仕様を released/ に写す")
    s.add_argument("name")
    s.set_defaults(func=cmd_release)
    s = sub.add_parser("conform", help="実装に適合テストをかける")
    s.add_argument("spec")
    s.add_argument("command", nargs=argparse.REMAINDER)
    s.set_defaults(func=cmd_conform)
    s = sub.add_parser("after-edit", help="編集の直後に回す")
    s.add_argument("file")
    s.set_defaults(func=cmd_after_edit)
    return p


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
