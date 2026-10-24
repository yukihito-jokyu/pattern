"""振り返り。選ばれた木の編集ごとの効果と、次のタスクへ移す教訓を多くても1つ書かせる。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from h2_kit import context, contracts, fsops, layout, profile, prompts, rollout, runner, skilltree
from h2_kit.errors import CommandError, InvalidFileError


@dataclass(frozen=True)
class Request:
    """振り返りの依頼。candidates は基準でない全部の段（候補と完成品）の木と実行。"""

    model: profile.Profile
    prompt: str
    source_dir: Path
    place: Path
    templates: Path
    views: tuple[rollout.RolloutView, ...]
    chosen: context.PoolEntry
    base_tree: skilltree.SkillTree
    candidates: tuple[context.PoolEntry, ...]
    decisions: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Reflected:
    """振り返りの結果。experience が None なら教訓は無い（NO_ENTRY か、読めない返答か、失敗）。"""

    edits: str
    experience: contracts.Experience | None
    declined: bool
    error: str
    cost_usd: float


def run_reflection(request: Request, chosen_id: str, why: str, id_map: tuple[tuple[str, str], ...]) -> Reflected:
    """選ばれた木を context/harness/、元の木を context/base_harness/ に置き、全候補と全実行を読ませる。"""
    adoption = {
        "chosen_label": request.chosen.label,
        "chosen_id": chosen_id,
        "candidate_ids": dict(id_map),
        "reason": why,
    }
    evidence = context.Evidence(
        prompt=request.prompt,
        source=request.source_dir,
        rollouts=request.views,
        harness=request.chosen.tree,
        base_harness=request.base_tree,
        pool=request.candidates,
        decisions=request.decisions,
        adoption=adoption,
    )
    built = context.write_context(request.place / layout.CONTEXT_DIR, evidence, request.model.leak_globs)
    values = {
        "work": request.model.work,
        "chosen": request.chosen.label,
        "why": why or "（理由はありません）",
        "layout": built.layout,
    }
    try:
        reply = runner.run_session(
            request.model, request.place, prompts.render_prompt(request.templates, "reflect", values), runner.READ_TOOLS
        )
    except (CommandError, InvalidFileError) as exc:
        return Reflected("", None, False, str(exc), 0.0)
    if not reply.ok:
        return Reflected("", None, False, reply.error, reply.cost_usd)
    found = contracts.parse_reflection(reply.text)
    if found.edits:
        fsops.write_text(request.place / layout.EDITS_FILE, found.edits + "\n")
    return Reflected(found.edits, found.experience, found.declined, "", reply.cost_usd)
