"""Re-judges the ALREADY saved findings of a run (without re-generating) and recomputes.

Useful when the judge is fixed: it reuses the expensive part (generation) and only
re-adjudicates + measures. Saves a *_rejudged.json and *_rejudged.md.

Usage:  LLM_BACKEND=ollama uv run python scripts/rejudge.py [runs/eii_k3.json]
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

# Defaults point at the v2 golden set (15 issues), the canonical one the validation
# runs use. The old v0 default (answer_key.json, 16 issues) silently mismatched any
# v2 run passed as argv[1] without a golden. The guard in main() catches the mismatch
# regardless of which combination is passed.
RUNS = sys.argv[1] if len(sys.argv) > 1 else "runs/eii_k3_v2.json"
GOLDEN = sys.argv[2] if len(sys.argv) > 2 else "data/golden/caso-EII/answer_key_v2.json"
DOSSIER = sys.argv[3] if len(sys.argv) > 3 else "data/golden/caso-EII/dossier_blind_v2.json"
OUT_JSON = str(Path(RUNS).with_suffix("")) + "_rejudged.json"
OUT_MD = str(Path(RUNS).with_suffix("")) + "_rejudged.md"
DETERMINISTIC = {"b0"}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def main() -> None:
    data = json.loads(Path(RUNS).read_text(encoding="utf-8"))
    golden = [GoldenIssue.model_validate(g) for g in json.loads(Path(GOLDEN).read_text(encoding="utf-8"))]
    dossier = Dossier.model_validate(json.loads(Path(DOSSIER).read_text(encoding="utf-8")))

    # Guard: re-judging against a golden that does not match the run silently produces
    # metrics different from the published ones. The run records how many golden it was
    # judged against; refuse to proceed if it disagrees with the loaded answer key.
    n_run = data.get("config", {}).get("n_golden")
    if n_run is not None and n_run != len(golden):
        raise SystemExit(
            f"Golden mismatch: {GOLDEN} has {len(golden)} issues but {RUNS} was judged "
            f"against {n_run}. Pass the matching answer_key + dossier as argv[2]/argv[3] "
            f"(v2 -> answer_key_v2.json + dossier_blind_v2.json; v0 -> answer_key.json + dossier_blind.json)."
        )

    approaches = list(data["runs"].keys())
    k = data["config"]["k"]
    log(f"Re-judging {RUNS} with judge={llm.judge_model()} | approaches={approaches} | k={k}")

    aggregates = {}
    new_runs: dict[str, list[dict]] = {}
    for name in approaches:
        runs = data["runs"][name]
        sets = runs[:1] if name in DETERMINISTIC else runs
        rms = []
        detail = []
        for i, det in enumerate(sets, start=1):
            findings = [Finding.model_validate(f) for f in det["findings"]]
            log(f"  [{name}] run {i}/{len(sets)} - re-judging {len(findings)} findings...")
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
    lines = [table, "", "## Decision rule (margin > noise)"]
    for cand, base in (("b1", "b0"), ("b2", "b1")):
        if cand in aggregates and base in aggregates:
            verdict = "WINS" if beats(aggregates[cand], aggregates[base]) else "does NOT win"
            dc, db = aggregates[cand].primary_score, aggregates[base].primary_score
            lines.append(f"- {cand} vs {base}: **{verdict}** ({dc.mean:.2f}+/-{dc.std:.2f} vs {db.mean:.2f}+/-{db.std:.2f})")
    out = "\n".join(lines)
    Path(OUT_MD).write_text(out, encoding="utf-8")
    log(f"\nWritten: {OUT_JSON} and {OUT_MD}\n")
    print(out)


if __name__ == "__main__":
    main()
