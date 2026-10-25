#!/usr/bin/env python3
"""docs/design/rules.md を検査し、docs/design/enforcement-matrix.md を生成する。

検査はフェーズに合わせて段階的に増える。--phase を省くと、manifest の status が ready なら 5、
building なら 4 になる（check コマンドに入れたまま、作成中も完成後も正しい範囲を検査するため）。
  3: ルールIDの形式・重複・節の接頭辞、必須項目、決定のあいまいな語（コード片を除く）、
     強制のキーワード、機械化しない理由、揺れの軸のカタログ全体が覆われていること
  4: 3 に加えて probes.json の形式、機械で縛る段ごとの probe、guard のルールIDの実在。
     エラーが無ければ対応表を書く
  5: 4 に加えて review を含むルールがレビュー用スキルの表の1列目にあること、
     doc を含むルールが AGENTS.md か実装用スキルにあること
  --final: 5 に加えて TODO の目印の残り、research.md の「未確認」、probe の結果（最新・全件成功・
     check への組み込み）、replace/append の probe の対象ファイルの実在、manifest の status が ready

使い方:
  python3 rules_check.py [--root <基盤>] [--phase 3|4|5] [--final] [--no-write]
  --no-write: 対応表を書き込まず、最新でなければエラーにする（check コマンドではこちらを使う）
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

AXES = (
    [f"A{i}" for i in range(1, 8)] + [f"B{i}" for i in range(1, 7)] + [f"C{i}" for i in range(1, 8)]
    + [f"D{i}" for i in range(1, 9)] + [f"E{i}" for i in range(1, 9)] + [f"F{i}" for i in range(1, 6)]
    + [f"G{i}" for i in range(1, 6)] + [f"H{i}" for i in range(1, 5)]
)
LEVELS = ["type", "format", "lint", "structure", "test", "generator", "review", "doc"]
MACHINE = ["type", "format", "lint", "structure", "test"]
FIELDS = ["状態", "軸", "決定", "理由", "出典", "強制", "機械化しない理由", "probe", "良い例", "悪い例"]
REQUIRED = ["軸", "決定", "理由", "強制", "probe", "良い例", "悪い例"]
VAGUE_JA = ["なるべく", "できるだけ", "できる限り", "可能な限り", "可能であれば", "極力", "適切", "適宜", "必要に応じ",
            "基本的に", "原則として", "推奨", "望ましい", "場合による", "場合によって", "ケースバイケース",
            "状況に応じ", "柔軟に", "など", "等々", "その他"]
VAGUE_EN = [r"\bshould\b", r"\bprefer(?:ably|red)?\b", r"\brecommended\b", r"\bappropriate(?:ly)?\b",
            r"\bas needed\b", r"\bif possible\b", r"\bgenerally\b", r"\busually\b", r"\betc\b", r"\bwhere sensible\b"]
OPEN_ENDED_JA = ["を含む", "ほか"]  # 列挙が閉じていない可能性がある語（警告）
RULE_HEAD = re.compile(r"^###\s+(\S+)\s+(.+?)\s*$")
FIELD_LINE = re.compile(r"^-\s*(" + "|".join(FIELDS) + r")\s*[:：]\s*(.*)$")
ID_FORMAT = re.compile(r"^[A-Z]{2,6}-\d{2,3}$")
PROBE_ID = re.compile(r"[A-Z]{2,6}-\d{2,3}-[A-Za-z0-9]+")
GENERATED_HEADER = "<!-- このファイルは rules_check.py が rules.md と probes.json から生成する。手で編集しない。 -->"


RANGE = re.compile(r"^([A-Z]+)(\d+)[〜～~]([A-Z]+)?(\d+)$")


def expand_axes(text: str) -> list[str]:
    """「B4〜B6、D1, X2」を軸の記号の一覧にする。範囲の記法（〜 か ~）は展開する。"""
    codes = []
    for token in (t for t in re.split(r"[,、\s]+", text.strip()) if t):
        match = RANGE.match(token)
        if match and (match.group(3) in (None, match.group(1))) and int(match.group(2)) <= int(match.group(4)):
            codes += [f"{match.group(1)}{i}" for i in range(int(match.group(2)), int(match.group(4)) + 1)]
        else:
            codes.append(token)
    return codes


def parse_rules(text: str):
    rules, excluded, extra_axes, section_prefixes = [], {}, set(), {}
    section, current, field = "", None, None
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            if current is not None and field is not None:
                current["fields"][field] += "\n" + line
            continue
        if in_fence:
            if current is not None and field is not None:
                current["fields"][field] += "\n" + line
            continue
        if line.startswith("## "):
            section = line[3:].strip()
            current, field = None, None
            words = section.split()
            if words and re.fullmatch(r"[A-Z]{2,6}", words[0]):
                section_prefixes[section] = words[0]
            continue
        head = RULE_HEAD.match(line)
        if head:
            current = {"id": head.group(1), "title": head.group(2), "line": lineno, "section": section, "fields": {}}
            rules.append(current)
            field = None
            continue
        if line.startswith("|") and ("対象外とした軸" in section or "追加した軸" in section):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not cells or not cells[0] or set(cells[0]) <= set("-: ") or cells[0] == "軸":
                continue
            for code in expand_axes(cells[0]):
                if "対象外とした軸" in section:
                    excluded[code] = cells[1] if len(cells) > 1 else ""
                else:
                    extra_axes.add(code)
            continue
        if current is None:
            continue
        match = FIELD_LINE.match(line)
        if match:
            field = match.group(1)
            current["fields"][field] = match.group(2).strip()
        elif field is not None:
            current["fields"][field] += "\n" + line
    return rules, excluded, extra_axes, section_prefixes


def split_enforce(enforce: str) -> tuple[list[str], str]:
    """「lint, review — 説明」を、キーワードの一覧と説明に分ける。"""
    first_line = enforce.strip().splitlines()[0] if enforce.strip() else ""
    parts = re.split(r"\s+[—–]\s+|\s+-\s+", first_line, maxsplit=1)
    keywords = [k for k in re.split(r"[,、\s]+", parts[0].strip()) if k]
    return keywords, (parts[1].strip() if len(parts) > 1 else "")


def strip_code(text: str) -> str:
    """フェンスとインラインのコード片を除く（ルール名・識別子・パスをあいまい語と誤認しないため）。"""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", " ", text)


def id_pattern(rid: str) -> re.Pattern:
    return re.compile(r"(?<![A-Z])" + re.escape(rid) + r"(?![\d-])")


def guard_rules(manifest: dict) -> list[str]:
    guard = manifest.get("guard", {})
    ids = [guard["rule"]] if guard.get("rule") else []
    ids += [s["rule"] for s in guard.get("suppressions", []) if isinstance(s, dict) and s.get("rule")]
    return sorted(set(ids))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root")
    parser.add_argument("--phase", type=int, choices=[3, 4, 5],
                        help="どのフェーズまでの検査をするか（既定: status が ready なら 5、それ以外は 4）")
    parser.add_argument("--final", action="store_true", help="仕上げの検査も行う（--phase 5 を含む）")
    parser.add_argument("--no-write", action="store_true", help="対応表を書き込まず、最新かどうかだけを検査する")
    args = parser.parse_args()

    root = _lib.resolve_root(args.root)
    manifest = _lib.load_manifest(root)
    phase = 5 if args.final else (args.phase or (5 if manifest.get("status") == "ready" else 4))
    rules_path = root / "docs/design/rules.md"
    probes_path = root / ".foundation/probes.json"
    matrix_path = root / "docs/design/enforcement-matrix.md"
    results_path = root / ".foundation/probe-results.json"
    skills = manifest.get("skills", {})
    review_dir = root / ".claude/skills" / skills.get("review", "review")
    impl_dir = root / ".claude/skills" / skills.get("impl", "impl")

    errors: list[str] = []
    warnings: list[str] = []
    if not rules_path.is_file():
        _lib.fail(f"{rules_path} がありません")
    rules, excluded, extra_axes, section_prefixes = parse_rules(rules_path.read_text(encoding="utf-8"))
    probes = (_lib.load_json(probes_path) if probes_path.is_file() else {}).get("probes", [])
    probe_by_id: dict[str, dict] = {}

    if phase >= 4:
        for probe in probes:
            pid = probe.get("id", "")
            if not PROBE_ID.fullmatch(pid):
                errors.append(f"probes.json: id {pid!r} は <ルールID>-<記号> の形にしてください（例: DEP-01-a）")
            if pid in probe_by_id:
                errors.append(f"probes.json: id {pid} が重複しています")
            probe_by_id[pid] = probe
            if probe.get("level") not in MACHINE:
                errors.append(f"probes.json: {pid} の level は {MACHINE} のどれかにしてください（どの段を証明するか）")
            if not probe.get("files"):
                errors.append(f"probes.json: {pid} に files がありません")
            for change in probe.get("files", []):
                if change.get("mode", "create") not in ("create", "replace", "append"):
                    errors.append(f"probes.json: {pid} の mode が不正です")
            if not probe.get("expect"):
                errors.append(f"probes.json: {pid} に expect（出力に含まれるべき文字列の正規表現）がありません")
            else:
                try:
                    re.compile(probe["expect"])
                except re.error as exc:
                    errors.append(f"probes.json: {pid} の expect が正規表現として不正です: {exc}")

    def skill_text(directory: Path) -> str:
        if not directory.is_dir():
            return ""
        return "\n".join((_lib.read_text(directory / rel) or "") for rel in _lib.iter_files(directory, [], []))

    review_text = skill_text(review_dir)
    doc_text = skill_text(impl_dir) + "\n" + ((_lib.read_text(root / "AGENTS.md") or "") if (root / "AGENTS.md").is_file() else "")
    if phase >= 5 and not review_dir.is_dir():
        errors.append(f"レビュー用スキル {review_dir.relative_to(root)} がありません")

    seen: set[str] = set()
    covered: set[str] = set()
    rows = []
    rule_by_id: dict[str, dict] = {}
    for rule in rules:
        rid, f = rule["id"], rule["fields"]
        where = f"rules.md:{rule['line']} {rid}"
        if not ID_FORMAT.fullmatch(rid):
            errors.append(f"{where}: ルールIDは <英大文字2〜6>-<数字2〜3> の形にしてください")
        if rid in seen:
            errors.append(f"{where}: ルールIDが重複しています")
        seen.add(rid)
        rule_by_id[rid] = rule
        prefix = section_prefixes.get(rule["section"])
        if prefix and not rid.startswith(prefix + "-"):
            errors.append(f"{where}: 節「{rule['section']}」のルールは {prefix}- で始めてください")
        if f.get("状態", "").startswith("廃止"):
            rows.append({"id": rid, "title": rule["title"], "levels": ["廃止"], "desc": "", "probes": [],
                         "reason": "", "retired": True})
            continue
        for name in REQUIRED:
            if not f.get(name, "").strip():
                errors.append(f"{where}: 「{name}」がありません")
        decision = strip_code(f.get("決定", ""))
        for word in VAGUE_JA:
            if word in decision:
                errors.append(f"{where}: 決定にあいまいな語「{word}」があります。条件と答えで書いてください")
        for pattern in VAGUE_EN:
            if re.search(pattern, decision, re.IGNORECASE):
                errors.append(f"{where}: 決定にあいまいな語 /{pattern}/ があります")
        for word in OPEN_ENDED_JA:
            if word in decision:
                warnings.append(f"{where}: 決定の「{word}」は列挙が閉じていない可能性があります。全部を列挙しているか確かめてください")
        axes = expand_axes(f.get("軸", ""))
        for axis in axes:
            if axis not in AXES and axis not in extra_axes:
                errors.append(f"{where}: 軸 {axis} はカタログにも「追加した軸」表にもありません")
        covered.update(axes)

        keywords, desc = split_enforce(f.get("強制", ""))
        unknown = [k for k in keywords if k not in LEVELS]
        if unknown:
            errors.append(f"{where}: 強制のキーワード {unknown} は {LEVELS} のどれかにしてください")
        levels = [k for k in LEVELS if k in keywords]
        machine_levels = [k for k in levels if k in MACHINE]
        if levels and not machine_levels and not f.get("機械化しない理由", "").strip():
            errors.append(f"{where}: 強制が {levels} だけのルールには「機械化しない理由」が必要です")
        if levels == ["generator"]:
            warnings.append(f"{where}: generator だけでは後から崩せます。structure か review と併用してください")

        listed = PROBE_ID.findall(f.get("probe", ""))
        if phase >= 4:
            for level in machine_levels:
                if not any(probe_by_id.get(pid, {}).get("level") == level for pid in listed):
                    errors.append(f"{where}: 強制の {level} を証明する probe（level: {level}）がありません")
            for pid in listed:
                probe = probe_by_id.get(pid)
                if probe is None:
                    errors.append(f"{where}: probe {pid} が probes.json にありません")
                elif probe.get("rule") != rid:
                    errors.append(f"{where}: probe {pid} の rule が {probe.get('rule')!r} になっています")
                elif probe.get("level") not in machine_levels:
                    errors.append(f"{where}: probe {pid} の level {probe.get('level')!r} は、このルールの強制に含まれていません")
        if phase >= 5:
            if "review" in levels and not re.search(r"^\|\s*" + re.escape(rid) + r"\s*\|", review_text, re.M):
                errors.append(f"{where}: 強制に review を含むので、レビュー用スキルの表の1列目に {rid} を書いてください")
            if "doc" in levels and not id_pattern(rid).search(doc_text):
                errors.append(f"{where}: 強制に doc を含むので、AGENTS.md か実装用スキルに {rid} を書いてください")
        reason = f.get("機械化しない理由", "").strip()
        rows.append({"id": rid, "title": rule["title"], "levels": levels, "desc": desc, "probes": listed,
                     "reason": reason.splitlines()[0] if reason else "", "retired": False})

    if phase >= 4:
        for pid, probe in probe_by_id.items():
            if probe.get("rule") not in rule_by_id:
                errors.append(f"probes.json: {pid} の rule {probe.get('rule')!r} は rules.md にありません")
        guard = manifest.get("guard", {})
        unnamed = [(s.get("pattern") if isinstance(s, dict) else s) for s in guard.get("suppressions", [])
                   if not (isinstance(s, dict) and s.get("rule"))]
        if unnamed and not guard.get("rule"):
            errors.append(f"manifest の guard.suppressions に rule の無いパターンがあります: {unnamed}。"
                          "そのパターンを禁じたルールIDを書いてください")
        for gid in guard_rules(manifest):
            rule = rule_by_id.get(gid)
            if rule is None:
                errors.append(f"manifest の guard のルールID {gid} が rules.md にありません")
            elif "H3" not in expand_axes(rule["fields"].get("軸", "")):
                warnings.append(f"manifest の guard のルールID {gid} の軸に H3（抜け道の禁止）がありません")

    missing_axes = [a for a in AXES + sorted(extra_axes) if a not in covered and a not in excluded]
    if missing_axes:
        errors.append(f"rules.md: 次の軸がルールにも「対象外とした軸」表にもありません: {', '.join(missing_axes)}")
    if not rules:
        errors.append("rules.md: ルールが1件もありません")

    results_note = "未実行"
    if phase >= 4 and results_path.is_file() and probes_path.is_file():
        results = _lib.load_json(results_path)
        results_note = "最新" if results.get("probes_sha256") == _lib.sha256_file(probes_path) else "古い"

    if args.final:
        if manifest.get("status") != "ready":
            errors.append("manifest の status が ready ではありません（フェーズ5の終わりに ready にする）")
        unversioned = [i.get("name") for i in manifest.get("stack", []) + manifest.get("tools", [])
                       if isinstance(i, dict) and not str(i.get("version", "")).strip()
                       and i.get("role") not in ("structure", "other")]
        if unversioned:
            errors.append(f"manifest の version が空です（フェーズ2で確認した版を書く）: {', '.join(map(str, unversioned))}")
        if results_note != "最新":
            errors.append(f"probe の結果が{results_note}です。violation_probe.py を実行してください")
        else:
            results = _lib.load_json(results_path)
            status = {r.get("id"): r.get("passed") for r in results.get("results", [])}
            failed = [pid for pid in probe_by_id if not status.get(pid)]
            if failed:
                errors.append(f"成功していない probe があります: {', '.join(failed)}")
            bad_wiring = [w["command"] for w in results.get("wiring", []) if not w.get("passed")]
            if bad_wiring:
                errors.append(f"check から呼ばれていない、または check で違反を検出できない検査があります: {', '.join(bad_wiring)}")
        for pid, probe in probe_by_id.items():
            for change in probe.get("files", []):
                if change.get("mode") in ("replace", "append") and not (root / change.get("path", "")).is_file():
                    errors.append(f"probes.json: {pid} の対象 {change.get('path')} がありません（mode={change.get('mode')}）")
        research = root / "docs/design/research.md"
        if research.is_file():
            pending = [line.strip() for line in research.read_text(encoding="utf-8").splitlines()
                       if re.search(r"確認の状態\s*[:：].*未確認", line)]
            if pending:
                errors.append(f"docs/design/research.md に確認の状態が「未確認」の項目が {len(pending)} 件残っています")
        skip, link = _lib.copy_settings(manifest)
        for rel in _lib.iter_files(root, skip, link, [".foundation/bin"]):
            if rel.startswith(".foundation/convergence/round-"):
                continue  # 収束テストの生データ（エージェントの差分）は検査しない
            text = _lib.read_text(root / rel)
            if text and _lib.TODO_MARKER in text:
                errors.append(f"{rel}: {_lib.TODO_MARKER} が {text.count(_lib.TODO_MARKER)} 件残っています")
        for required in ["docs/design/overview.md", "docs/design/architecture.md", "docs/design/research.md",
                         "docs/design/convergence-report.md", "AGENTS.md", "CLAUDE.md"]:
            if not (root / required).is_file():
                errors.append(f"{required} がありません")

    if phase >= 4:
        matrix = build_matrix(rows, excluded)
        if args.no_write:
            current = matrix_path.read_text(encoding="utf-8") if matrix_path.is_file() else ""
            if current != matrix:
                errors.append("enforcement-matrix.md が最新ではありません。--no-write を外して rules_check.py を実行してください")
        elif not errors:
            matrix_path.write_text(matrix, encoding="utf-8")

    for warning in warnings:
        print(f"WARN {warning}")
    for error in errors:
        print(f"ERROR {error}")
    active = [r for r in rows if not r["retired"]]
    counts = {level: sum(1 for r in active if r["levels"] and r["levels"][0] == level) for level in LEVELS}
    summary = "、".join(f"{k} {v}" for k, v in counts.items() if v)
    print(f"[phase {phase}{' final' if args.final else ''}] ルール {len(active)} 件（{summary}）、"
          f"probe {len(probes)} 件（結果: {results_note}）、エラー {len(errors)} 件、警告 {len(warnings)} 件")
    if errors:
        if phase >= 4 and not args.no_write:
            print("エラーがあるため enforcement-matrix.md は書き換えていません")
        return 1
    return 0


def build_matrix(rows, excluded) -> str:
    active = [r for r in rows if not r["retired"]]
    lines = [GENERATED_HEADER, "", "# 強制の対応表", "",
             "ルールごとに、どの仕組みで守らせているかを示す。段の強さは type > format > lint・structure・test > generator > review > doc の順である。",
             "probe が実際に検査で落ちるかの結果は `.foundation/probe-results.json` にある（`violation_probe.py` が書く）。",
             "", "## 集計（各ルールの最も強い段で数える）", "", "| 段 | 件数 |", "|---|---|"]
    for level in LEVELS:
        lines.append(f"| {level} | {sum(1 for r in active if r['levels'] and r['levels'][0] == level)} |")
    lines += ["", "## ルールごとの対応", "",
              "| ルールID | 題名 | 強制 | 仕組み | probe |", "|---|---|---|---|---|"]
    for r in rows:
        probes = "、".join(r["probes"]) or "—"
        levels = ", ".join(r["levels"]) or "—"
        lines.append(f"| {r['id']} | {_cell(r['title'])} | {levels} | {_cell(r['desc']) or '—'} | {probes} |")
    lines += ["", "## 機械で縛っていないルール", "", "| ルールID | 題名 | 強制 | 機械化しない理由 |", "|---|---|---|---|"]
    for r in active:
        if not set(r["levels"]) & set(MACHINE):
            lines.append(f"| {r['id']} | {_cell(r['title'])} | {', '.join(r['levels'])} | {_cell(r['reason'])} |")
    lines += ["", "## 対象外とした軸", "", "| 軸 | 理由 |", "|---|---|"]
    for axis in sorted(excluded, key=lambda a: (a[0], int(re.sub(r'\D', '', a) or 0))):
        lines.append(f"| {axis} | {_cell(excluded[axis])} |")
    return "\n".join(lines) + "\n"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


if __name__ == "__main__":
    sys.exit(main())
