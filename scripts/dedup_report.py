"""Validacion OFFLINE del deduplicado sobre runs ya juzgados (sin API).

El dedup agrupa por contenido y NO ve el golden ni las adjudicaciones. Aqui las
usamos -despues- como vara de medir independiente para responder dos preguntas:

  1. ¿Conserva la senal? La cobertura de golden tras fundir = union de los golden
     de cada cluster. Debe ser IDENTICA a la de antes (el dedup no tira hallazgos).
  2. ¿Es PURO? Un cluster es impuro si funde hallazgos adjudicados a golden DISTINTOS
     -> habria conflado dos problemas reales en un solo item del informe. Eso es el
     dano real del dedup, y se mide contra etiquetas que el dedup nunca vio.

Y la ganancia de producto: cuanto colapsa el conteo (~60-100 -> ~N) y cuantos
clusters quedan por problema (ideal: 1, no 5).

Uso:
    uv run python scripts/dedup_report.py runs/a2_eii_k3.json
    uv run python scripts/dedup_report.py runs/a2_eii_k3.json --sweep
    uv run python scripts/dedup_report.py runs/a2_eii_k3.json --threshold 0.55
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from interaction_review.dedup import DEFAULT_THRESHOLD
from interaction_review.schemas import Finding

_TP = {"tp_match", "tp_new"}


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _eval_run(run: dict, threshold: float) -> dict:
    """Metricas de un run individual antes/despues de deduplicar."""
    findings = [Finding.model_validate(x) for x in run["findings"]]
    adj = {a["finding_id"]: a for a in run["adjudications"]}

    n_before = len(findings)
    cov_before = {
        a["matched_golden_id"]
        for a in adj.values()
        if a.get("label") == "tp_match" and a.get("matched_golden_id")
    }
    tp_before = sum(1 for a in adj.values() if a.get("label") in _TP)

    # Para auditar pureza necesitamos saber que crudos cayeron en cada cluster.
    # deduplicate() devuelve representantes; re-derivamos los clusters con la misma
    # logica de id -> reconstruimos por id del representante no basta. En su lugar,
    # agrupamos nosotros replicando el criterio: mas simple y robusto -> mapear cada
    # finding a su cluster via un dedup "instrumentado".
    clusters = _clusters(findings, threshold)

    cov_after: set[str] = set()
    impure = 0
    tp_clusters = 0
    clusters_per_golden: dict[str, int] = {}
    for members in clusters:
        labels = [adj.get(m.id, {}) for m in members]
        goldens = {
            a.get("matched_golden_id")
            for a in labels
            if a.get("label") == "tp_match" and a.get("matched_golden_id")
        }
        cov_after |= goldens
        if len(goldens) >= 2:
            impure += 1
        if any(a.get("label") in _TP for a in labels):
            tp_clusters += 1
        for g in goldens:
            clusters_per_golden[g] = clusters_per_golden.get(g, 0) + 1

    n_after = len(clusters)
    # clusters por golden cubierto (ideal 1): media sobre los golden realmente cubiertos
    dup_factor = (
        statistics.mean(clusters_per_golden.values()) if clusters_per_golden else 0.0
    )
    return {
        "n_before": n_before,
        "n_after": n_after,
        "reduction": 1 - n_after / n_before if n_before else 0.0,
        "cov_before": len(cov_before),
        "cov_after": len(cov_after),
        "cov_lost": len(cov_before - cov_after),
        "impure_clusters": impure,
        "prec_before": tp_before / n_before if n_before else 0.0,
        "prec_after": tp_clusters / n_after if n_after else 0.0,
        "dup_factor_before": (
            statistics.mean(
                [
                    sum(
                        1
                        for a in adj.values()
                        if a.get("matched_golden_id") == g
                    )
                    for g in cov_before
                ]
            )
            if cov_before
            else 0.0
        ),
        "dup_factor_after": dup_factor,
    }


def _clusters(findings: list[Finding], threshold: float) -> list[list[Finding]]:
    """Reproduce la agrupacion de dedup.deduplicate, devolviendo los miembros.

    (deduplicate() devuelve ya fundidos; aqui necesitamos los miembros para auditar
    pureza contra el golden, asi que replicamos el mismo bucle por representante.)
    """
    from interaction_review.dedup import similarity

    clusters: list[list[Finding]] = []
    reps: list[Finding] = []
    for f in findings:
        best_i, best_sim = -1, threshold
        for i, rep in enumerate(reps):
            s = similarity(f, rep)
            if s >= best_sim:
                best_i, best_sim = i, s
        if best_i >= 0:
            clusters[best_i].append(f)
        else:
            clusters.append([f])
            reps.append(f)
    return clusters


def _agg(runs: list[dict], approach: str, threshold: float) -> dict:
    rows = [_eval_run(r, threshold) for r in runs]

    def m(k: str) -> float:
        return statistics.mean(r[k] for r in rows)

    return {
        "approach": approach,
        "k": len(rows),
        "n_before": m("n_before"),
        "n_after": m("n_after"),
        "reduction": m("reduction"),
        "cov_before": m("cov_before"),
        "cov_after": m("cov_after"),
        "cov_lost": sum(r["cov_lost"] for r in rows),
        "impure": sum(r["impure_clusters"] for r in rows),
        "prec_before": m("prec_before"),
        "prec_after": m("prec_after"),
        "dup_before": m("dup_factor_before"),
        "dup_after": m("dup_factor_after"),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Valida el deduplicado sobre un run juzgado.")
    p.add_argument("run", help="Ruta a un runs/*.json ya juzgado.")
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    p.add_argument("--sweep", action="store_true", help="Barre umbrales 0.40..0.75.")
    args = p.parse_args(argv)

    data = _load(args.run)
    runs_by_approach = data.get("runs", {})

    if args.sweep:
        thresholds = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
        print(f"# Barrido de umbral — {args.run}\n")
        print("| approach | T | n_antes | n_despues | reduccion | cov_perdida | impuros | dup_antes | dup_despues |")
        print("|---|---|---|---|---|---|---|---|---|")
        for approach, runs in runs_by_approach.items():
            if not runs or not runs[0].get("adjudications"):
                continue
            for t in thresholds:
                a = _agg(runs, approach, t)
                print(
                    f"| {approach} | {t:.2f} | {a['n_before']:.0f} | {a['n_after']:.1f} | "
                    f"{a['reduction']*100:.0f}% | {a['cov_lost']} | {a['impure']} | "
                    f"{a['dup_before']:.1f} | {a['dup_after']:.1f} |"
                )
        return 0

    t = args.threshold
    print(f"# Deduplicado @ T={t:.2f} -- {args.run}\n")
    print("| approach | k | n_antes | n_despues | reduccion | cov antes->desp | cov_perdida | impuros | prec antes->desp | dup/golden antes->desp |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for approach, runs in runs_by_approach.items():
        if not runs or not runs[0].get("adjudications"):
            continue
        a = _agg(runs, approach, t)
        print(
            f"| {approach} | {a['k']} | {a['n_before']:.0f} | {a['n_after']:.1f} | "
            f"{a['reduction']*100:.0f}% | {a['cov_before']:.1f}->{a['cov_after']:.1f} | "
            f"{a['cov_lost']} | {a['impure']} | "
            f"{a['prec_before']:.2f}->{a['prec_after']:.2f} | "
            f"{a['dup_before']:.1f}->{a['dup_after']:.1f} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
