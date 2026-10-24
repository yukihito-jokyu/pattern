"""テスト用の偽の claude。本物の子プロセスとして動き、依頼文から役割を見分けて決まった振る舞いをする（TEST-02）。

引数のうち `behavior=<名前>` と `log=<パス>` だけを読み、ほかの引数（本物の claude のフラグ）は記録するだけ。
実行（stream-json）では、作業場所に入れたスキルに DELIVER_MARK があれば answer.md を書く。
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

DELIVER_MARK = "答えを answer.md に書く"
REJECTED_MARK = "前の試みは却下された"


def main() -> int:
    argv = sys.argv[1:]
    options = dict(item.split("=", 1) for item in argv if item.startswith(("behavior=", "log=")))
    behaviors = set(options.get("behavior", "").split(","))
    prompt = sys.stdin.read()
    role = _find_role(prompt, argv)
    if "log" in options:
        with Path(options["log"]).open("a", encoding="utf-8") as log:
            log.write(json.dumps({"role": role, "argv": argv}, ensure_ascii=False) + "\n")
    if f"fail-{role}" in behaviors:
        print("偽の claude が失敗した", file=sys.stderr)
        return 1
    if role == "rollout":
        return _run_rollout(prompt, behaviors)
    if role in ("inv", "dom"):
        reply = _run_propose(prompt, behaviors, role)
    elif role == "compose":
        reply = _run_compose(behaviors)
    elif role == "select":
        reply = _run_select(behaviors)
    else:
        reply = _run_reflect(behaviors)
    result = {"type": "result", "subtype": "success", "is_error": False, "num_turns": 2}
    print(json.dumps({**result, "total_cost_usd": 0.02, "result": reply}, ensure_ascii=False))
    return 0


def _find_role(prompt: str, argv: list[str]) -> str:
    if "stream-json" in argv:
        return "rollout"
    if "# あなたの次元：INV" in prompt:
        return "inv"
    if "# あなたの次元：DOM" in prompt:
        return "dom"
    if "```choice" in prompt:
        return "select"
    if "<edits>" in prompt:
        return "reflect"
    return "compose"


def _run_rollout(prompt: str, behaviors: set[str]) -> int:
    skills = sorted(path.parent.name for path in Path(".claude/skills").glob("*/SKILL.md"))
    events: list[dict[str, object]] = [{"type": "system", "subtype": "init", "model": "fake", "skills": skills}]
    if skills and "no-skill" not in behaviors:
        use = {"type": "tool_use", "name": "Skill", "input": {"skill": skills[0]}}
        events.append({"type": "assistant", "message": {"content": [use]}})
        done = {"type": "tool_result", "content": "Launching skill", "is_error": False}
        events.append({"type": "user", "message": {"content": [done]}})
    body = "".join(path.read_text(encoding="utf-8") for path in Path(".claude/skills").rglob("*.md"))
    if DELIVER_MARK in body:
        Path("answer.md").write_text(f"依頼: {prompt.strip()}\n", encoding="utf-8")
    reply = "" if "silent" in behaviors else "作業を終えました"
    events.append({"type": "assistant", "message": {"content": [{"type": "text", "text": reply or "…"}]}})
    events.append(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "num_turns": 3,
            "total_cost_usd": 0.01,
            "permission_denials": [],
            "result": reply,
        }
    )
    for event in events:
        print(json.dumps(event, ensure_ascii=False))
    return 0


def _run_propose(prompt: str, behaviors: set[str], role: str) -> str:
    harness = Path("context/harness")
    if "keep" in behaviors:
        return "<notes>\nKEEP_BASE: 実行どうしに分かれ目が無かった\n</notes>"
    if "off-surface" in behaviors:
        (harness / "notes.txt").write_text("編集面の外\n", encoding="utf-8")
        return "<notes>\nnotes.txt を足した\n</notes>"
    broken = "invalid" in behaviors or ("invalid-once" in behaviors and REJECTED_MARK not in prompt)
    if broken:
        (harness / "scripts").mkdir(exist_ok=True)
        (harness / "scripts" / "check.py").write_text("def broken(:\n", encoding="utf-8")
        return "<notes>\nscripts/check.py を足した\n</notes>"
    shutil.rmtree(harness / "scripts", ignore_errors=True)
    skill = harness / "SKILL.md"
    name = f"references/{role}-check.md"
    skill.write_text(
        skill.read_text(encoding="utf-8").rstrip() + f"\n\n仕上げる前に `{name}` を読み、{DELIVER_MARK}。\n",
        encoding="utf-8",
    )
    (harness / name).write_text(f"# {role} の確かめ\n\n成果物があるかを確かめる。\n", encoding="utf-8")
    return f"<notes>\n{name} を足した: base1 で answer.md が無かった\n</notes>"


def _run_compose(behaviors: set[str]) -> str:
    pool = sorted(path for path in Path("context/pool").glob("*") if path.is_dir())
    if "keep" in behaviors or not pool:
        return "<notes>\nKEEP_BASE\n</notes>"
    shutil.rmtree("context/harness")
    shutil.copytree(pool[0] / "harness", "context/harness")
    return f"<notes>\nkept -> {pool[0].name} の編集 -> 基準の実行 2/2 で answer.md が無かった\n</notes>"


def _run_select(behaviors: set[str]) -> str:
    ids = sorted(path.stem for path in Path("context/candidates").glob("*.md"))
    chosen = "ZZ" if "select-bad" in behaviors else ids[0]
    return f"<why>\nDELIVERY で決めた。\n</why>\n\n```choice\n{chosen}\n```"


def _run_reflect(behaviors: set[str]) -> str:
    edits = "\n".join(
        [
            "<edits>",
            "component: SKILL.md",
            "candidates: inv1",
            "change: 確かめの行",
            "observed: answer.md ができた",
            "verdict: helped",
            "</edits>",
        ]
    )
    if "no-entry" in behaviors:
        return f"{edits}\n\nNO_ENTRY"
    lesson = "\n".join(
        [
            "<experience>",
            "cue: 成果物の書き忘れ",
            "lesson: SKILL.md に仕上げの確かめを足す",
            "evidence: inv1 の行",
            "confidence: low",
            "</experience>",
        ]
    )
    return f"{edits}\n\n{lesson}"


if __name__ == "__main__":
    sys.exit(main())
