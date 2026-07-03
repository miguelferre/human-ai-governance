"""SEMANTIC layer of the deduplication (with LLM): the residual that the lexical step does not join.

The deterministic dedup (dedup.py) collapses textually obvious duplicates, but leaves
the residual "same problem, very different wording/guideline" (calibration: real
matches with median Jaccard 0.127 -> text is not enough). That judgment is IRREDUCIBLE:
here an LLM does it, consistent with the project's thesis (the mechanical part to the code, to the
model only the irreducible part, ADR-004).

Flow: lexical dedup (cheap, no LLM) -> ONE call to the model to group the residual
by underlying problem -> merge of each group (reuses dedup._merge: unites guidelines,
maximum severity, cumulative merged_count). The model ONLY groups by id; the merge and the
guarantee of not losing any finding are deterministic, in code.

Guarantee: each input finding appears in EXACTLY one output finding (it is neither
lost nor duplicated), even if the model hallucinates ids or repeats one in two groups.
"""

from __future__ import annotations

from interaction_review import llm, prompts
from interaction_review.dedup import _merge, _representative, deduplicate, text_similarity
from interaction_review.schemas import Finding

# Anti-over-merge guardrail (the LLM PROPOSES, the code CHECKS): within a group
# that the model deemed "same problem", the member whose locus+title is very
# dissimilar from the representative is VETOED (probably another problem in the same area). Calibrated offline:
# the strict prompt alone did not lower the impurity; this gate did. Low floor -> only cuts
# the egregious pairings, keeps the genuine rewrites (same locus, different citation).
SEMANTIC_LOCUS_FLOOR: float = 0.18


def _llm_groups(findings: list[Finding], model: str | None, temperature: float) -> list[list[str]]:
    """Asks the model for the groups of ids that are the same problem. Returns lists of ids."""
    payload = [
        {"id": f.id, "title": f.title, "locus": f.locus, "guideline_ids": f.guideline_ids}
        for f in findings
    ]
    out = llm.call_structured(
        model=model or llm.judge_model(),
        system=prompts.SEMANTIC_DEDUP_SYSTEM,
        user=prompts.semantic_dedup_user(payload),
        tool=prompts.SEMANTIC_DEDUP_TOOL,
        temperature=temperature,
    )
    groups: list[list[str]] = []
    if isinstance(out, dict):
        for g in out.get("groups", []):
            if isinstance(g, dict):
                ids = [i for i in g.get("finding_ids", []) if isinstance(i, str)]
                if len(ids) >= 2:
                    groups.append(ids)
    return groups


def _refine_group(members: list[Finding], floor: float) -> list[list[Finding]]:
    """Guardrail: within an LLM group, separates whoever has a very dissimilar locus.

    Returns subgroups: the core (similar to the representative by title+locus) and each
    outlier on its own. This way a group that mixed two neighboring problems is split and stops
    conflating. It does not lose findings (the outliers remain as singletons).
    """
    if len(members) < 2:
        return [members]
    rep = _representative(members)
    sig = f"{rep.title} {rep.locus}"
    core, outliers = [], []
    for m in members:
        if m.id == rep.id or text_similarity(f"{m.title} {m.locus}", sig) >= floor:
            core.append(m)
        else:
            outliers.append([m])
    return [core] + outliers


def deduplicate_llm(
    findings: list[Finding],
    *,
    pre_dedup: bool = True,
    model: str | None = None,
    temperature: float = 0.0,
    locus_floor: float = SEMANTIC_LOCUS_FLOOR,
) -> list[Finding]:
    """Deduplicates with a semantic layer (LLM) on top of the lexical dedup.

    `pre_dedup`: applies the deterministic dedup first (recommended: fewer items to send
    to the model and it focuses on the hard residual). `locus_floor`: anti-over-merge guardrail
    (the LLM proposes the groups, the code vetoes members with a dissimilar locus; 0 = no guardrail).
    """
    base = deduplicate(findings) if pre_dedup else list(findings)
    if len(base) < 2:
        return base

    by_id = {f.id: f for f in base}
    groups = _llm_groups(base, model, temperature)

    # Builds clusters respecting: each id in ONLY one cluster; order by 1st appearance.
    order = {f.id: n for n, f in enumerate(base)}
    assigned: set[str] = set()
    clusters: list[list[Finding]] = []
    for ids in groups:
        members = [by_id[i] for i in dict.fromkeys(ids) if i in by_id and i not in assigned]
        if len(members) >= 2:
            assigned.update(m.id for m in members)
            clusters.append(members)
    # The ungrouped ones remain on their own.
    for f in base:
        if f.id not in assigned:
            clusters.append([f])
    # Guardrail in code: splits the groups that mix dissimilar loci.
    refined: list[list[Finding]] = []
    for c in clusters:
        refined.extend(_refine_group(c, locus_floor) if locus_floor > 0 else [c])
    # Stable order: by the index of the earliest member of each cluster.
    refined.sort(key=lambda c: min(order[m.id] for m in c))
    return [_merge(c) for c in refined]
