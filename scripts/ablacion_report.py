"""Report of the user testimony ablation (ADR-007).

Two modes:

  dist    OFFLINE, no API. Given one or more answer_key files labeled with
          `revealed_by`, it prints the distribution (user_only / tech_only / both)
          per case and aggregated. It is the CEILING of the testimony's contribution
          to recall: if there is barely any user_only, the voice cannot contribute
          much recall even if it wanted to. An honest result on its own.

  compare Requires already-judged runs (produced by `compare`, spends API). Given
          the labeled golden and two runs -WITH voice and WITHOUT voice (dossier
          without END_USER)-, it prints the recall per subset in each condition and
          the delta in user_only, which is the underlying question: does recall drop
          when the voice is removed?

Usage:
    uv run python scripts/ablacion_report.py dist data/external/*/answer_key.json
    uv run python scripts/ablacion_report.py compare \\
        --golden data/external/robodebt-hard/answer_key.json \\
        --voz runs/robodebt_voz_k3.json --sin-voz runs/robodebt_sinvoz_k3.json \\
        --approach p3
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from interaction_review.ablation import revealed_by_distribution
from interaction_review.metrics import recall_by_revealed_by
from interaction_review.schemas import Adjudication, GoldenIssue, RevealedBy

_ORDER = [RevealedBy.USER_ONLY, RevealedBy.BOTH, RevealedBy.TECH_ONLY, RevealedBy.UNKNOWN]


def _load(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _golden(path: str) -> list[GoldenIssue]:
    return [GoldenIssue.model_validate(x) for x in _load(path)]


def _case_name(path: str) -> str:
    # data/external/<case>/answer_key.json -> <case>
    return Path(path).parent.name or Path(path).stem


# --------------------------------------------------------------------------- #
# dist mode: revealed_by distribution (offline).
# --------------------------------------------------------------------------- #
def cmd_dist(args: argparse.Namespace) -> int:
    rows: list[tuple[str, dict[RevealedBy, int]]] = []
    omitidos: list[str] = []
    for path in args.goldens:
        try:
            golden = _golden(path)
        except FileNotFoundError:
            print(f"(warning) does not exist: {path}")
            continue
        dist = revealed_by_distribution(golden)
        # A case where EVERYTHING is unknown is not labeled -> it does not take part in the ablation.
        # (This way a glob over data/external/* keeps only the cases with testimony.)
        etiquetados = sum(v for rb, v in dist.items() if rb is not RevealedBy.UNKNOWN)
        if etiquetados == 0:
            omitidos.append(_case_name(path))
            continue
        rows.append((_case_name(path), dist))

    if not rows:
        print("No golden labeled with revealed_by was loaded.")
        return 1

    print("# Testimony ablation - golden distribution (offline, ADR-007)\n")
    print("How many GoldenIssue each source type reveals. `user_only` is the ceiling of "
          "the testimony's contribution to recall.\n")
    header = "| case | total | user_only | both | tech_only | unknown | %voice-dependent |"
    print(header)
    print("|---|---|---|---|---|---|---|")

    tot = {rb: 0 for rb in RevealedBy}
    total_issues = 0
    for name, dist in rows:
        n = sum(dist.values())
        total_issues += n
        for rb in RevealedBy:
            tot[rb] += dist[rb]
        # "voice-dependent" = user_only (only the voice reveals it). Recall ceiling of the testimony.
        pct = dist[RevealedBy.USER_ONLY] / n * 100 if n else 0.0
        print(
            f"| {name} | {n} | {dist[RevealedBy.USER_ONLY]} | {dist[RevealedBy.BOTH]} | "
            f"{dist[RevealedBy.TECH_ONLY]} | {dist[RevealedBy.UNKNOWN]} | {pct:.0f}% |"
        )

    pct_tot = tot[RevealedBy.USER_ONLY] / total_issues * 100 if total_issues else 0.0
    print(
        f"| **TOTAL** | **{total_issues}** | **{tot[RevealedBy.USER_ONLY]}** | "
        f"**{tot[RevealedBy.BOTH]}** | **{tot[RevealedBy.TECH_ONLY]}** | "
        f"**{tot[RevealedBy.UNKNOWN]}** | **{pct_tot:.0f}%** |"
    )
    print(
        f"\n> Reading: {tot[RevealedBy.USER_ONLY]}/{total_issues} problems "
        f"({pct_tot:.0f}%) are revealed only by the user's voice; "
        f"{tot[RevealedBy.BOTH]} are revealed by voice AND documentation (there the testimony "
        f"contributes grounding, not recall)."
    )
    if omitidos:
        print(
            f"\n> Omitted {len(omitidos)} unlabeled cases (they do not take part in the ablation): "
            f"{', '.join(sorted(omitidos))}."
        )
    return 0


# --------------------------------------------------------------------------- #
# compare mode: recall per subset with voice vs without voice (needs runs).
# --------------------------------------------------------------------------- #
def _adjs_per_run(data: dict, approach: str) -> list[list[Adjudication]]:
    runs = data.get("runs", {}).get(approach, [])
    out: list[list[Adjudication]] = []
    for r in runs:
        adj = r.get("adjudications")
        if not adj:
            continue
        out.append([Adjudication.model_validate(a) for a in adj])
    return out


def _mean_recall_by_subset(
    runs_adj: list[list[Adjudication]], golden: list[GoldenIssue]
) -> dict[RevealedBy, tuple[float, float, int]]:
    """Mean (and std) of recall per subset over k runs. Returns {rb: (mean, std, n_golden)}."""
    per_rb: dict[RevealedBy, list[float]] = {rb: [] for rb in RevealedBy}
    n_by_rb: dict[RevealedBy, int] = {}
    for adj in runs_adj:
        for sr in recall_by_revealed_by(adj, golden):
            per_rb[sr.revealed_by].append(sr.recall)
            n_by_rb[sr.revealed_by] = sr.n_golden
    out: dict[RevealedBy, tuple[float, float, int]] = {}
    for rb, vals in per_rb.items():
        if not vals:
            continue
        mean = statistics.mean(vals)
        std = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        out[rb] = (mean, std, n_by_rb.get(rb, 0))
    return out


def cmd_compare(args: argparse.Namespace) -> int:
    golden = _golden(args.golden)
    voz = _mean_recall_by_subset(_adjs_per_run(_load(args.voz), args.approach), golden)
    sin = _mean_recall_by_subset(_adjs_per_run(_load(args.sin_voz), args.approach), golden)

    if not voz or not sin:
        print(
            f"There are no adjudications for approach '{args.approach}' in one of the runs. "
            "Was `compare` run with --save over both dossiers (with voice and without voice)?"
        )
        return 1

    print(f"# Testimony ablation - recall per subset ({args.approach}, ADR-007)\n")
    print("| revealed_by | n | recall WITH voice | recall WITHOUT voice | delta |")
    print("|---|---|---|---|---|")
    for rb in _ORDER:
        if rb not in voz and rb not in sin:
            continue
        mv, sv, n = voz.get(rb, (0.0, 0.0, 0))
        ms, ss, n2 = sin.get(rb, (0.0, 0.0, n))
        delta = mv - ms
        print(
            f"| {rb.value} | {n or n2} | {mv:.2f}±{sv:.2f} | {ms:.2f}±{ss:.2f} | "
            f"{delta:+.2f} |"
        )

    # The headline: the delta in user_only.
    if RevealedBy.USER_ONLY in voz:
        mv = voz[RevealedBy.USER_ONLY][0]
        ms = sin.get(RevealedBy.USER_ONLY, (0.0, 0.0, 0))[0]
        drop = mv - ms
        print(
            f"\n> **Headline:** on the problems that only the voice reveals, the recall goes from "
            f"{mv:.2f} (with voice) to {ms:.2f} (without voice), delta {drop:+.2f}. "
            + (
                "The testimony DOES contribute recall."
                if drop >= 0.15
                else "The testimony contributes little recall (its value is in the grounding)."
            )
        )
    else:
        print("\n> There is no user_only subset in this golden: nothing to isolate here.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Report of the testimony ablation (ADR-007).")
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("dist", help="revealed_by distribution of the golden (offline, no API).")
    pd.add_argument("goldens", nargs="+", help="Paths to labeled answer_key.json files.")
    pd.set_defaults(func=cmd_dist)

    pc = sub.add_parser("compare", help="Recall per subset with voice vs without voice (needs runs).")
    pc.add_argument("--golden", required=True, help="labeled answer_key.json.")
    pc.add_argument("--voz", required=True, help="runs/*.json of the dossier WITH voice.")
    pc.add_argument("--sin-voz", required=True, dest="sin_voz", help="runs/*.json of the dossier WITHOUT voice.")
    pc.add_argument("--approach", default="p3", help="Approach to compare (default: p3).")
    pc.set_defaults(func=cmd_compare)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
