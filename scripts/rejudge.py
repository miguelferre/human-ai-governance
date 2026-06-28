"""Re-juzga los hallazgos YA guardados de una corrida (sin re-generar) y recalcula.

Util cuando se arregla el juez: reaprovecha la parte cara (generacion) y solo
vuelve a adjudicar + medir. Guarda un *_rejudged.json y *_rejudged.md.

Uso:  LLM_BACKEND=ollama uv run python scripts/rejudge.py [runs/eii_k3.json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from interaction_review import judge as J
from interaction_review import llm
from interaction_review.metrics import aggregate, beats, compute_run_metrics
from interaction_review.report import render_metrics_md
from interaction_review.schemas import Dossier, Finding, GoldenIssue

RUNS = sys.argv[1] if len(sys.argv) > 1 else "runs/eii_k3.json"
GOLDEN = "data/golden/caso-EII/answer_key.json"
DOSSIER = "data/golden/caso-EII/dossier_blind.json"
OUT_JSON = RUNS.replace(".json", "_rejudged.json")
OUT_MD = RUNS.replace(".json", "_rejudged.md")
DETERMINISTIC = {"b0"}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def main() -> None:
    data = json.loads(Path(RUNS).read_text(encoding="utf-8"))
    golden = [GoldenIssue.model_validate(g) for g in json.loads(Path(GOLDEN).read_text(encoding="utf-8"))]
    dossier = Dossier.model_validate(json.loads(Path(DOSSIER).read_text(encoding="utf-8")))
    approaches = list(data["runs"].keys())
    k = data["config"]["k"]
    log(f"Re-juzgando {RUNS} con juez={llm.judge_model()} | approaches={approaches} | k={k}")

    aggregates = {}
    new_runs: dict[str, list[dict]] = {}
    for name in approaches:
        runs = data["runs"][name]
        sets = runs[:1] if name in DETERMINISTIC else runs
        rms = []
        detail = []
        for i, det in enumerate(sets, start=1):
            findings = [Finding.model_validate(f) for f in det["findings"]]
            log(f"  [{name}] corrida {i}/{len(sets)} — re-juzgando {len(findings)} hallazgos...")
            adjs = J.adjudicate(findings, golden, dossier)
            rm = compute_run_metrics(name, findings, adjs, golden)
            rms.append(rm)
            detail.append(
                {
                    "findings": [f.model_dump() for f in findings],
                    "adjudications": [a.model_dump() for a in adjs],
                    "metrics": rm.model_dump(),
                }
            )
            log(f"      recall={rm.recall:.2f} prec={rm.precision:.2f} gen={rm.genericity_rate:.2f}")
        if name in DETERMINISTIC and k > 1:
            rms = rms * k
            detail = detail * k
        aggregates[name] = aggregate(rms)
        new_runs[name] = detail

    config = dict(data["config"])
    config["rejudged_with"] = llm.judge_model()
    result = {"config": config, "aggregates": {n: a.model_dump() for n, a in aggregates.items()}, "runs": new_runs}
    Path(OUT_JSON).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    table = render_metrics_md([aggregates[a] for a in approaches])
    lines = [table, "", "## Regla de decision (margen > ruido)"]
    for cand, base in (("b1", "b0"), ("b2", "b1")):
        if cand in aggregates and base in aggregates:
            verdict = "GANA" if beats(aggregates[cand], aggregates[base]) else "NO gana"
            dc, db = aggregates[cand].primary_score, aggregates[base].primary_score
            lines.append(f"- {cand} vs {base}: **{verdict}** ({dc.mean:.2f}+/-{dc.std:.2f} vs {db.mean:.2f}+/-{db.std:.2f})")
    out = "\n".join(lines)
    Path(OUT_MD).write_text(out, encoding="utf-8")
    log(f"\nEscrito: {OUT_JSON} y {OUT_MD}\n")
    print(out)


if __name__ == "__main__":
    main()
