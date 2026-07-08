"""Inspect AI port of the HAX/PAIR interaction-layer reviewer (a bridge, not a reimplementation).

The dataset is the held-out corpus under `data/external/`. The **solver** runs the project's OWN
pipeline (`approaches.REGISTRY[...]` + `dedup`) and never calls an Inspect model. The **scorer** runs
the project's OWN judge (`judge.adjudicate`) and metrics (`metrics.compute_run_metrics`), exposing
recall / precision / genericity / grounding / primary as Inspect metrics. So Inspect provides the
orchestration, the `.eval` log (`inspect view`) and the aggregation; the method (generation, dedup,
the judge, F2 with the genericity gate) stays exactly as validated.

Run with `--model none` (the solver does not use an Inspect model). The generator/judge are the
project's own models, selected via `GEN_MODEL` / `JUDGE_MODEL`; pass `-T gen_model=... -T judge_model=...`
to pin them (recorded in the log as task args and in each score's metadata). See
docs/adr/ADR-010-inspect-bridge.md and evals/inspect/README.md.

NOTE: the aggregate Inspect reports (mean +/- stderr across cases) is a window onto the harness, NOT a
re-measurement of the pre-registered product number (docs/RESULTS*.md), which stays frozen.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import Score, Scorer, Target, metric, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver

from interaction_review import judge as judge_mod
from interaction_review import llm
from interaction_review.approaches import REGISTRY
from interaction_review.dedup import deduplicate
from interaction_review.guidelines import all_guidelines
from interaction_review.metrics import compute_run_metrics, recall_by_revealed_by
from interaction_review.report import render_findings_md
from interaction_review.schemas import Dossier, Finding, GoldenIssue

_EXTERNAL = Path(__file__).resolve().parents[2] / "data" / "external"
_METRIC_KEYS = ("recall", "precision", "genericity_rate", "grounding_rate", "primary_score")


def load_external_cases() -> MemoryDataset:
    """The held-out corpus (data/external/<case>/{dossier,answer_key}.json) as an Inspect dataset."""
    samples: list[Sample] = []
    for d in sorted(p for p in _EXTERNAL.iterdir() if p.is_dir()):
        dj, aj = d / "dossier.json", d / "answer_key.json"
        if not (dj.is_file() and aj.is_file()):
            continue
        dossier = json.loads(dj.read_text(encoding="utf-8"))
        golden = json.loads(aj.read_text(encoding="utf-8"))
        samples.append(
            Sample(
                input=f"{dossier.get('system_name', '?')} - {dossier.get('domain', '?')}",
                id=d.name,
                metadata={"case": d.name, "dossier": dossier, "golden": golden},
            )
        )
    return MemoryDataset(samples)


# --------------------------------------------------------------------------- #
# nan-aware aggregation. The control case `sistema-bueno` has no golden, so recall / primary are
# undefined there (emitted as NaN by the scorer); a naive mean would fold that in as 0 and depress
# the aggregate. Under a dict-keyed `metrics=` mapping Inspect passes each metric a list of Score
# objects whose `.value` is already the scalar for that key (verified against inspect-ai 0.3.244).
# --------------------------------------------------------------------------- #
def _floats(scores: list) -> list[float]:
    out: list[float] = []
    for s in scores:
        v = getattr(s, "value", None)
        if v is None and hasattr(s, "score"):
            v = s.score.value
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if not math.isnan(f):
            out.append(f)
    return out


@metric
def nan_mean():
    def m(scores: list) -> float:
        import numpy as np

        vals = _floats(scores)
        return float(np.mean(vals)) if vals else float("nan")

    return m


@metric
def nan_stderr():
    def m(scores: list) -> float:
        import numpy as np

        vals = _floats(scores)
        if len(vals) < 2:
            return float("nan")
        return float(np.std(vals, ddof=1) / math.sqrt(len(vals)))

    return m


def _metric_map() -> dict:
    return {k: [nan_mean(), nan_stderr()] for k in _METRIC_KEYS}


# --------------------------------------------------------------------------- #
# Solver: the project's pipeline. Never calls Inspect's `generate`.
# --------------------------------------------------------------------------- #
@solver
def review_solver(approach: str = "p3", dedup: bool = True) -> Solver:
    guidelines = list(all_guidelines())

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        dossier = Dossier.model_validate(state.metadata["dossier"])
        run = REGISTRY.get(approach)
        if run is None:
            raise ValueError(f"Unknown approach {approach!r}. Available: {sorted(REGISTRY)}.")
        findings = run(dossier, guidelines)
        if dedup:
            findings = deduplicate(findings)
        state.store.set("findings", [f.model_dump(mode="json") for f in findings])
        # The transcript is the real report, so `inspect view` is actually useful.
        state.output.completion = render_findings_md(dossier, findings, approach)
        return state

    return solve


# --------------------------------------------------------------------------- #
# Scorer: the project's judge + metrics. Not `model_graded_qa`.
# --------------------------------------------------------------------------- #
@scorer(metrics=_metric_map())
def review_scorer(approach: str = "p3") -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        dossier = Dossier.model_validate(state.metadata["dossier"])
        golden = [GoldenIssue.model_validate(g) for g in state.metadata["golden"]]
        findings = [Finding.model_validate(f) for f in state.store.get("findings", [])]

        adjudications = judge_mod.adjudicate(findings, golden, dossier)
        m = compute_run_metrics(approach, findings, adjudications, golden)

        no_golden = m.n_golden == 0
        no_findings = m.n_findings == 0
        nan = float("nan")
        value = {
            "recall": nan if no_golden else m.recall,
            "precision": nan if no_findings else m.precision,
            "genericity_rate": nan if no_findings else m.genericity_rate,
            "grounding_rate": nan if no_findings else m.grounding_rate,
            "primary_score": nan if no_golden else m.primary_score,
        }
        subset = recall_by_revealed_by(adjudications, golden)
        return Score(
            value=value,
            answer=f"{m.n_findings} findings; recall {m.recall:.2f}; precision {m.precision:.2f}",
            explanation=render_findings_md(dossier, findings, approach),
            metadata={
                "run_metrics": m.model_dump(),
                "adjudications": [a.model_dump() for a in adjudications],
                "recall_by_revealed_by": [s.model_dump() for s in subset],
                # The models that actually generated/judged, resolved (not "none"). Anti-mislabel.
                "gen_model": llm.gen_model(),
                "judge_model": llm.judge_model(),
            },
        )

    return score


@task
def hax_pair_review(
    approach: str = "p3",
    dedup: bool = True,
    gen_model: str | None = None,
    judge_model: str | None = None,
) -> Task:
    """The eval task. Corpus x (project pipeline) x (project judge + metrics).

    `epochs` (Inspect's -T/--epochs) plays the role of the project's `k`. `gen_model`/`judge_model`
    pin the project's own models (recorded in the log). Always run with `--model none`.
    """
    if gen_model:
        os.environ["GEN_MODEL"] = gen_model
    if judge_model:
        os.environ["JUDGE_MODEL"] = judge_model
    return Task(
        dataset=load_external_cases(),
        solver=review_solver(approach=approach, dedup=dedup),
        scorer=review_scorer(approach=approach),
    )
