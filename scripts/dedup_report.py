"""OFFLINE validation of the deduplication over already-judged runs (no API).

The dedup groups by content and does NOT see the golden or the adjudications. Here
we use them -afterwards- as an independent yardstick to answer two questions:

  1. Does it preserve the signal? The golden coverage after merging = union of the
     goldens of each cluster. It must be IDENTICAL to the one before (the dedup does
     not drop findings).
  2. Is it PURE? A cluster is impure if it merges findings adjudicated to DIFFERENT
     goldens -> it would have conflated two real problems into a single item of the
     report. That is the real harm of the dedup, and it is measured against labels
     the dedup never saw.

And the product gain: how much the count collapses (~60-100 -> ~N) and how many
clusters remain per problem (ideal: 1, not 5).

Usage:
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
    """Metrics of an individual run before/after deduplicating."""
    findings = [Finding.model_validate(x) for x in run["findings"]]
    adj = {a["finding_id"]: a for a in run["adjudications"]}

    n_before = len(findings)
    cov_before = {
        a["matched_golden_id"]
        for a in adj.values()
        if a.get("label") == "tp_match" and a.get("matched_golden_id")
    }
    tp_before = sum(1 for a in adj.values() if a.get("label") in _TP)

    # To audit purity we need to know which raw findings fell into each cluster.
    # deduplicate() returns representatives; re-deriving the clusters by the id of the
    # representative is not enough. Instead, we group them ourselves replicating the
    # criterion: simpler and more robust -> map each finding to its cluster via an
    # "instrumented" dedup.
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
    # clusters per covered golden (ideal 1): mean over the goldens actually covered
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
    """Reproduces the grouping of dedup.deduplicate, returning the members.

    (deduplicate() returns them already merged; here we need the members to audit
    purity against the golden, so we replicate the same loop by representative.)
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
    p = argparse.ArgumentParser(description="Validates the deduplication over a judged run.")
    p.add_argument("run", help="Path to an already-judged runs/*.json.")
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    p.add_argument("--sweep", action="store_true", help="Sweeps thresholds 0.40..0.75.")
    args = p.parse_args(argv)

    data = _load(args.run)
    runs_by_approach = data.get("runs", {})

    if args.sweep:
        thresholds = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
        print(f"# Threshold sweep - {args.run}\n")
        print("| approach | T | n_before | n_after | reduction | cov_lost | impure | dup_before | dup_after |")
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
    print(f"# Deduplication @ T={t:.2f} -- {args.run}\n")
    print("| approach | k | n_before | n_after | reduction | cov before->after | cov_lost | impure | prec before->after | dup/golden before->after |")
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
