"""モデルの返答のタグ（notes、why、choice の囲み、振り返りの表と教訓）を読む。タグはここだけに書く（STATE-02）。"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

NOTES = re.compile(r"<notes>(.*?)</notes>", re.S)
WHY = re.compile(r"<why>(.*?)</why>", re.S)
CHOICE = re.compile(r"```choice[ \t]*\n(.*?)\n?```", re.S)
EDITS = re.compile(r"<edits>(.*?)</edits>", re.S)
EXPERIENCE = re.compile(r"<experience>(.*?)</experience>", re.S)
DECISION = re.compile(r"^\s*(kept|revised|dropped)\s*->\s*(.+?)\s*->\s*(.+?)\s*$", re.M)
VERDICT = re.compile(r"^\s*verdict\s*:\s*(.+?)\s*$", re.M | re.I)
KEEP_BASE = "KEEP_BASE"
NO_ENTRY = "NO_ENTRY"
VERDICTS = ("helped", "hurt", "no observed effect", "confounded")
EXPERIENCE_KEYS = ("cue", "lesson", "evidence", "confidence")
REQUIRED_EXPERIENCE_KEYS = ("cue", "lesson", "evidence")
WHY_MAX_LINES = 6


@dataclass(frozen=True)
class Decision:
    """合成の notes の1行（kept|revised|dropped -> 編集 -> 根拠）。"""

    kind: str
    edit: str
    evidence: str


@dataclass(frozen=True)
class Choice:
    chosen_id: str
    why: str


@dataclass(frozen=True)
class Experience:
    cue: str
    lesson: str
    evidence: str
    confidence: str


@dataclass(frozen=True)
class Reflection:
    """振り返りの返答。edits は編集ごとの表の本文、experience は教訓（無ければ None）。"""

    edits: str
    experience: Experience | None
    declined: bool


def parse_notes(text: str) -> str:
    """最後の `<notes>` の中身。タグが無ければ返答の全文。"""
    found = NOTES.findall(text)
    return str(found[-1]).strip() if found else text.strip()


def is_keep_base(notes: str) -> bool:
    return KEEP_BASE in notes


def parse_decisions(notes: str) -> list[Decision]:
    return [Decision(kind, edit, evidence) for kind, edit, evidence in DECISION.findall(notes)]


def parse_choice(text: str, ids: Sequence[str]) -> tuple[Choice | None, str]:
    """選択役の返答から、選んだ ID と理由を読む。読めなければ (None, 理由)。"""
    found = CHOICE.findall(text)
    if not found:
        return None, "返答に choice の囲みがありません"
    chosen = str(found[-1]).strip()
    if chosen not in ids:
        return None, f"選んだ {chosen!r} は候補の ID（{', '.join(ids)}）にありません"
    why = WHY.findall(text)
    lines = str(why[-1]).strip().splitlines() if why else []
    return Choice(chosen, "\n".join(lines[:WHY_MAX_LINES])), ""


def parse_reflection(text: str) -> Reflection:
    """振り返りの返答。cue・lesson・evidence が揃わない教訓は無いものとして扱う。"""
    edits = EDITS.findall(text)
    body = str(edits[-1]).strip() if edits else ""
    found = EXPERIENCE.findall(text)
    if not found:
        return Reflection(body, None, declined=NO_ENTRY in text)
    fields: dict[str, str] = {}
    for line in str(found[-1]).strip().splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip().lower() in EXPERIENCE_KEYS:
            fields[key.strip().lower()] = value.strip()
    if not all(fields.get(key) for key in REQUIRED_EXPERIENCE_KEYS):
        return Reflection(body, None, declined=False)
    experience = Experience(fields["cue"], fields["lesson"], fields["evidence"], fields.get("confidence", ""))
    return Reflection(body, experience, declined=False)


def list_verdicts(edits: str) -> list[str]:
    """編集の表の verdict の値を、小文字にして表の順に並べる。"""
    return [value.strip().lower() for value in VERDICT.findall(edits)]
