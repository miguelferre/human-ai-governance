"""Analisis de cobertura por issue del golden a partir de un fichero de corrida.

Lee un JSON guardado por `comparar --save` y el answer key, y muestra:
- por approach: hallazgos medios, tp_new medios, issues del golden emparejados, recall.
- cobertura issue-a-issue de B1 union B2: cuales se redescubren y cuales se escapan.

Uso:  uv run python scripts/coverage_report.py [runs/eii_k3.json] [answer_key.json]
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

RUNS = sys.argv[1] if len(sys.argv) > 1 else "runs/eii_k3.json"
GOLDEN = sys.argv[2] if len(sys.argv) > 2 else "data/golden/caso-EII/answer_key.json"


def main() -> None:
    data = json.loads(Path(RUNS).read_text(encoding="utf-8"))
    golden = json.loads(Path(GOLDEN).read_text(encoding="utf-8"))
    gids = [g["id"] for g in golden]

    print(f"# Cobertura — {data['config']['system_name']}")
    print(f"gen={data['config']['gen_model']} | judge={data['config']['judge_model']} "
          f"| k={data['config']['k']} | golden={len(gids)}\n")

    matched_by_llm: dict[str, int] = defaultdict(int)  # gid -> nº de corridas (b1/b2) que lo emparejan

    for name, runs in data["runs"].items():
        nruns = len(runs)
        n_find = [len(r["findings"]) for r in runs]
        n_new = [sum(1 for a in r["adjudications"] if a["label"] == "tp_new") for r in runs]
        # issues distintos emparejados en cada corrida -> media de recall
        per_run_matched = []
        for r in runs:
            m = {a["matched_golden_id"] for a in r["adjudications"]
                 if a["label"] == "tp_match" and a.get("matched_golden_id")}
            per_run_matched.append(m)
            if name in ("b1", "b2"):
                for gid in m:
                    matched_by_llm[gid] += 1
        recalls = [len(m) / len(gids) for m in per_run_matched]
        avg = lambda xs: sum(xs) / len(xs) if xs else 0  # noqa: E731
        print(f"## {name}  (n={nruns})")
        print(f"  hallazgos medios: {avg(n_find):.1f} | tp_new medios: {avg(n_new):.1f} "
              f"| recall medio: {avg(recalls):.2f}")
        union = set().union(*per_run_matched) if per_run_matched else set()
        print(f"  issues distintos emparejados (union de corridas): {len(union)}/{len(gids)}\n")

    # Cobertura issue-a-issue de B1 union B2
    total_llm_runs = sum(len(data["runs"].get(n, [])) for n in ("b1", "b2"))
    print("## Cobertura issue-a-issue (B1 union B2)")
    detectados = [g for g in golden if matched_by_llm.get(g["id"], 0) > 0]
    perdidos = [g for g in golden if matched_by_llm.get(g["id"], 0) == 0]
    print(f"  DETECTADOS: {len(detectados)}/{len(gids)} | PERDIDOS: {len(perdidos)}/{len(gids)}\n")
    print("  Detectados (id -> nº corridas que lo emparejan, de %d):" % total_llm_runs)
    for g in sorted(detectados, key=lambda g: -matched_by_llm[g["id"]]):
        print(f"    [{matched_by_llm[g['id']]:>2}] {g['id']}")
    print("\n  PERDIDOS (nunca emparejados por B1/B2):")
    for g in perdidos:
        print(f"    [ 0] {g['id']}  (sev {g['severity']})")


if __name__ == "__main__":
    main()
