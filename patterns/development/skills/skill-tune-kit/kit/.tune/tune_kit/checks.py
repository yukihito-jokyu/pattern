"""検査の種類の一覧と、機械で判定する種類の評価を受け持つ。副作用は持たない。"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

RESPONSE_TARGET = "response"
FILE_TARGET_PREFIX = "file:"
DETAIL_LIMIT = 300


@dataclass(frozen=True)
class Kind:
    """検査の種類。required は検査に必須の項目、judge は採点役が判定するか。"""

    name: str
    judge: bool
    required: tuple[str, ...]
    optional: tuple[str, ...]
    expected: str
    summary: str
    example: str


# 検査の種類。足すときは plan.py の検証、test_checks.py の test_kind_<種類>、make docs を一緒に変える（PROC-02）
KINDS: dict[str, Kind] = {
    "contains": Kind(
        name="contains",
        judge=False,
        required=("value",),
        optional=("target",),
        expected="使わない",
        summary="対象の文字列に value が含まれる（NFKC で正規化し、空白の並びを1つにして比べる）",
        example='{"id": "K1", "kind": "contains", "severity": "must", "value": "2026-01-05"}',
    ),
    "not_contains": Kind(
        name="not_contains",
        judge=False,
        required=("value",),
        optional=("target",),
        expected="使わない",
        summary="対象の文字列に value が含まれない（比べ方は contains と同じ）",
        example='{"id": "K2", "kind": "not_contains", "severity": "must", "value": "TODO"}',
    ),
    "regex": Kind(
        name="regex",
        judge=False,
        required=("pattern",),
        optional=("target",),
        expected="使わない",
        summary="対象の文字列のどこかが正規表現 pattern に一致する（Python の re.search、複数行モード）",
        example='{"id": "K3", "kind": "regex", "severity": "should", "pattern": "^## 概要$"}',
    ),
    "equals": Kind(
        name="equals",
        judge=False,
        required=(),
        optional=("target", "value", "expected_file"),
        expected="value、expected_file、ケースの expected の順に、最初にあるものを正解にする",
        summary="対象の文字列が正解と一致する（NFKC で正規化し、行末の空白と前後の空行を除いて比べる）",
        example='{"id": "K4", "kind": "equals", "severity": "must", "target": "file:out/result.txt"}',
    ),
    "json_equals": Kind(
        name="json_equals",
        judge=False,
        required=(),
        optional=("target", "value", "expected_file"),
        expected="equals と同じ",
        summary="対象の文字列と正解を JSON として読み、値が等しい（キーの順と空白は問わない）",
        example='{"id": "K5", "kind": "json_equals", "severity": "must", "target": "file:out/data.json"}',
    ),
    "exists": Kind(
        name="exists",
        judge=False,
        required=("target",),
        optional=(),
        expected="使わない",
        summary="target に書いたファイル（file:<sandbox からの相対パス>）がある",
        example='{"id": "K6", "kind": "exists", "severity": "must", "target": "file:docs/summary.md"}',
    ),
    "command": Kind(
        name="command",
        judge=False,
        required=("run",),
        optional=(),
        expected="使わない",
        summary="sandbox でシェルのコマンド run を実行し、終了コードが 0 になる（300秒で打ち切り）",
        example='{"id": "K7", "kind": "command", "severity": "must", "run": "python3 -m unittest"}',
    ),
    "judge": Kind(
        name="judge",
        judge=True,
        required=("criterion",),
        optional=("use_expected",),
        expected="use_expected が true なら、ケースの expected と expected/ のファイルを採点役に見せる",
        summary="採点役が criterion の文を満たすかを判定する。2人の採点役が同じ判定をできる1文で書く",
        example='{"id": "Q1", "kind": "judge", "severity": "must", "criterion": "依頼の日付を全部変換している"}',
    ),
}


@dataclass(frozen=True)
class Outcome:
    passed: bool
    detail: str


def build_normalized(text: str) -> str:
    """NFKC で正規化し、改行を LF にそろえ、行末の空白と前後の空行を除く。"""
    lines = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip("\n")


def build_collapsed(text: str) -> str:
    """build_normalized に加えて、空白の並び（改行を含む）を1つの空白にする。"""
    return " ".join(build_normalized(text).split())


def _build_excerpt(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= DETAIL_LIMIT else flat[:DETAIL_LIMIT] + "…"


def evaluate_contains(text: str, value: str) -> Outcome:
    if build_collapsed(value) in build_collapsed(text):
        return Outcome(passed=True, detail=f"「{_build_excerpt(value)}」がある")
    return Outcome(passed=False, detail=f"「{_build_excerpt(value)}」が無い")


def evaluate_not_contains(text: str, value: str) -> Outcome:
    if build_collapsed(value) in build_collapsed(text):
        return Outcome(passed=False, detail=f"「{_build_excerpt(value)}」がある")
    return Outcome(passed=True, detail=f"「{_build_excerpt(value)}」が無い")


def evaluate_regex(text: str, pattern: str) -> Outcome:
    match = re.search(pattern, text, re.MULTILINE)
    if match is None:
        return Outcome(passed=False, detail=f"/{pattern}/ に一致する箇所が無い")
    return Outcome(passed=True, detail=f"「{_build_excerpt(match.group(0))}」が一致した")


def evaluate_equals(text: str, expected: str) -> Outcome:
    if build_normalized(text) == build_normalized(expected):
        return Outcome(passed=True, detail="正解と一致した")
    return Outcome(passed=False, detail=f"正解と違う（出力の先頭: 「{_build_excerpt(text)}」）")


def evaluate_json_equals(text: str, expected: str) -> Outcome:
    try:
        actual_value = json.loads(text)
    except json.JSONDecodeError as exc:
        return Outcome(passed=False, detail=f"出力が JSON として読めない（{exc.msg}）")
    try:
        expected_value = json.loads(expected)
    except json.JSONDecodeError as exc:
        return Outcome(passed=False, detail=f"正解が JSON として読めない（{exc.msg}）。監査で正解を直す")
    if actual_value == expected_value:
        return Outcome(passed=True, detail="正解と同じ値だった")
    return Outcome(passed=False, detail=f"正解と違う値だった（出力の先頭: 「{_build_excerpt(text)}」）")


def evaluate_exists(found: bool) -> Outcome:
    return Outcome(passed=found, detail="ファイルがある" if found else "ファイルが無い")


def evaluate_command(code: int, tail: str) -> Outcome:
    if code == 0:
        return Outcome(passed=True, detail="終了コード 0")
    return Outcome(passed=False, detail=f"終了コード {code}: {_build_excerpt(tail)}")


def evaluate_text_check(kind: str, text: str | None, value: str, expected: str | None) -> Outcome:
    """文字列を比べる種類（contains、not_contains、regex、equals、json_equals）を評価する。

    text が None なら対象のファイルが無い。value は contains・not_contains の値か regex の pattern。
    """
    if text is None:
        return Outcome(passed=False, detail="対象のファイルが無い")
    by_value = _VALUE_EVALUATORS.get(kind)
    if by_value is not None:
        return by_value(text, value)
    if expected is None:
        return Outcome(passed=False, detail="正解が無い。計画の検査を直す")
    return evaluate_equals(text, expected) if kind == "equals" else evaluate_json_equals(text, expected)


_VALUE_EVALUATORS: dict[str, Callable[[str, str], Outcome]] = {
    "contains": evaluate_contains,
    "not_contains": evaluate_not_contains,
    "regex": evaluate_regex,
}


def is_valid_pattern(pattern: str) -> bool:
    try:
        re.compile(pattern)
    except re.error:
        return False
    return True
