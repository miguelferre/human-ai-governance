"""Per-issue coverage analysis of the golden from a run file.

Reads a JSON saved by `comparar --save` and the answer key, and shows:
- per approach: mean findings, mean tp_new, matched golden issues, recall.
- issue-by-issue coverage of B1 union B2: which are rediscovered and which slip through.

Usage:  uv run python scripts/coverage_report.py [runs/eii_k3.json] [answer_key.json]
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

    print(f"# Coverage - {data['config']['system_name']}")
    print(f"gen={data['config']['gen_model']} | judge={data['config']['judge_model']} "
          f"| k={data['config']['k']} | golden={len(gids)}\n")

    matched_by_llm: dict[str, int] = defaultdict(int)  # gid -> number of runs (b1/b2) that match it

    for name, runs in data["runs"].items():
        nruns = len(runs)
        n_find = [len(r["findings"]) for r in runs]
        n_new = [sum(1 for a in r["adjudications"] if a["label"] == "tp_new") for r in runs]
        # distinct issues matched in each run -> mean recall
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
        print(f"  mean findings: {avg(n_find):.1f} | mean tp_new: {avg(n_new):.1f} "
              f"| mean recall: {avg(recalls):.2f}")
        union = set().union(*per_run_matched) if per_run_matched else set()
        print(f"  distinct issues matched (union of runs): {len(union)}/{len(gids)}\n")

    # Issue-by-issue coverage of B1 union B2
    total_llm_runs = sum(len(data["runs"].get(n, [])) for n in ("b1", "b2"))
    print("## Issue-by-issue coverage (B1 union B2)")
    detectados = [g for g in golden if matched_by_llm.get(g["id"], 0) > 0]
    perdidos = [g for g in golden if matched_by_llm.get(g["id"], 0) == 0]
    print(f"  DETECTED: {len(detectados)}/{len(gids)} | MISSED: {len(perdidos)}/{len(gids)}\n")
    print("  Detected (id -> number of runs that match it, of %d):" % total_llm_runs)
    for g in sorted(detectados, key=lambda g: -matched_by_llm[g["id"]]):
        print(f"    [{matched_by_llm[g['id']]:>2}] {g['id']}")
    print("\n  MISSED (never matched by B1/B2):")
    for g in perdidos:
        print(f"    [ 0] {g['id']}  (sev {g['severity']})")


if __name__ == "__main__":
    main()
