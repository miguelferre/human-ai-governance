"""Experiment orchestration: runs approaches k times, adjudicates and aggregates.

Saves the raw data (findings + adjudications) so they can be re-adjudicated or
re-measured without generating again (reproducibility, ADR-002). `runs/` is gitignored.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)

from interaction_review import llm
from interaction_review.approaches import REGISTRY
from interaction_review.judge import adjudicate as default_judge
from interaction_review.metrics import AggregateMetrics, RunMetrics, aggregate, compute_run_metrics
from interaction_review.schemas import Adjudication, Dossier, Finding, GoldenIssue, Guideline

# Approaches without randomness: it is enough to generate/judge once and replicate.
DETERMINISTIC = {"b0"}

JudgeFn = Callable[[list[Finding], list[GoldenIssue], Dossier], list[Adjudication]]


def run_experiment(
    *,
    dossier: Dossier,
    golden: list[GoldenIssue],
    guidelines: list[Guideline],
    approaches: list[str],
    k: int,
    judge: JudgeFn = default_judge,
    save_path: str | None = None,
) -> dict:
    """Returns {'aggregates': {name: AggregateMetrics}, 'runs': {...}, 'config': {...}}.

    Two phases to avoid reloading models on each iteration: first ALL the generation
    (keeps the generator model loaded), then ALL the adjudication (keeps the judge
    model loaded). Locally, that reduces model swaps from ~13 to 1.
    """
    for name in approaches:
        if name not in REGISTRY:
            raise ValueError(f"Unknown approach: {name}. Available: {sorted(REGISTRY)}")

    # --- Phase 1: generation (generator model) ---
    _log(f"[compare] phase 1/2 generation | approaches={approaches} k={k} model={llm.gen_model()}")

    def _write_gen_checkpoint(results: dict[str, list[list[Finding]]]) -> str | None:
        """Rewrite the .gen checkpoint with whatever has been generated so far.

        Written INCREMENTALLY (after each run) so a crash mid-phase-1 does not lose the runs
        already generated: re-judge from it with scripts/rejudge.py without re-generating.
        with_suffix (not str.replace) so a save_path without a .json suffix does not collapse
        onto itself and overwrite the checkpoint it is meant to protect.
        """
        if not save_path:
            return None
        gen_path = str(Path(save_path).with_suffix(".gen.json"))
        checkpoint = {
            "config": {"approaches": approaches, "k": k, "gen_model": llm.gen_model(),
                       "judge_model": llm.judge_model(), "system_name": dossier.system_name},
            "runs": {
                name: [{"findings": [f.model_dump() for f in fs], "adjudications": [], "metrics": {}}
                       for fs in runs]
                for name, runs in results.items()
            },
        }
        Path(gen_path).parent.mkdir(parents=True, exist_ok=True)
        Path(gen_path).write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")
        return gen_path

    gen_results: dict[str, list[list[Finding]]] = {name: [] for name in approaches}
    for name in approaches:
        n_iter = 1 if name in DETERMINISTIC else k
        _log(f"[compare]   generating {name}: {n_iter} run(s)...")
        for _ in range(n_iter):
            gen_results[name].append(REGISTRY[name](dossier, guidelines))
            _write_gen_checkpoint(gen_results)  # incremental: survive a mid-phase-1 crash
    if (gen_path := _write_gen_checkpoint(gen_results)):
        _log(f"[compare] generation checkpoint saved: {gen_path}")

    # --- Phase 2: adjudication + metrics (judge model) ---
    _log(f"[compare] phase 2/2 adjudication | judge={llm.judge_model()}")
    aggregates: dict[str, AggregateMetrics] = {}
    runs_detail: dict[str, list[dict]] = {}
    for name in approaches:
        _log(f"[compare]   judging {name} ({len(gen_results[name])} run(s))...")
        run_metrics: list[RunMetrics] = []
        detail: list[dict] = []
        for findings in gen_results[name]:
            adjs = judge(findings, golden, dossier)
            rm = compute_run_metrics(name, findings, adjs, golden)
            run_metrics.append(rm)
            detail.append(
                {
                    "findings": [f.model_dump() for f in findings],
                    "adjudications": [a.model_dump() for a in adjs],
                    "metrics": rm.model_dump(),
                }
            )
        # Replicate the deterministic result up to k (variance 0).
        if name in DETERMINISTIC and k > 1:
            run_metrics = run_metrics * k
            detail = detail * k

        aggregates[name] = aggregate(run_metrics)
        runs_detail[name] = detail

    result = {
        "config": {
            "approaches": approaches,
            "k": k,
            "gen_model": llm.gen_model(),
            "judge_model": llm.judge_model(),
            "n_golden": len(golden),
            "system_name": dossier.system_name,
        },
        "aggregates": {n: a.model_dump() for n, a in aggregates.items()},
        "runs": runs_detail,
    }

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # We also return the AggregateMetrics objects, for the render.
    result["_aggregate_objs"] = aggregates
    return result
