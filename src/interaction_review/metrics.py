"""Metricas de evaluacion contra el golden set.

Implementa la definicion de exito del plan (seccion 1):
recall, precision, genericity_rate, grounding_rate, tp_new, y la metrica
primaria F-beta sujeta a un techo de genericidad.

Constantes PRE-REGISTRADAS (ver docs/adr/ADR-002): se fijan aqui, en codigo,
ANTES de ver resultados, para no racionalizarlas a posteriori.
"""

from __future__ import annotations

import statistics

from pydantic import BaseModel

from interaction_review.schemas import (
    Adjudication,
    AdjudicationLabel,
    Finding,
    GoldenIssue,
    RevealedBy,
)

# --- Parametros pre-registrados (ADR-002) ---
# beta > 1 prioriza recall: en auditoria, no detectar un problema real es peor
# que un falso positivo barato de descartar.
BETA: float = 2.0
# Un approach con genericity_rate por encima de este techo NO se considera valido
# aunque tenga buen F-beta: escupir genericos es, por definicion, un fallo.
GENERICITY_THRESHOLD: float = 0.25


def f_beta(precision: float, recall: float, beta: float = BETA) -> float:
    """F-beta. Devuelve 0.0 si el denominador es 0."""
    b2 = beta * beta
    denom = b2 * precision + recall
    if denom == 0:
        return 0.0
    return (1 + b2) * (precision * recall) / denom


class RunMetrics(BaseModel):
    """Metricas de UNA ejecucion de un approach sobre el caso golden."""

    approach: str
    n_findings: int
    n_golden: int
    recall: float
    precision: float
    genericity_rate: float
    grounding_rate: float
    tp_new: int
    fbeta: float
    meets_genericity_gate: bool
    primary_score: float  # F-beta si pasa el gate de genericidad, si no 0.0


def compute_run_metrics(
    approach: str,
    findings: list[Finding],
    adjudications: list[Adjudication],
    golden: list[GoldenIssue],
) -> RunMetrics:
    """Calcula las metricas de una ejecucion.

    - recall: GoldenIssues emparejados (via TP_MATCH) / total golden.
    - precision: hallazgos reales (TP_MATCH + TP_NEW) / total hallazgos.
    - genericity_rate: FP_GENERIC / total hallazgos.
    - grounding_rate: hallazgos con los 3 anclajes / total hallazgos
      (se mide sobre los Finding, independiente del juez).
    """
    n = len(findings)
    by_label: dict[AdjudicationLabel, int] = {lbl: 0 for lbl in AdjudicationLabel}
    matched_golden: set[str] = set()
    for a in adjudications:
        by_label[a.label] += 1
        if a.label == AdjudicationLabel.TP_MATCH and a.matched_golden_id:
            matched_golden.add(a.matched_golden_id)

    tp = by_label[AdjudicationLabel.TP_MATCH] + by_label[AdjudicationLabel.TP_NEW]

    recall = len(matched_golden) / len(golden) if golden else 0.0
    precision = tp / n if n else 0.0
    genericity_rate = by_label[AdjudicationLabel.FP_GENERIC] / n if n else 0.0
    grounding_rate = sum(1 for f in findings if f.is_grounded()) / n if n else 0.0

    fb = f_beta(precision, recall)
    gate = genericity_rate <= GENERICITY_THRESHOLD

    return RunMetrics(
        approach=approach,
        n_findings=n,
        n_golden=len(golden),
        recall=recall,
        precision=precision,
        genericity_rate=genericity_rate,
        grounding_rate=grounding_rate,
        tp_new=by_label[AdjudicationLabel.TP_NEW],
        fbeta=fb,
        meets_genericity_gate=gate,
        primary_score=fb if gate else 0.0,
    )


class SubsetRecall(BaseModel):
    """Recall sobre el subconjunto del golden con un `revealed_by` dado.

    Es la unidad de la ablacion del testimonio (ADR-007). Comparar el mismo
    subconjunto (p. ej. USER_ONLY) entre la condicion CON voz y SIN voz mide si el
    testimonio del usuario aporta al recall o solo al grounding.
    """

    revealed_by: RevealedBy
    n_golden: int
    n_matched: int
    recall: float


def recall_by_revealed_by(
    adjudications: list[Adjudication],
    golden: list[GoldenIssue],
) -> list[SubsetRecall]:
    """Desglosa el recall por la fuente que revela cada GoldenIssue.

    Devuelve una entrada por cada valor de `revealed_by` PRESENTE en el golden
    (los ausentes se omiten). El matching es el mismo que en `compute_run_metrics`:
    un golden esta emparejado si algun hallazgo lo referencia via TP_MATCH.
    """
    matched: set[str] = {
        a.matched_golden_id
        for a in adjudications
        if a.label == AdjudicationLabel.TP_MATCH and a.matched_golden_id
    }
    out: list[SubsetRecall] = []
    for rb in RevealedBy:
        subset = [g for g in golden if g.revealed_by == rb]
        if not subset:
            continue
        n_matched = sum(1 for g in subset if g.id in matched)
        out.append(
            SubsetRecall(
                revealed_by=rb,
                n_golden=len(subset),
                n_matched=n_matched,
                recall=n_matched / len(subset),
            )
        )
    return out


class Stat(BaseModel):
    """Media y desviacion tipica de una metrica sobre k ejecuciones."""

    mean: float
    std: float


class AggregateMetrics(BaseModel):
    """Agregado de k ejecuciones del mismo approach (media +/- std)."""

    approach: str
    k: int
    recall: Stat
    precision: Stat
    genericity_rate: Stat
    grounding_rate: Stat
    primary_score: Stat


def _stat(values: list[float]) -> Stat:
    if not values:
        return Stat(mean=0.0, std=0.0)
    mean = statistics.mean(values)
    # pstdev (poblacional): k es pequeno y describimos exactamente estas k corridas.
    std = statistics.pstdev(values) if len(values) > 1 else 0.0
    return Stat(mean=mean, std=std)


def aggregate(runs: list[RunMetrics]) -> AggregateMetrics:
    """Agrega k RunMetrics del mismo approach. Lanza si la lista esta vacia o mezcla approaches."""
    if not runs:
        raise ValueError("aggregate() necesita al menos una ejecucion.")
    approaches = {r.approach for r in runs}
    if len(approaches) > 1:
        raise ValueError(f"aggregate() mezcla approaches distintos: {approaches}")
    return AggregateMetrics(
        approach=runs[0].approach,
        k=len(runs),
        recall=_stat([r.recall for r in runs]),
        precision=_stat([r.precision for r in runs]),
        genericity_rate=_stat([r.genericity_rate for r in runs]),
        grounding_rate=_stat([r.grounding_rate for r in runs]),
        primary_score=_stat([r.primary_score for r in runs]),
    )


def beats(candidate: AggregateMetrics, baseline: AggregateMetrics) -> bool:
    """Regla de decision del plan: un approach 'gana' a otro si mejora la metrica
    primaria por un margen MAYOR que la varianza observada.

    Operativizacion: la media del candidato supera a la del baseline por mas que
    la suma de sus desviaciones tipicas (margen > ruido combinado).
    """
    margin = candidate.primary_score.mean - baseline.primary_score.mean
    noise = candidate.primary_score.std + baseline.primary_score.std
    return margin > noise
