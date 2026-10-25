#!/usr/bin/env python3
"""違反例（probe）を基盤の一時コピーに1件ずつ入れて検査を回し、検査が落ちることを証明する。

元のディレクトリには触れない。最初に何も入れない状態（baseline）で検査が通ることを確かめ、
その後 probe ごとに「終了コードが0以外」かつ「出力が expect の正規表現に一致」すれば成功とする。
probe に command（速い検査だけを回す絞ったコマンド）がある場合は、絞ったコマンドごとに代表の probe を
check 全体でも回し、その検査が check に組み込まれていることを確かめる（wiring）。
結果は .foundation/probe-results.json に書く（probes.json のハッシュ付き。rules_check.py --final が参照する）。
--only か --probes を付けたときは、正規の結果を上書きしないよう書かない。

使い方:
  python3 violation_probe.py [--root <基盤>] [--only DEP-01-a,NAM-02-a] [--timeout 600] [--keep-temp]
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root")
    parser.add_argument("--probes", help="既定: <root>/.foundation/probes.json（別のファイルを指定すると結果は書かない）")
    parser.add_argument("--only", help="カンマ区切りの probe ID だけを回す（結果ファイルは書かない）")
    parser.add_argument("--timeout", type=int, default=600, help="1回の検査の秒数の上限")
    parser.add_argument("--workdir", help="一時コピーを置く親ディレクトリ（既定: OS の一時ディレクトリ）")
    parser.add_argument("--keep-temp", action="store_true", help="一時コピーを消さずに残す")
    args = parser.parse_args()

    root = _lib.resolve_root(args.root)
    manifest = _lib.load_manifest(root)
    probes_path = Path(args.probes).resolve() if args.probes else root / ".foundation/probes.json"
    doc = _lib.load_json(probes_path)
    default_command = manifest.get("commands", {}).get("check")
    if not default_command:
        _lib.fail("manifest の commands.check がありません")
    probes = doc.get("probes", [])
    if args.only:
        wanted = {p.strip() for p in args.only.split(",") if p.strip()}
        probes = [p for p in probes if p.get("id") in wanted]
        missing = wanted - {p.get("id") for p in probes}
        if missing:
            _lib.fail(f"probes.json に無い ID: {', '.join(sorted(missing))}")
    if not probes:
        print("probe が0件です。機械で縛るルールの違反例を probes.json に書いてください")
        return 1

    skip, link = _lib.copy_settings(manifest)
    parent = Path(args.workdir).resolve() if args.workdir else None
    if parent:
        parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix=f"{manifest.get('name', 'foundation')}-probe-", dir=parent))
    work = temp_root / "repo"
    print(f"一時コピー: {work}")
    _lib.copy_project(root, work, skip, link)

    try:
        started = time.monotonic()
        code, output = _lib.run_shell(default_command, work, args.timeout)
        print(f"baseline  `{default_command}` → 終了コード {code}（{time.monotonic() - started:.1f} 秒）")
        if code != 0:
            print("baseline で検査が落ちています。先に検査が通る状態にしてください。出力の末尾:")
            print(_lib.tail(output, 40))
            return 2

        results = []
        for probe in probes:
            pid, rule = probe.get("id"), probe.get("rule")
            command = probe.get("command") or default_command
            applied = []
            try:
                for change in probe.get("files", []):
                    applied.append(_lib.apply_file_change(work, change))
            except ValueError as exc:
                for target, original in reversed(applied):
                    _lib.revert_file_change(target, original)
                results.append({"id": pid, "rule": rule, "passed": False, "exit": None, "matched": False,
                                "reason": f"適用できません: {exc}"})
                print(f"失敗  {pid}  適用できません: {exc}")
                continue
            started = time.monotonic()
            code, output = _lib.run_shell(command, work, args.timeout)
            elapsed = time.monotonic() - started
            for target, original in reversed(applied):
                _lib.revert_file_change(target, original)
            matched = bool(re.search(probe.get("expect", ""), output))
            passed = code != 0 and matched
            reason = "" if passed else ("検査が通ってしまった（違反を検出していない）" if code == 0
                                        else "検査は落ちたが、出力が expect に一致しない（別の理由で落ちた可能性）")
            results.append({"id": pid, "rule": rule, "passed": passed, "exit": code, "matched": matched,
                            "reason": reason, "output_tail": "" if passed else _lib.tail(output, 15)})
            print(f"{'成功' if passed else '失敗'}  {pid}  終了コード {code}、expect 一致 {'あり' if matched else 'なし'}"
                  f"（{elapsed:.1f} 秒）{'  ' + reason if reason else ''}")
            if not passed:
                print("    " + _lib.tail(output, 15).replace("\n", "\n    "))
        # 組み込みの確認: probe ごとに絞ったコマンドは、check 全体の中で本当に呼ばれているか。
        # 絞ったコマンドごとに代表の probe を1件、check 全体で回して落ちることを確かめる。
        wiring = []
        if not args.only:
            representatives: dict[str, dict] = {}
            for probe, result in zip(probes, results):
                command = probe.get("command")
                if command and command != default_command and command not in representatives and result["passed"]:
                    representatives[command] = probe
            for probe in probes:
                command = probe.get("command")
                if command and command != default_command and command not in representatives:
                    representatives[command] = probe  # 成功した probe が無い場合も、未確認として記録する
            for command, probe in representatives.items():
                applied = []
                try:
                    for change in probe.get("files", []):
                        applied.append(_lib.apply_file_change(work, change))
                    code, output = _lib.run_shell(default_command, work, args.timeout)
                    passed = code != 0 and bool(re.search(probe.get("expect", ""), output))
                except ValueError:
                    passed = False
                finally:
                    for target, original in reversed(applied):
                        _lib.revert_file_change(target, original)
                wiring.append({"command": command, "probe": probe.get("id"), "passed": passed})
                print(f"{'成功' if passed else '失敗'}  組み込み `{command}` を check 全体で確認（{probe.get('id')}）"
                      + ("" if passed else "  check の中で呼ばれていないか、別の段で先に落ちている"))
    finally:
        if args.keep_temp:
            print(f"一時コピーを残しました: {work}")
        else:
            shutil.rmtree(temp_root, ignore_errors=True)

    failed = [r for r in results if not r["passed"]]
    failed_wiring = [w for w in wiring if not w["passed"]]
    if not args.only and not args.probes:  # 一部や別のファイルの結果で、正規の結果を上書きしない
        _lib.write_json(root / ".foundation/probe-results.json", {
            "probes_sha256": _lib.sha256_file(probes_path),
            "command": default_command,
            "results": results,
            "wiring": wiring,
        })
    print(f"\nprobe {len(results)} 件中 成功 {len(results) - len(failed)} 件、失敗 {len(failed)} 件"
          + (f"／組み込みの確認 {len(wiring)} 件中 失敗 {len(failed_wiring)} 件" if wiring else ""))
    return 1 if failed or failed_wiring else 0


if __name__ == "__main__":
    sys.exit(main())
