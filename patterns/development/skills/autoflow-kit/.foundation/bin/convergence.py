#!/usr/bin/env python3
"""収束テスト: 独立エージェントに同じ課題を解かせ、書き方の違い（揺れ）を測る。

サブコマンド:
  prepare        課題ごとに基盤のコピーを人数分作り、plan.json を書く
  review-prepare 違反を仕込んだ差分（review-seeds.json）を置いたコピーを人数分作り、plan-review.json を書く
  run            plan の各コピーで runner（既定: claude -p）を実行し、結果を _results/ に保存する
  diff           課題ごとにコピー同士を比べ、指標とレポート（report.json / report.md / *.patch）を書く
  review-score   レビュー結果に含まれるルールIDを数え、検出率を採点する

例:
  python3 convergence.py prepare --root . --round 1
  python3 convergence.py run --workdir <W> --round 1
  python3 convergence.py diff --workdir <W> --round 1 --out .foundation/convergence/round-1 --check
"""

from __future__ import annotations

import argparse
import difflib
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
RULE_ID = re.compile(r"(?<![A-Z])[A-Z]{2,6}-\d{2,3}(?![\d-])")
MAX_TEXT_BYTES = 1_000_000

AGENT_TOOL_IMPL = """あなたは、このリポジトリを初めて触る開発者です。作業ディレクトリは {dir} です。
このディレクトリの外のファイルを読んだり書いたりしてはいけません。
まず {dir}/CLAUDE.md を読み、そこから辿れる指示（AGENTS.md、.claude/skills/ のスキル）に従って、次の依頼を最後まで実装してください。
質問はできません。依頼から決まらないことは、リポジトリの指示にある既定値に従ってください。

依頼:
{prompt}"""

AGENT_TOOL_REVIEW = """あなたは、このリポジトリを初めて触るレビュアーです。作業ディレクトリは {dir} です。
このディレクトリの外のファイルを読んだり書いたりしてはいけません（下の保存先を除く）。
まず {dir}/CLAUDE.md を読み、そこから辿れる指示（AGENTS.md、.claude/skills/ のスキル）に従って、次の依頼に応えてください。
最後に、レビュー結果の全文を {result} に保存してください。

依頼:
{prompt}"""


def default_workdir(name: str) -> Path:
    return Path(tempfile.gettempdir()) / "pattern-foundation" / name


def round_dir(workdir: Path, rnd: int) -> Path:
    return workdir / f"round-{rnd}"


def safe(run_id: str) -> str:
    return run_id.replace("/", "__")


# ---------------------------------------------------------------- prepare

# コピーに入れないもの。前のラウンドの差分・課題一覧（ホールドアウトを含む）・レビューの正解表が
# エージェントに見えると独立性が崩れ、前のラウンドの識別子が「既存の名前」に数えられて names が水増しされる
COPY_EXCLUDE = [".foundation/convergence", ".foundation/probe-results.json"]


def cmd_prepare(args) -> int:
    root = _lib.resolve_root(args.root)
    manifest = _lib.load_manifest(root)
    conv = manifest.get("convergence", {})
    agents = args.agents or conv.get("agents", 3)
    tasks_path = Path(args.tasks).resolve() if args.tasks else root / ".foundation/convergence/tasks.json"
    tasks = _lib.load_json(tasks_path).get("tasks", [])
    if args.only_tasks:
        wanted = set(args.only_tasks.split(","))
        tasks = [t for t in tasks if t.get("id") in wanted]
    elif not args.include_holdout:
        tasks = [t for t in tasks if t.get("kind") != "holdout"]
    for task in tasks:
        if _lib.TODO_MARKER in task.get("prompt", ""):
            _lib.fail(f"課題 {task.get('id')} の prompt がひな形のままです")
    if not tasks:
        _lib.fail("課題が0件です")

    workdir = Path(args.workdir).resolve() if args.workdir else default_workdir(manifest["name"])
    rdir = round_dir(workdir, args.round)
    if (rdir / "plan.json").exists():
        if not args.force:
            _lib.fail(f"{rdir} は準備済みです（作り直すなら --force）")
        shutil.rmtree(rdir)
    skip, link = _lib.copy_settings(manifest)
    runs, bases = [], {}
    for task in tasks:
        tid = task["id"]
        base = rdir / tid / "base"
        _lib.copy_project(root, base, skip, link, COPY_EXCLUDE)
        bases[tid] = str(base)
        for k in range(1, agents + 1):
            run_id = f"{tid}/agent-{k}"
            target = rdir / tid / f"agent-{k}"
            _lib.copy_project(base, target, skip, [])  # base 内の依存はリンク済みなのでそのまま写す
            _lib.git_snapshot(target)
            runs.append({"id": run_id, "task": tid, "dir": str(target), "prompt": task["prompt"],
                         "agent_tool_prompt": AGENT_TOOL_IMPL.format(dir=target, prompt=task["prompt"])})
    plan = {"kind": "impl", "round": args.round, "root": str(root), "name": manifest["name"],
            "agents": agents, "tasks": [t["id"] for t in tasks], "bases": bases, "runs": runs}
    _lib.write_json(rdir / "plan.json", plan)
    print(f"準備しました: {rdir}")
    print(f"課題 {len(tasks)} 件 × エージェント {agents} 人 = セッション {len(runs)} 回")
    print(f"次: python3 {Path(__file__).name} run --workdir {workdir} --round {args.round}")
    return 0


def cmd_review_prepare(args) -> int:
    root = _lib.resolve_root(args.root)
    manifest = _lib.load_manifest(root)
    agents = args.agents or manifest.get("convergence", {}).get("agents", 3)
    seeds_path = Path(args.seeds).resolve() if args.seeds else root / ".foundation/convergence/review-seeds.json"
    seeds_doc = _lib.load_json(seeds_path)
    seeds = seeds_doc.get("probes", [])
    if not seeds:
        _lib.fail("review-seeds.json の probes が0件です")
    prompt = seeds_doc.get("prompt") or "未コミットの変更をレビューして"
    workdir = Path(args.workdir).resolve() if args.workdir else default_workdir(manifest["name"])
    rdir = round_dir(workdir, args.round)
    review_root = rdir / "review"
    if review_root.exists():
        if not args.force:
            _lib.fail(f"{review_root} は準備済みです（作り直すなら --force）")
        shutil.rmtree(review_root)
    changes = [c for seed in seeds for c in seed.get("files", [])]
    paths = [c.get("path") for c in changes]
    clashing = sorted({c.get("path") for c in changes
                       if paths.count(c.get("path")) > 1 and c.get("mode", "create") != "append"})
    if clashing:
        _lib.fail(f"review-seeds.json で複数の seed が同じファイルを作成・置換しています: {', '.join(clashing)}。"
                  "後の seed が前の違反を消すので、別のファイルに分けてください")
    skip, link = _lib.copy_settings(manifest)
    runs = []
    for k in range(1, agents + 1):
        target = review_root / f"agent-{k}"
        _lib.copy_project(root, target, skip, link, COPY_EXCLUDE)
        if not _lib.git_snapshot(target):
            _lib.fail("review-prepare には git が必要です（基準のコミットの上に違反を未コミットで置くため）")
        for seed in seeds:
            for change in seed.get("files", []):
                try:
                    _lib.apply_file_change(target, change)
                except ValueError as exc:
                    _lib.fail(f"seed {seed.get('id')} を適用できません: {exc}")
        run_id = f"review/agent-{k}"
        result_file = rdir / "_results" / f"{safe(run_id)}.md"
        runs.append({"id": run_id, "task": "review", "dir": str(target), "prompt": prompt,
                     "agent_tool_prompt": AGENT_TOOL_REVIEW.format(dir=target, prompt=prompt, result=result_file)})
    expected = sorted({s.get("rule") for s in seeds if s.get("rule")})
    plan = {"kind": "review", "round": args.round, "root": str(root), "name": manifest["name"],
            "agents": agents, "expected": expected, "seeds": [s.get("id") for s in seeds], "runs": runs}
    _lib.write_json(rdir / "plan-review.json", plan)
    print(f"準備しました: {review_root}（seed {len(seeds)} 件、期待するルールID {len(expected)} 件、エージェント {agents} 人）")
    return 0


# ---------------------------------------------------------------- run

def cmd_run(args) -> int:
    workdir = Path(args.workdir).resolve()
    rdir = round_dir(workdir, args.round)
    plan = _lib.load_json(rdir / ("plan-review.json" if args.kind == "review" else "plan.json"))
    manifest = _lib.load_manifest(Path(plan["root"]))
    conv = manifest.get("convergence", {})
    runner = json.loads(args.runner) if args.runner else conv.get("runner")
    if not runner or "{prompt}" not in " ".join(runner):
        _lib.fail("runner がありません。manifest の convergence.runner に {prompt} を含むコマンド配列を書いてください")
    if shutil.which(runner[0]) is None:
        _lib.fail(f"{runner[0]} が見つかりません。Agent ツールで代わりに実行する場合は plan の agent_tool_prompt を使ってください")
    timeout = args.timeout or conv.get("timeout_sec", 1800)
    parallel = args.parallel or conv.get("parallel", 3)
    runs = plan["runs"]
    if args.only:
        wanted = set(args.only.split(","))
        runs = [r for r in runs if r["id"] in wanted]
    results_dir = rdir / "_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}  # 入れ子のセッションとして扱われないようにする

    def execute(run: dict) -> tuple[str, int, float]:
        command = [arg.replace("{prompt}", run["prompt"]) for arg in runner]
        started = time.monotonic()
        try:
            proc = subprocess.run(command, cwd=run["dir"], capture_output=True, text=True, timeout=timeout, env=env)
            code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            code = 124
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = f"[timeout] {timeout} 秒で打ち切りました"
        elapsed = time.monotonic() - started
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = None
        record = {"id": run["id"], "exit": code, "seconds": round(elapsed, 1),
                  "output": parsed if parsed is not None else None,
                  "stdout": None if parsed is not None else stdout, "stderr_tail": _lib.tail(stderr, 30)}
        _lib.write_json(results_dir / f"{safe(run['id'])}.json", record)
        cost = parsed.get("total_cost_usd") if isinstance(parsed, dict) else None
        return run["id"], code, elapsed, cost

    print(f"{len(runs)} 件を最大 {parallel} 並列で実行します（1件の上限 {timeout} 秒）")
    failed, total_cost = 0, 0.0
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        for run_id, code, elapsed, cost in pool.map(execute, runs):
            failed += code != 0
            total_cost += cost or 0.0
            cost_text = f"、${cost:.3f}" if cost is not None else ""
            print(f"{'完了' if code == 0 else '失敗'}  {run_id}  終了コード {code}（{elapsed:.0f} 秒{cost_text}）")
    if total_cost:
        print(f"費用の合計（runner が報告した値）: ${total_cost:.3f}")
    print(f"結果: {results_dir}")
    return 1 if failed else 0


# ---------------------------------------------------------------- diff

def snapshot(directory: Path, skip: list[str], link: list[str]) -> dict[str, bytes]:
    files = {}
    for rel in _lib.iter_files(directory, skip, link):
        full = directory / rel
        if full.stat().st_size <= MAX_TEXT_BYTES:
            files[rel] = full.read_bytes()
        else:
            files[rel] = _lib.sha256_file(full).encode()
    return files


def git_changed(directory: Path) -> set[str] | None:
    """git のコピーなら、.gitignore を反映した変更ファイル（追跡中の変更・削除と未追跡）を返す。"""
    if not (directory / ".git").is_dir() or shutil.which("git") is None:
        return None
    proc = subprocess.run(["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
                          cwd=directory, capture_output=True)
    if proc.returncode != 0:
        return None
    changed, entries = set(), proc.stdout.decode("utf-8", "replace").split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        if len(entry) > 3:
            status, path = entry[:2], entry[3:]
            changed.add(path)
            if "R" in status or "C" in status:  # 名前の変更は、次の要素が元のパス
                i += 1
                if i < len(entries) and entries[i]:
                    changed.add(entries[i])
        i += 1
    return changed


def decode(data: bytes | None) -> str | None:
    if data is None or b"\0" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def normalized_lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.splitlines() if line.strip()]


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def cmd_diff(args) -> int:
    workdir = Path(args.workdir).resolve()
    rdir = round_dir(workdir, args.round)
    plan = _lib.load_json(rdir / "plan.json")
    root = Path(plan["root"])
    manifest = _lib.load_manifest(root)
    conv = manifest.get("convergence", {})
    thresholds = {"files": 1.0, "names": 0.8, "content": 0.0, **conv.get("thresholds", {})}
    skip, link = _lib.copy_settings(manifest)
    ignore = conv.get("ignore", [])
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    check_command = manifest.get("commands", {}).get("check")
    protected_globs = manifest.get("protected", [])

    report = {"round": plan["round"], "thresholds": thresholds, "tasks": []}
    for tid in plan["tasks"]:
        base_dir = Path(plan["bases"][tid])
        base = snapshot(base_dir, skip, link)
        base_idents = set()
        for data in base.values():
            text = decode(data)
            if text:
                base_idents.update(IDENT.findall(text))
        agents = sorted([r for r in plan["runs"] if r["task"] == tid], key=lambda r: r["id"])
        changes, versions, idents, checks = {}, {}, {}, {}
        for run in agents:
            name = run["id"].split("/")[-1]
            current = snapshot(Path(run["dir"]), skip, link)
            from_git = git_changed(Path(run["dir"]))
            candidates = from_git if from_git is not None else set(base) | set(current)
            changed = sorted(p for p in candidates
                             if base.get(p) != current.get(p) and not _lib.matches_any(p, ignore))
            changes[name] = set(changed)
            versions[name] = {p: current.get(p) for p in changed}
            new_idents = set()
            for p in changed:
                text = decode(current.get(p))
                if text:
                    new_idents.update(i for i in IDENT.findall(text) if i not in base_idents)
            idents[name] = new_idents
            patch = []
            for p in changed:
                before, after = decode(base.get(p)), decode(current.get(p))
                if before is None and base.get(p) is not None or after is None and current.get(p) is not None:
                    patch.append(f"Binary or large file differs: {p}\n")
                    continue
                patch.extend(difflib.unified_diff((before or "").splitlines(True), (after or "").splitlines(True),
                                                  f"a/{p}" if p in base else "/dev/null",
                                                  f"b/{p}" if p in current else "/dev/null"))
            task_out = out / tid
            task_out.mkdir(parents=True, exist_ok=True)
            (task_out / f"{name}.patch").write_text("".join(patch), encoding="utf-8")
            if args.check and check_command:
                code, output = _lib.run_shell(check_command, Path(run["dir"]), args.check_timeout)
                checks[name] = {"exit": code, "tail": "" if code == 0 else _lib.tail(output, 20)}

        names = sorted(changes)
        pairs = list(itertools.combinations(names, 2))
        files_score = mean([jaccard(changes[a], changes[b]) for a, b in pairs]) if pairs else 1.0
        names_score = mean([jaccard(idents[a], idents[b]) for a, b in pairs]) if pairs else 1.0
        file_scores = []
        all_paths = sorted(set().union(*changes.values())) if changes else []
        for p in all_paths:
            holders = [n for n in names if p in changes[n] and decode(versions[n].get(p)) is not None]
            if len(holders) < 2:
                continue
            sims = []
            for a, b in itertools.combinations(holders, 2):
                la, lb = normalized_lines(decode(versions[a][p])), normalized_lines(decode(versions[b][p]))
                sims.append((difflib.SequenceMatcher(None, la, lb, autojunk=False).ratio(), a, b))
            worst = min(sims)
            file_scores.append({"path": p, "similarity": round(sum(s[0] for s in sims) / len(sims), 3),
                                "worst_pair": [worst[1], worst[2]], "worst": round(worst[0], 3)})
        content_score = mean([f["similarity"] for f in file_scores])
        partial_paths = [{"path": p, "agents": [n for n in names if p in changes[n]]}
                         for p in all_paths if 0 < sum(p in changes[n] for n in names) < len(names)]
        common_idents = set.intersection(*idents.values()) if idents else set()
        partial_idents = {n: sorted(idents[n] - common_idents) for n in names}
        check_ok = all(c["exit"] == 0 for c in checks.values()) if checks else None
        # 保護ファイルの変更は、設定やルールを緩めて検査を通した疑いがある（hooks が効かない実行方法では特に）
        protected = {n: sorted(p for p in changes[n] if _lib.matches_any(p, protected_globs)) for n in names}
        protected = {n: v for n, v in protected.items() if v}
        converged = (not protected and files_score is not None and files_score >= thresholds["files"]
                     and names_score is not None and names_score >= thresholds["names"]
                     and (content_score is None or content_score >= thresholds["content"])
                     and check_ok is not False)
        excerpts = []
        differing = [f for f in file_scores if f["worst"] < 1.0]
        for f in sorted(differing, key=lambda x: (x["similarity"], x["path"]))[:5]:
            a, b = f["worst_pair"]
            diff = list(difflib.unified_diff(decode(versions[a][f["path"]]).splitlines(),
                                             decode(versions[b][f["path"]]).splitlines(),
                                             f"{a}/{f['path']}", f"{b}/{f['path']}", lineterm=""))
            excerpts.append({"path": f["path"], "pair": [a, b], "similarity": f["worst"], "diff": diff[:80]})
        report["tasks"].append({
            "id": tid, "agents": names, "files": files_score, "names": names_score, "content": content_score,
            "check": {n: checks[n]["exit"] for n in sorted(checks)} if checks else None, "converged": converged,
            "changed_files": {n: sorted(changes[n]) for n in names}, "partial_files": partial_paths,
            "common_new_names": len(common_idents), "partial_new_names": partial_idents,
            "file_similarity": sorted(file_scores, key=lambda x: x["path"]), "excerpts": excerpts,
            "check_failures": {n: checks[n]["tail"] for n in sorted(checks) if checks[n]["exit"] != 0},
            "protected_changes": protected,
        })
    _lib.write_json(out / "report.json", report)
    (out / "report.md").write_text(render_report(report), encoding="utf-8")
    print(render_summary(report))
    print(f"レポート: {out / 'report.md'}")
    return 0 if all(t["converged"] for t in report["tasks"]) else 1


def fmt(value) -> str:
    return "—" if value is None else f"{value:.3f}"


def render_summary(report: dict) -> str:
    lines = ["| 課題 | files | names | content | check | 保護 | 基準 |", "|---|---|---|---|---|---|---|"]
    for t in report["tasks"]:
        check = "—" if t["check"] is None else ("全員通過" if all(v == 0 for v in t["check"].values())
                                               else "失敗あり")
        guarded = "変更あり" if t["protected_changes"] else "—"
        lines.append(f"| {t['id']} | {fmt(t['files'])} | {fmt(t['names'])} | {fmt(t['content'])} | {check} | "
                     f"{guarded} | {'満たす' if t['converged'] else '満たさない'} |")
    return "\n".join(lines)


def render_report(report: dict) -> str:
    th = report["thresholds"]
    lines = [f"# 収束テスト ラウンド {report['round']} のレポート", "",
             "このファイルは convergence.py diff が生成する。揺れの分類（R1〜R7）と対処は convergence-report.md に書く。", "",
             f"基準: files ≥ {th['files']}、names ≥ {th['names']}、content ≥ {th['content']}、check は全員通過、"
             "保護ファイルの変更なし", "",
             "## 指標", "", render_summary(report)]
    for t in report["tasks"]:
        lines += ["", f"## {t['id']}", "", "### 一部のエージェントだけが作った・変えたファイル", ""]
        if t["partial_files"]:
            lines += ["| ファイル | " + " | ".join(t["agents"]) + " |", "|---|" + "---|" * len(t["agents"])]
            for item in t["partial_files"]:
                marks = " | ".join("✓" if n in item["agents"] else "–" for n in t["agents"])
                lines.append(f"| `{item['path']}` | {marks} |")
        else:
            lines.append("なし（全員が同じファイルの集合を変えた）")
        lines += ["", f"### 一部のエージェントだけが作った名前（全員に共通の新しい名前は {t['common_new_names']} 個）", ""]
        any_partial = False
        for name, idents in t["partial_new_names"].items():
            if idents:
                any_partial = True
                shown = ", ".join(f"`{i}`" for i in idents[:40])
                more = f" ほか {len(idents) - 40} 個" if len(idents) > 40 else ""
                lines.append(f"- {name}: {shown}{more}")
        if not any_partial:
            lines.append("なし")
        lines += ["", "### 内容の類似度が低いファイル", ""]
        if t["excerpts"]:
            for ex in t["excerpts"]:
                lines += [f"#### `{ex['path']}`（{ex['pair'][0]} と {ex['pair'][1]}、類似度 {ex['similarity']:.3f}）", "",
                          "```diff", *ex["diff"], "```", ""]
        elif t["file_similarity"]:
            lines.append("なし（共通して変えたファイルの中身は全員一致）")
        else:
            lines.append("共通して変えたテキストファイルがありません")
        if t["protected_changes"]:
            lines += ["", "### 保護ファイルを変えたエージェント（基準を満たさない扱い。設定やルールの緩和でないか差分を確かめる）", ""]
            for name, paths in t["protected_changes"].items():
                lines.append(f"- {name}: " + ", ".join(f"`{p}`" for p in paths))
        if t["check_failures"]:
            lines += ["", "### check に失敗したエージェント", ""]
            for name, out in t["check_failures"].items():
                lines += [f"#### {name}", "", "```", out, "```", ""]
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------- review-score

def review_text(results_dir: Path, run_id: str) -> str | None:
    json_path = results_dir / f"{safe(run_id)}.json"
    for path in (results_dir / f"{safe(run_id)}.md", results_dir / f"{safe(run_id)}.txt"):
        if path.is_file():
            return path.read_text(encoding="utf-8")
    if json_path.is_file():
        record = _lib.load_json(json_path)
        output = record.get("output")
        if isinstance(output, dict):
            return str(output.get("result", ""))
        return record.get("stdout") or ""
    return None


def cmd_review_score(args) -> int:
    workdir = Path(args.workdir).resolve()
    rdir = round_dir(workdir, args.round)
    plan = _lib.load_json(rdir / "plan-review.json")
    expected = set(plan["expected"])
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows, detected_sets = [], []
    for run in sorted(plan["runs"], key=lambda r: r["id"]):
        text = review_text(rdir / "_results", run["id"])
        if text is None:
            rows.append({"agent": run["id"], "missing": True})
            continue
        found = set(RULE_ID.findall(text))
        detected = expected & found
        detected_sets.append(frozenset(detected))
        verdict = "差し戻し" if "差し戻し" in text else ("承認" if "承認" in text else "不明")
        rows.append({"agent": run["id"], "missing": False, "recall": round(len(detected) / len(expected), 3) if expected else 1.0,
                     "detected": sorted(detected), "missed": sorted(expected - found),
                     "extra": sorted(found - expected), "verdict": verdict})
    agreement = len(set(detected_sets)) <= 1 and len(detected_sets) == len(plan["runs"])
    result = {"round": plan["round"], "expected": sorted(expected), "agents": rows, "agreement": agreement}
    _lib.write_json(out / "review-report.json", result)
    lines = [f"# レビュー検出率 ラウンド {plan['round']}", "", f"仕込んだ違反のルールID: {', '.join(sorted(expected))}", "",
             "| エージェント | 検出率 | 見逃し | 余計なルールID | 判定 |", "|---|---|---|---|---|"]
    for r in rows:
        if r["missing"]:
            lines.append(f"| {r['agent']} | 結果なし | — | — | — |")
        else:
            lines.append(f"| {r['agent']} | {r['recall']:.3f} | {', '.join(r['missed']) or 'なし'} | "
                         f"{', '.join(r['extra']) or 'なし'} | {r['verdict']} |")
    lines += ["", f"エージェント間で検出したルールIDの集合が一致: {'はい' if agreement else 'いいえ'}"]
    (out / "review-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    ok = agreement and all(not r["missing"] and r["recall"] == 1.0 and r["verdict"] == "差し戻し" for r in rows)
    return 0 if ok else 1


# ---------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prepare", help="課題ごとに基盤のコピーを人数分作る")
    p.add_argument("--root")
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--tasks")
    p.add_argument("--agents", type=int)
    p.add_argument("--include-holdout", action="store_true")
    p.add_argument("--only-tasks", help="カンマ区切りの課題ID")
    p.add_argument("--workdir")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_prepare)

    p = sub.add_parser("review-prepare", help="違反を仕込んだコピーを人数分作る")
    p.add_argument("--root")
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--seeds")
    p.add_argument("--agents", type=int)
    p.add_argument("--workdir")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_review_prepare)

    p = sub.add_parser("run", help="runner（既定: claude -p）を各コピーで実行する")
    p.add_argument("--workdir", required=True)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--kind", choices=["impl", "review"], default="impl")
    p.add_argument("--parallel", type=int)
    p.add_argument("--timeout", type=int)
    p.add_argument("--runner", help="manifest の runner を上書きする JSON 配列")
    p.add_argument("--only", help="カンマ区切りの実行ID")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("diff", help="揺れを計測してレポートを書く")
    p.add_argument("--workdir", required=True)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--check", action="store_true", help="各コピーで commands.check を実行する")
    p.add_argument("--check-timeout", type=int, default=900)
    p.set_defaults(func=cmd_diff)

    p = sub.add_parser("review-score", help="レビュー検出率を採点する")
    p.add_argument("--workdir", required=True)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_review_score)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
