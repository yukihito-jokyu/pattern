"""Silent, fail-open native-hook collector for local macOS/Linux sessions."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shlex
import stat
import sys
import time
from pathlib import Path

from event_model import INTENT_EVENT, LOCK_TIMEOUT_SEC, MAX_INPUT_BYTES, SOURCE_EVENTS, normalize, safe_id, utc_now


def open_private(path: Path, flags: int) -> int:
    fd = os.open(str(path), flags | os.O_NOFOLLOW, 0o600)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise ValueError("STATE-01 regular file required")
    os.fchmod(fd, 0o600)
    return fd


def acquire_lock(fd: int) -> None:
    deadline = time.monotonic() + LOCK_TIMEOUT_SEC
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise TimeoutError("ASYNC-01 lock timeout")
            time.sleep(0.01)


def append_event(payload: dict, source: str, log_dir: Path) -> Path:
    observed_at = utc_now()
    if log_dir.is_symlink():
        raise ValueError("STATE-01 symlink log directory refused")
    log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_fd = open_private(log_dir / ".writer.lock", os.O_CREAT | os.O_RDWR)
    try:
        acquire_lock(lock_fd)
        key_fd = open_private(log_dir / ".fingerprint-key", os.O_CREAT | os.O_RDWR)
        try:
            key = os.read(key_fd, 33)
            if not key:
                key = os.urandom(32)
                if os.write(key_fd, key) != 32:
                    raise OSError("short key write")
            if len(key) != 32:
                raise ValueError("OPS-01 invalid fingerprint key")
        finally:
            os.close(key_fd)
        event = normalize(payload, source, key, observed_at)
        session_hash = hashlib.sha256(event["session_id"].encode()).hexdigest()[:32]
        filename = source + "-" + observed_at[:10] + "-" + session_hash + ".jsonl"
        path = log_dir / filename
        data = (json.dumps(event, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
                + "\n").encode("utf-8")
        log_fd = open_private(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY)
        try:
            offset = 0
            while offset < len(data):
                written = os.write(log_fd, data[offset:])
                if not written:
                    raise OSError("short log write")
                offset += written
        finally:
            os.close(log_fd)
        return path
    finally:
        os.close(lock_fd)


def intent_context(payload: dict, source: str, log_dir: Path) -> dict:
    example = {"session_id": safe_id(payload.get("session_id")),
               "turn_id": safe_id(payload.get("turn_id")), "agent_id": safe_id(payload.get("agent_id")),
               "tool_name": "Read", "tool_input": {"file_path": str(log_dir.resolve().parent / "src/auth.ts")},
               "purpose": "認証エラーの原因を確認する", "expected": "認証処理の条件を確認できる"}
    command = " ".join(shlex.quote(str(value)) for value in (
        Path(sys.executable).resolve(), Path(__file__).resolve(), "--intent", "--source", source,
        "--log-dir", log_dir.resolve(),
    ))
    text = ("このプロジェクトでは操作・目的・結果を記録します。内部の思考過程ではなく、操作の目的を短く明示してください。"
            "Bash等にdescriptionを渡せる場合は、何のために行うかをdescriptionへ書いてください。"
            "説明欄がないツールは、実行直前に次のコマンドへJSONをstdinで渡して目的を記録してください: "
            + command + "\nJSONの例: " + json.dumps(example, ensure_ascii=False)
            + "\ntool_nameとdescription以外のtool_inputは次のhook入力と一致させ、session_id・turn_id・agent_idは例の値を使います。"
            "Codexのシェル実行はhook上の名前Bash、入力キーcommandを使います。"
            "ClaudeのRead/Write/Editのパスはhookが絶対パスへ展開するため、絶対パスで指定してください。"
            "有効期限は5分、1記録は次の一致する1操作だけに対応します。"
            "目的の記録コマンド自身には追加の目的記録は不要です。説明できない理由を推測して埋めないでください。")
    return {"hookSpecificOutput": {"hookEventName": payload["hook_event_name"], "additionalContext": text}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, choices=tuple(SOURCE_EVENTS))
    parser.add_argument("--log-dir", type=Path, default=Path(".agent-logs"))
    parser.add_argument("--intent", action="store_true", help="Record a declared purpose for the next exact tool input")
    parser.add_argument("--context", action="store_true", help="Add purpose-recording instructions at prompt/subagent start")
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError("ERR-02 input too large")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("ERR-02 object required")
        if args.intent:
            payload["hook_event_name"] = INTENT_EVENT
        append_event(payload, args.source, args.log_dir)
        if args.context and not args.intent and payload["hook_event_name"] in ("UserPromptSubmit", "SubagentStart"):
            print(json.dumps(intent_context(payload, args.source, args.log_dir), ensure_ascii=False))
    except Exception:
        # Never print the exception: its message can include the original input.
        print("observer: recording failed; event not saved", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
