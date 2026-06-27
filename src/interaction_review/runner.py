"""Orquestacion del experimento: corre approaches k veces, adjudica y agrega.

Guarda los crudos (hallazgos + adjudicaciones) para poder re-adjudicar o re-medir
sin volver a generar (reproducibilidad, ADR-002). `runs/` esta gitignored.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from interaction_review import llm
from interaction_review.approaches import REGISTRY
from interaction_review.judge import adjudicate as default_judge
from interaction_review.metrics import AggregateMetrics, RunMetrics, aggregate, compute_run_metrics
from interaction_review.schemas import Adjudication, Dossier, Finding, GoldenIssue, Guideline

# Approaches sin aleatoriedad: basta generar/juzgar una vez y replicar.
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
    """Devuelve {'aggregates': {name: AggregateMetrics}, 'runs': {...}, 'config': {...}}.

    Dos fases para no recargar modelos en cada iteracion: primero TODA la generacion
    (mantiene cargado el modelo generador), luego TODA la adjudicacion (mantiene
    cargado el modelo juez). En local, eso reduce los swaps de modelo de ~13 a 1.
    """
    for name in approaches:
        if name not in REGISTRY:
            raise ValueError(f"Approach desconocido: {name}. Disponibles: {sorted(REGISTRY)}")

    # --- Fase 1: generacion (modelo generador) ---
    gen_results: dict[str, list[list[Finding]]] = {}
    for name in approaches:
        n_iter = 1 if name in DETERMINISTIC else k
        gen_results[name] = [REGISTRY[name](dossier, guidelines) for _ in range(n_iter)]

    # --- Fase 2: adjudicacion + metricas (modelo juez) ---
    aggregates: dict[str, AggregateMetrics] = {}
    runs_detail: dict[str, list[dict]] = {}
    for name in approaches:
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
        # Replicar el resultado determinista hasta k (varianza 0).
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

    # Devolvemos los objetos AggregateMetrics tambien, para el render.
    result["_aggregate_objs"] = aggregates
    return result
