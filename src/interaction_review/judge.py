"""LLM-judge: adjudicates the findings against the golden set (ADR-002).

Uses a model and a prompt DIFFERENT from the generator to avoid self-evaluation. Its
output is a pre-labeling that the human then reviews (`human_confirmed`).
"""

from __future__ import annotations

from functools import lru_cache

from interaction_review import llm, prompts
from interaction_review.dedup import text_similarity
from interaction_review.guidelines import all_guidelines
from interaction_review.schemas import (
    Adjudication,
    AdjudicationLabel,
    Dossier,
    Finding,
    GoldenIssue,
)


@lru_cache(maxsize=1)
def _group_by_guideline() -> dict[str, str]:
    """guideline id -> 'corpus:group' (HAX phase / PAIR chapter)."""
    return {g.id: f"{g.corpus.value}:{g.group}" for g in all_guidelines()}


def _shares_area(fg: set[str], f_groups: set[str], g: GoldenIssue, gmap: dict[str, str]) -> bool:
    """The finding and the golden share the EXACT guideline or the same group/area."""
    if fg & set(g.guideline_ids):
        return True
    return bool(f_groups & {gmap[i] for i in g.guideline_ids if i in gmap})


def _candidates(f: Finding, golden: list[GoldenIssue]) -> list[GoldenIssue]:
    """ALL the golden as candidates, the LIKELY ones first.

    Measurement debt (TESTPLAN B2): the original filter only offered golden that
    shared the EXACT guideline with the finding. A finding that cited the 'wrong'
    guideline (another phase, or another corpus) was left without the correct golden among its
    candidates -> FALSE MISS (real P3 ~14/15 measured as ~12). The 'short list' was a
    crutch for the local 14B judge (ADR-004); the cloud judge is strong and can scan all
    15. ALL are offered, with those that share guideline/group first (a hint) and the rest
    ordered by text similarity, so as not to deny a match due to a citation discrepancy.
    """
    gmap = _group_by_guideline()
    fg = set(f.guideline_ids)
    f_groups = {gmap[i] for i in fg if i in gmap}
    primary, rest = [], []
    for g in golden:
        (primary if _shares_area(fg, f_groups, g, gmap) else rest).append(g)
    ftext = f"{f.title} {f.locus} {f.evidence}"
    rest.sort(key=lambda g: text_similarity(ftext, f"{g.description} {g.locus}"), reverse=True)
    return primary + rest


def _payload(grounded: list[Finding], golden: list[GoldenIssue]) -> list[dict]:
    gmap = _group_by_guideline()
    out = []
    for f in grounded:
        fg = set(f.guideline_ids)
        f_groups = {gmap[i] for i in fg if i in gmap}
        cands = _candidates(f, golden)
        out.append(
            {
                "id": f.id,
                "title": f.title,
                "locus": f.locus,
                "evidence": f.evidence,
                "candidates": [
                    {
                        "id": g.id,
                        "description": g.description,
                        "shares_guideline": _shares_area(fg, f_groups, g, gmap),
                    }
                    for g in cands
                ],
            }
        )
    return out


def adjudicate(
    findings: list[Finding], golden: list[GoldenIssue], dossier: Dossier
) -> list[Adjudication]:
    """Returns one adjudication per finding (in the same order as `findings`)."""
    if not findings:
        return []
    grounded = [f for f in findings if f.is_grounded()]
    # Candidates per finding (to validate that the judge picks one from ITS list).
    cand_ids_by_finding = {f.id: {g.id for g in _candidates(f, golden)} for f in grounded}

    # Judge in small BATCHES: a single call with 20+ findings saturates the time
    # limit of the 14B (happened in P3). Batches of BATCH keep each call short and reliable.
    raw: dict = {}
    BATCH = 6
    for i in range(0, len(grounded), BATCH):
        chunk = grounded[i : i + BATCH]
        out = llm.call_structured(
            model=llm.judge_model(),
            system=prompts.JUDGE_SYSTEM,
            user=prompts.judge_user(_payload(chunk, golden), dossier),
            tool=prompts.JUDGE_TOOL,
            temperature=0.0,  # deterministic judge
        )
        if isinstance(out, dict):
            for a in out.get("adjudications", []):
                if isinstance(a, dict) and a.get("finding_id"):
                    raw[a["finding_id"]] = a

    adjudications: list[Adjudication] = []
    for f in findings:
        # STRUCTURAL GENERICITY (hard gate, in code): without anchoring => fp_generic ALWAYS,
        # before looking at the judge. Without this, B0 (empty checklist) contaminates the floor.
        if not f.is_grounded():
            adjudications.append(
                Adjudication(
                    finding_id=f.id,
                    label=AdjudicationLabel.FP_GENERIC,
                    judge_rationale="(not anchored: no locus/evidence)",
                )
            )
            continue
        a = raw.get(f.id)
        if a is None:
            adjudications.append(
                Adjudication(
                    finding_id=f.id,
                    label=AdjudicationLabel.FP_INCORRECT,
                    judge_rationale="(no judge classification)",
                )
            )
            continue
        # The LABEL is DERIVED: valid candidate -> tp_match; if "none" -> tp_new/fp_incorrect.
        cc = str(a.get("corresponde_a_candidato", "")).strip()
        matched = cc if cc in cand_ids_by_finding.get(f.id, set()) else None
        if matched is not None:
            label = AdjudicationLabel.TP_MATCH
        elif bool(a.get("es_real")):
            label = AdjudicationLabel.TP_NEW
        else:
            label = AdjudicationLabel.FP_INCORRECT
        adjudications.append(
            Adjudication(
                finding_id=f.id,
                label=label,
                matched_golden_id=matched,
                judge_rationale=str(a.get("judge_rationale", "")),
            )
        )
    return adjudications
