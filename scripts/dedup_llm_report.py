"""Validacion de la capa SEMANTICA del dedup (LLM) sobre runs ya juzgados.

Como dedup_report.py pero para deduplicate_llm: mide cuanto colapsa el conteo y si el
agrupado del modelo es PURO (no funde golden distintos), usando las adjudicaciones -que
el dedup no ve- como vara independiente. A diferencia del determinista, gasta API (una
llamada por corrida). Para auditar pureza se agrupa sobre los hallazgos CRUDOS
(pre_dedup=False): cada crudo tiene su adjudicacion, asi el cruce con el golden es limpio.

Uso:
    uv run python scripts/dedup_llm_report.py runs/a2_eii_k3.json --approach p3
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from interaction_review import dedup_llm
from interaction_review.dedup import deduplicate
from interaction_review.schemas import Finding

_TP = {"tp_match", "tp_new"}


def _clusters_llm(findings: list[Finding]) -> list[list[Finding]]:
    """Reproduce la agrupacion de deduplicate_llm (pre_dedup=False) devolviendo miembros."""
    by_id = {f.id: f for f in findings}
    order = {f.id: n for n, f in enumerate(findings)}
    groups = dedup_llm._llm_groups(findings, None, 0.0)
    assigned: set[str] = set()
    clusters: list[list[Finding]] = []
    for ids in groups:
        members = [by_id[i] for i in dict.fromkeys(ids) if i in by_id and i not in assigned]
        if len(members) >= 2:
            assigned.update(m.id for m in members)
            clusters.append(members)
    for f in findings:
        if f.id not in assigned:
            clusters.append([f])
    clusters.sort(key=lambda c: min(order[m.id] for m in c))
    return clusters


def _eval_run(run: dict) -> dict:
    findings = [Finding.model_validate(x) for x in run["findings"]]
    adj = {a["finding_id"]: a for a in run["adjudications"]}
    n_raw = len(findings)
    n_det = len(deduplicate(findings))  # referencia: dedup determinista
    cov_before = {a["matched_golden_id"] for a in adj.values()
                  if a.get("label") == "tp_match" and a.get("matched_golden_id")}

    clusters = _clusters_llm(findings)
    cov_after, impure = set(), 0
    for c in clusters:
        gs = {adj[m.id]["matched_golden_id"] for m in c
              if adj.get(m.id, {}).get("label") == "tp_match" and adj[m.id].get("matched_golden_id")}
        cov_after |= gs
        if len(gs) >= 2:
            impure += 1
    return {
        "n_raw": n_raw, "n_det": n_det, "n_llm": len(clusters),
        "cov_before": len(cov_before), "cov_after": len(cov_after),
        "cov_lost": len(cov_before - cov_after), "impure": impure,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Valida la capa semantica del dedup (gasta API).")
    p.add_argument("run")
    p.add_argument("--approach", default="p3")
    args = p.parse_args(argv)
    data = json.loads(Path(args.run).read_text(encoding="utf-8"))
    runs = data["runs"].get(args.approach, [])
    if not runs or not runs[0].get("adjudications"):
        print(f"(sin adjudicaciones para {args.approach} en {args.run})")
        return 1
    rows = [_eval_run(r) for r in runs]

    def m(k):
        return statistics.mean(r[k] for r in rows)

    print(f"# Dedup-LLM @ {args.run} [{args.approach}] (k={len(rows)})\n")
    print(f"- n crudo:        {m('n_raw'):.1f}")
    print(f"- n dedup lexico: {m('n_det'):.1f}")
    print(f"- n dedup LLM:    {m('n_llm'):.1f}  (reduccion vs crudo {(1-m('n_llm')/m('n_raw'))*100:.0f}%)")
    print(f"- cobertura golden: {m('cov_before'):.1f} -> {m('cov_after'):.1f}  (perdida total {sum(r['cov_lost'] for r in rows)})")
    print(f"- clusters impuros (funden >=2 golden): {sum(r['impure'] for r in rows)} en {len(rows)} corridas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
