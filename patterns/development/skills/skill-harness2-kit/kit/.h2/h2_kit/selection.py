"""完成品の盲検の選択。成果物を出した完成品だけを、匿名の ID で比べて1つを選ぶ（STATE-05）。"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from h2_kit import context, contracts, layout, profile, prompts, rollout, runner
from h2_kit.errors import CommandError, InvalidFileError

# 候補のファイル名。ラベル（どの木から来たか）を名前に入れない
CANDIDATE_NAME = "{anon}"
SEED_DIGITS = 12
WHY_LIMIT = 2000
TRIVIAL_WHY = "k = 1 なので、選択役を起動せずに1つの完成品を選んだ（harness2 の trivial_selection）"


@dataclass(frozen=True)
class Pool:
    """選択の材料。views は成果物を出した完成品、dropped は出さなかった完成品のラベル。"""

    views: tuple[rollout.RolloutView, ...]
    dropped: tuple[str, ...]


@dataclass(frozen=True)
class Selected:
    """選択の結果。chosen_label が空なら、成果物を出した完成品が無かった。"""

    chosen_label: str
    chosen_id: str
    why: str
    id_map: tuple[tuple[str, str], ...]
    fallback: bool
    error: str
    cost_usd: float
    dropped: tuple[str, ...]


@dataclass(frozen=True)
class Request:
    """選択の依頼。place は selection/ のディレクトリ。"""

    model: profile.Profile
    prompt: str
    source_dir: Path
    place: Path
    templates: Path
    task_id: str
    mode: str


def build_pool(finals: Sequence[rollout.RolloutView]) -> Pool:
    """完成品のうち、終わって成果物を出したものだけを候補にする（基準の実行は入れない）。"""
    kept = tuple(view for view in finals if view.record.ok and view.record.delivered)
    dropped = tuple(view.label for view in finals if view not in kept)
    return Pool(kept, dropped)


def compute_anonymous_ids(labels: Sequence[str], task_id: str, k: int, mode: str) -> dict[str, str]:
    """匿名の ID → ラベル。並べ替えたラベルを、タスク・k・モードの種でシャッフルする（やり直しても同じ）。"""
    seed = int(hashlib.sha1(f"{task_id}|{k}|{mode}".encode()).hexdigest()[:SEED_DIGITS], 16)
    ordered = sorted(labels)
    random.Random(seed).shuffle(ordered)
    return {build_anonymous_id(index): label for index, label in enumerate(ordered)}


def build_anonymous_id(index: int) -> str:
    """A..Z、AA..AZ、BA...。"""
    found = ""
    number = index + 1
    while number:
        number, rest = divmod(number - 1, 26)
        found = chr(ord("A") + rest) + found
    return found


def run_selection(request: Request, pool: Pool) -> Selected:
    """選択役に選ばせる。k が 1 なら起動しない。選択役が失敗したら、並べた最初の完成品に戻す。"""
    labels = [view.label for view in pool.views]
    if not labels:
        return Selected("", "", "", (), False, "成果物を出した完成品がありません", 0.0, pool.dropped)
    id_map = compute_anonymous_ids(labels, request.task_id, request.model.k, request.mode)
    pairs = tuple(sorted(id_map.items()))
    if request.model.k == 1:
        return Selected(labels[0], next(iter(id_map)), TRIVIAL_WHY, pairs, False, "", 0.0, pool.dropped)
    views = {view.label: view for view in pool.views}
    candidates = tuple(
        (CANDIDATE_NAME.format(anon=anon, label=label), rollout.read_deliverable(views[label])) for anon, label in pairs
    )
    evidence = context.Evidence(prompt=request.prompt, source=request.source_dir, candidates=candidates)
    context.write_context(request.place / layout.CONTEXT_DIR, evidence, request.model.leak_globs)
    try:
        reply = runner.run_session(request.model, request.place, _render_select(request, id_map), runner.READ_TOOLS)
    except (CommandError, InvalidFileError) as exc:
        return _build_fallback(id_map, str(exc), 0.0, pool.dropped)
    choice, problem = contracts.parse_choice(reply.text, sorted(id_map)) if reply.ok else (None, reply.error)
    if choice is None:
        return _build_fallback(id_map, problem, reply.cost_usd, pool.dropped)
    label = id_map[choice.chosen_id]
    return Selected(label, choice.chosen_id, choice.why[:WHY_LIMIT], pairs, False, "", reply.cost_usd, pool.dropped)


def _render_select(request: Request, id_map: Mapping[str, str]) -> str:
    model = request.model
    values = {
        "n": str(len(id_map)),
        "work": model.work,
        "deliverable_word": model.deliverable_word,
        "selection_lead": prompts.render_part(
            request.templates, "_selection-lead", {"text": model.selection_lead}, bool(model.selection_lead)
        ),
        "selection_checks": prompts.render_part(
            request.templates, "_selection-checks", {"text": model.selection_checks}, bool(model.selection_checks)
        ),
        "ids": "、".join(sorted(id_map)),
    }
    return prompts.render_prompt(request.templates, "select", values)


def _build_fallback(id_map: Mapping[str, str], error: str, cost: float, dropped: tuple[str, ...]) -> Selected:
    """中立の代わり。完成品だけの候補なので、ラベルを並べた最初のものを選ぶ（harness2 の _fallback）。"""
    label = sorted(id_map.values())[0]
    anon = next(anon for anon, found in id_map.items() if found == label)
    return Selected(label, anon, "", tuple(sorted(id_map.items())), True, error[:WHY_LIMIT], cost, dropped)
