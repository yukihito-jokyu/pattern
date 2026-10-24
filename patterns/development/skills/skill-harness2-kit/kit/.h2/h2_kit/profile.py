"""profile.json の型と検証。harness2 の BenchPrompts（仕事の説明）と BenchSpec（予算と実行の形）に当たる。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from h2_kit import guards, layout

SCHEMA_VERSION = 1
MAX_K = 5
MAX_WIDTH = 8
MIN_OBS_TRUNC = 10000
DEFAULT_OBS_TRUNC = 50000
FILES_DELIVERABLE = "files"
REPLY_DELIVERABLE = "reply"
ANY_DELIVERABLE = "any"
DELIVERABLES = (FILES_DELIVERABLE, REPLY_DELIVERABLE, ANY_DELIVERABLE)
EFFORTS = ("", "low", "medium", "high", "xhigh", "max")
DEFAULT_ROLLOUT_TOOLS = ("Read", "Edit", "Write", "Glob", "Grep", "Bash(python3 *)", "Bash(ls *)")
METHOD_TEXTS = ("work", "inv_levers", "dom_levers", "yardstick", "selection_checks")
REQUIRED_TEXTS = ("work", "domain_word", "deliverable_word")
OPTIONAL_TEXTS = ("inv_levers", "dom_levers", "yardstick", "selection_lead", "selection_checks")


@dataclass(frozen=True)
class RolloutSpec:
    """実行（rollout）の `claude -p` の形。tools には Skill を runner が必ず足す。"""

    model: str
    tools: tuple[str, ...]
    timeout_sec: int
    max_budget_usd: float


@dataclass(frozen=True)
class ImproverSpec:
    """編集・合成・選択・振り返りのセッションの `claude -p` の形。"""

    model: str
    effort: str
    timeout_sec: int
    max_budget_usd: float


@dataclass(frozen=True)
class Profile:
    """1つの対象の改善の設定。文の項目はひな形にそのまま入る。"""

    schema_version: int
    skill: str
    work: str
    domain_word: str
    deliverable_word: str
    inv_levers: str
    dom_levers: str
    yardstick: str
    selection_lead: str
    selection_checks: str
    k: int
    modes: tuple[str, ...]
    seed: int | None
    width: int
    obs_trunc: int
    deliverable: str
    claude: tuple[str, ...]
    rollout: RolloutSpec
    improver: ImproverSpec
    leak_globs: tuple[str, ...]


def parse_profile(data: object) -> tuple[Profile | None, list[str]]:
    """profile.json の中身を検証する。問題を全部集め、1つでもあれば Profile を返さない。"""
    if not isinstance(data, dict):
        return None, ["profile.json の最上位はオブジェクトにしてください"]
    problems: list[str] = []
    texts = {name: _read_text(data.get(name), name, name in REQUIRED_TEXTS, problems) for name in REQUIRED_TEXTS}
    texts.update({name: _read_text(data.get(name), name, False, problems) for name in OPTIONAL_TEXTS})
    for name in METHOD_TEXTS:
        problems += guards.check_measurement_words(name, texts[name])
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        problems.append(f"schema_version が {version!r} です。この補助 CLI は {SCHEMA_VERSION} の形だけを読みます")
    profile = Profile(
        schema_version=SCHEMA_VERSION,
        skill=_read_skill(data.get("skill"), problems),
        work=texts["work"],
        domain_word=texts["domain_word"],
        deliverable_word=texts["deliverable_word"],
        inv_levers=texts["inv_levers"],
        dom_levers=texts["dom_levers"],
        yardstick=texts["yardstick"],
        selection_lead=texts["selection_lead"],
        selection_checks=texts["selection_checks"],
        k=_read_int(data.get("k"), "k", (1, MAX_K), problems),
        modes=_read_modes(data.get("modes"), problems),
        seed=_read_seed(data.get("seed"), problems),
        width=_read_int(data.get("width"), "width", (1, MAX_WIDTH), problems),
        obs_trunc=_read_int(data.get("obs_trunc"), "obs_trunc", (MIN_OBS_TRUNC, 10**7), problems),
        deliverable=_read_choice(data.get("deliverable"), "deliverable", DELIVERABLES, problems),
        claude=_read_strings(data.get("claude"), "claude", True, problems),
        rollout=_parse_rollout(data.get("rollout"), problems),
        improver=_parse_improver(data.get("improver"), problems),
        leak_globs=_read_strings(data.get("leak_globs"), "leak_globs", False, problems),
    )
    return (None, problems) if problems else (profile, [])


def parse_skill_path(value: object) -> tuple[str, list[str]]:
    """対象スキルのディレクトリ（リポジトリからの相対パス）を確かめる。"""
    problems: list[str] = []
    return _read_skill(value, problems), problems


def build_default_profile(skill: str) -> dict[str, object]:
    """init が書く profile.json のひな形。文の項目は人と決めるので空にする。"""
    return {
        "schema_version": SCHEMA_VERSION,
        "skill": skill,
        "work": "",
        "domain_word": "",
        "deliverable_word": "",
        "inv_levers": "",
        "dom_levers": "",
        "yardstick": "",
        "selection_lead": "",
        "selection_checks": "",
        "k": 2,
        "modes": [layout.PARALLEL],
        "seed": None,
        "width": 2,
        "obs_trunc": DEFAULT_OBS_TRUNC,
        "deliverable": ANY_DELIVERABLE,
        "claude": ["claude"],
        "rollout": {"model": "", "tools": list(DEFAULT_ROLLOUT_TOOLS), "timeout_sec": 900, "max_budget_usd": 1.0},
        "improver": {"model": "", "effort": "", "timeout_sec": 1200, "max_budget_usd": 2.0},
        "leak_globs": [],
    }


def _parse_rollout(data: object, problems: list[str]) -> RolloutSpec:
    if not isinstance(data, dict):
        problems.append("rollout はオブジェクトにしてください")
        data = {}
    return RolloutSpec(
        model=_read_text(data.get("model"), "rollout.model", False, problems),
        tools=_read_strings(data.get("tools"), "rollout.tools", True, problems),
        timeout_sec=_read_int(data.get("timeout_sec"), "rollout.timeout_sec", (30, 7200), problems),
        max_budget_usd=_read_usd(data.get("max_budget_usd"), "rollout.max_budget_usd", problems),
    )


def _parse_improver(data: object, problems: list[str]) -> ImproverSpec:
    if not isinstance(data, dict):
        problems.append("improver はオブジェクトにしてください")
        data = {}
    return ImproverSpec(
        model=_read_text(data.get("model"), "improver.model", False, problems),
        effort=_read_choice(data.get("effort"), "improver.effort", EFFORTS, problems),
        timeout_sec=_read_int(data.get("timeout_sec"), "improver.timeout_sec", (30, 7200), problems),
        max_budget_usd=_read_usd(data.get("max_budget_usd"), "improver.max_budget_usd", problems),
    )


def _read_text(value: object, name: str, required: bool, problems: list[str]) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        problems.append(f"{name} は{'空でない' if required else ''}文字列にしてください")
        return ""
    return value.strip()


def _read_int(value: object, name: str, bounds: tuple[int, int], problems: list[str]) -> int:
    low, high = bounds
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        problems.append(f"{name} は {low} 以上 {high} 以下の整数にしてください（今は {value!r}）")
        return low
    return value


def _read_usd(value: object, name: str, problems: list[str]) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        problems.append(f"{name} は正の数（米ドル）にしてください（今は {value!r}）")
        return 0.0
    return float(value)


def _read_choice(value: object, name: str, choices: Sequence[str], problems: list[str]) -> str:
    if value is None and "" in choices:
        return ""
    if not isinstance(value, str) or value not in choices:
        shown = "、".join(choice for choice in choices if choice)
        problems.append(f"{name} は {shown} のどれかにしてください（今は {value!r}）")
        return choices[0]
    return value


def _read_strings(value: object, name: str, required: bool, problems: list[str]) -> tuple[str, ...]:
    if value is None and not required:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        problems.append(f"{name} は空でない文字列の配列にしてください")
        return ()
    if required and not value:
        problems.append(f"{name} には1つ以上の値を書いてください")
    return tuple(str(item) for item in value)


def _read_modes(value: object, problems: list[str]) -> tuple[str, ...]:
    modes = _read_strings(value, "modes", True, problems)
    if any(mode not in layout.MODES for mode in modes) or len(set(modes)) != len(modes):
        problems.append(f"modes は {'、'.join(layout.MODES)} から重ならずに選んでください（今は {list(modes)!r}）")
        return ()
    return tuple(mode for mode in layout.MODES if mode in modes)


def _read_seed(value: object, problems: list[str]) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        problems.append(f"seed は整数か null にしてください（今は {value!r}）")
        return None
    return value


def _read_skill(value: object, problems: list[str]) -> str:
    """対象スキルのディレクトリ（リポジトリからの相対パス）。外へ出るパスと絶対パスは拒む。"""
    if not isinstance(value, str) or not value.strip():
        problems.append("skill は対象スキルのディレクトリ（リポジトリからの相対パス）にしてください")
        return ""
    parts = value.strip().strip("/").split("/")
    if value.startswith("/") or ".." in parts:
        problems.append(f"skill はリポジトリの中の相対パスにしてください（今は {value!r}）")
        return ""
    return "/".join(parts)
