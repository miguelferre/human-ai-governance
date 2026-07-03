"""Reviewer CLI. Commands: prefill / ingest / review / evaluate / compare.

The v1 output is command-line only, never a UI (see plan).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from interaction_review.approaches import REGISTRY
from interaction_review.dedup import deduplicate
from interaction_review.dedup_llm import deduplicate_llm
from interaction_review.guidelines import all_guidelines
from interaction_review.llm import LLMNotConfigured, gen_model
from interaction_review.metrics import aggregate, beats, compute_run_metrics
from interaction_review.report import (
    render_findings_md,
    render_metrics_md,
    render_regulatory_crosswalk,
)
from interaction_review.report_html import render_findings_html
from interaction_review.runner import run_experiment
from interaction_review.schemas import (
    Adjudication,
    Dossier,
    Finding,
    GoldenIssue,
    Guideline,
    GuidelineCorpus,
)


def _load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _tool_version() -> str:
    try:
        return version("interaction-review")
    except PackageNotFoundError:
        return "dev"


def _select_guidelines(corpus_arg: str) -> list[Guideline]:
    valid = {c.value: c for c in GuidelineCorpus}  # {"HAX": ..., "PAIR": ...}
    wanted = set()
    for raw in corpus_arg.split(","):
        c = raw.strip().upper()
        if not c:
            continue
        if c not in valid:
            raise SystemExit(
                f"Unknown corpus {raw.strip()!r}. Valid options: "
                f"{', '.join(sorted(valid)).lower()} (e.g. --corpus hax,pair)."
            )
        wanted.add(valid[c])
    if not wanted:
        raise SystemExit("No corpus selected. Use --corpus hax, pair, or hax,pair.")
    return [g for g in all_guidelines() if g.corpus in wanted]


def _emit(text: str, out: str | None) -> None:
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(f"Written: {out}")
    else:
        print(text)


def _maybe_dedup(findings: list[Finding], *, dedup: bool, dedup_llm: bool) -> list[Finding]:
    """Applies the requested consolidation (dedup_llm takes priority over dedup).

    Shared by the normal and the 'auto' path so both honor the flags (before, the
    router path silently ignored them).
    """
    if dedup_llm:
        before = len(findings)
        findings = deduplicate_llm(findings)
        print(f"[dedup-llm] {before} -> {len(findings)} findings consolidated.", file=sys.stderr)
    elif dedup:
        before = len(findings)
        findings = deduplicate(findings)
        print(f"[dedup] {before} -> {len(findings)} findings consolidated.", file=sys.stderr)
    return findings


def cmd_review(args: argparse.Namespace) -> int:
    dossier = Dossier.model_validate(_load_json(args.dossier))
    guidelines = _select_guidelines(args.corpus)

    # 'auto' = product router: picks b1 (easy) or p3+dedup (hard) by coverage.
    if args.approach == "auto":
        from interaction_review.router import route

        findings, choice = route(dossier, guidelines)
        print(f"[router] {choice} -> {len(findings)} findings.", file=sys.stderr)
        # the router already dedups its p3 branch; honor an explicit --dedup/--dedup-llm too
        findings = _maybe_dedup(findings, dedup=args.dedup, dedup_llm=args.dedup_llm)
        label = f"auto ({choice})"
    else:
        approach = REGISTRY.get(args.approach)
        if approach is None:
            print(
                f"Approach '{args.approach}' not available. Available: {sorted(REGISTRY)}",
                file=sys.stderr,
            )
            return 2
        # p3/p3n are verbose by design -> dedup on by default (disable with --no-dedup)
        dedup = args.dedup or (args.approach in ("p3", "p3n") and not args.no_dedup)
        findings = _maybe_dedup(approach(dossier, guidelines), dedup=dedup, dedup_llm=args.dedup_llm)
        label = args.approach

    # Provenance for the report (it goes into a compliance file, so date/model/version matter).
    meta = {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "tool_version": _tool_version(),
        "model": "deterministic (no model)" if args.approach == "b0" else gen_model(),
    }
    if args.format == "html":
        report = render_findings_html(
            dossier, findings, label, include_crosswalk=args.crosswalk, meta=meta
        )
    else:
        report = render_findings_md(dossier, findings, label, meta=meta)
        if args.crosswalk:
            report = report + "\n" + render_regulatory_crosswalk(findings)
    _emit(report, args.out)
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    golden = [GoldenIssue.model_validate(x) for x in _load_json(args.golden)]

    # From a compare runs/*.json: read findings + adjudications for one run directly.
    # Closes the compare -> evaluate loop (before, --adjudications wanted a JSON no tool wrote).
    if args.run:
        data = _load_json(args.run)
        runs = data.get("runs", {}).get(args.approach)
        if not runs:
            print(
                f"[evaluate] no runs for approach {args.approach!r} in {args.run}. "
                f"Available: {sorted(data.get('runs', {}))}.",
                file=sys.stderr,
            )
            return 2
        if not 0 <= args.idx < len(runs):
            print(f"[evaluate] --idx {args.idx} out of range (0..{len(runs) - 1}).", file=sys.stderr)
            return 2
        det = runs[args.idx]
        findings = [Finding.model_validate(x) for x in det.get("findings", [])]
        adjudications = [Adjudication.model_validate(x) for x in det.get("adjudications", [])]
        if not adjudications:
            print(
                f"[evaluate] run {args.idx} of {args.approach!r} has no adjudications "
                "(is it a .gen.json checkpoint?).",
                file=sys.stderr,
            )
            return 2
        run = compute_run_metrics(args.approach, findings, adjudications, golden)
        _emit(render_metrics_md([aggregate([run])]), args.out)
        return 0

    if not args.findings and not args.dossier:
        print(
            "[evaluate] needs --run (compare output), --findings (precomputed), or --dossier.",
            file=sys.stderr,
        )
        return 2
    # Findings: either loaded from a file, or generated by running the approach.
    if args.findings:
        findings = [Finding.model_validate(x) for x in _load_json(args.findings)]
    else:
        dossier = Dossier.model_validate(_load_json(args.dossier))
        approach = REGISTRY.get(args.approach)
        if approach is None:
            print(f"Approach '{args.approach}' not available.", file=sys.stderr)
            return 2
        findings = approach(dossier, _select_guidelines(args.corpus))

    if not args.adjudications:
        grounded = sum(1 for f in findings if f.is_grounded())
        n = len(findings)
        pct = (grounded / n * 100) if n else 0.0
        print(
            "Without --adjudications recall/precision cannot be computed "
            "(they require the LLM judge + review, F2).\n"
            f"Grounding only: {grounded}/{n} findings anchored ({pct:.0f}%) over {len(golden)} golden."
        )
        return 0

    adjudications = [Adjudication.model_validate(x) for x in _load_json(args.adjudications)]
    run = compute_run_metrics(args.approach, findings, adjudications, golden)
    agg = aggregate([run])
    _emit(render_metrics_md([agg]), args.out)
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    from interaction_review.ingest import ingest_templates

    try:
        dossier = ingest_templates(
            profile=args.profile,
            experience=args.experience,
            inventory=args.inventory,
            system_name=args.system_name,
            domain=args.domain,
        )
    except (ValueError, FileNotFoundError) as e:
        print(f"[ingest] {e}", file=sys.stderr)
        return 2

    text = json.dumps(dossier.model_dump(mode="json"), indent=2, ensure_ascii=False)
    print(
        f"[ingest] {len(dossier.sources)} sources -> dossier of '{dossier.system_name}'.",
        file=sys.stderr,
    )
    _emit(text, args.out)
    return 0


def cmd_prefill(args: argparse.Namespace) -> int:
    from interaction_review.smart_ingest import prefill_document

    try:
        filled = prefill_document(
            args.doc, kind=args.type, template_file=args.template, model=args.model
        )
    except (ValueError, FileNotFoundError) as e:
        print(f"[prefill] {e}", file=sys.stderr)
        return 2
    except LLMNotConfigured as e:
        print(f"[LLM not configured] {e}", file=sys.stderr)
        return 3

    print(
        f"[prefill] template '{args.type}' pre-filled from {Path(args.doc).name}. "
        "REVIEW the answers before 'ingest': the model may have missed or misread "
        "something, and blank slots are fields the document did not cover.",
        file=sys.stderr,
    )
    _emit(filled, args.out)
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    dossier = Dossier.model_validate(_load_json(args.dossier))
    golden = [GoldenIssue.model_validate(x) for x in _load_json(args.golden)]
    guidelines = _select_guidelines(args.corpus)
    approaches = [a.strip() for a in args.approaches.split(",") if a.strip()]

    if args.k < 1:
        print("[compare] --k must be >= 1.", file=sys.stderr)
        return 2
    unknown = [a for a in approaches if a not in REGISTRY]
    if unknown:
        extra = " ('auto' is a review-only router, not a comparable rung)" if "auto" in unknown else ""
        print(
            f"[compare] unknown approach(es): {unknown}. Available: {sorted(REGISTRY)}{extra}.",
            file=sys.stderr,
        )
        return 2

    try:
        result = run_experiment(
            dossier=dossier,
            golden=golden,
            guidelines=guidelines,
            approaches=approaches,
            k=args.k,
            save_path=args.save,
        )
    except LLMNotConfigured as e:
        print(f"[LLM not configured] {e}", file=sys.stderr)
        return 3

    aggs = result["_aggregate_objs"]
    table = render_metrics_md([aggs[a] for a in approaches if a in aggs])

    # Decision rule (ADR-002): each rung must beat the previous one.
    decision_lines = ["", "## Decision rule (margin > noise)"]
    for cand, base in (("b1", "b0"), ("b2", "b1")):
        if cand in aggs and base in aggs:
            verdict = "WINS" if beats(aggs[cand], aggs[base]) else "does NOT win"
            dc = aggs[cand].primary_score
            db = aggs[base].primary_score
            decision_lines.append(
                f"- {cand} vs {base}: **{verdict}** "
                f"(primary {dc.mean:.2f}±{dc.std:.2f} vs {db.mean:.2f}±{db.std:.2f})"
            )
    config = result["config"]
    footer = (
        f"\n> gen_model={config['gen_model']} | judge_model={config['judge_model']} | "
        f"k={config['k']} | golden={config['n_golden']}"
    )
    _emit(table + "\n" + "\n".join(decision_lines) + footer, args.out)
    if args.save:
        print(f"Raw output saved to: {args.save}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="interaction-review",
        description="Human-AI interaction layer reviewer (HAX-18 + PAIR).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pr = sub.add_parser("review", help="Generates a findings report for a system.")
    pr.add_argument("--dossier", required=True, help="JSON with the system Dossier.")
    pr.add_argument(
        "--approach",
        default="p3",
        help="Approach: p3 (default, the product) / b0/b1/b2/p3n/a4, or 'auto' "
        "(router: b1 easy / p3+dedup hard). Needs an LLM except b0.",
    )
    pr.add_argument("--corpus", default="hax,pair", help="Corpus: hax, pair or both (default: hax,pair).")
    pr.add_argument(
        "--dedup",
        action="store_true",
        help="Consolidates near-duplicate findings, deterministic. On by default for p3/p3n.",
    )
    pr.add_argument(
        "--no-dedup",
        action="store_true",
        help="Disables the default dedup for p3/p3n (emit the raw block-by-block findings).",
    )
    pr.add_argument(
        "--dedup-llm",
        action="store_true",
        help="SEMANTIC consolidation with the LLM (lexical dedup + LLM layer; uses API). Takes priority over --dedup.",
    )
    pr.add_argument(
        "--crosswalk",
        action="store_true",
        help="Appends the regulatory mapping (EU AI Act / NIST AI RMF) of the findings. Indicative (ADR-008).",
    )
    pr.add_argument(
        "--format",
        choices=["md", "html"],
        default="md",
        help="Report format: md (default) or html (self-contained, prints to PDF).",
    )
    pr.add_argument("--out", default=None, help="Output file (default: stdout). Use .html with --format html.")
    pr.set_defaults(func=cmd_review)

    pe = sub.add_parser("evaluate", help="Computes metrics against a golden set.")
    pe.add_argument("--golden", required=True, help="JSON with the list of GoldenIssue.")
    pe.add_argument("--run", default=None, help="compare runs/*.json: read findings+adjudications for --approach/--idx.")
    pe.add_argument("--idx", type=int, default=0, help="Run index within --run (default: 0).")
    pe.add_argument("--dossier", default=None, help="Dossier JSON (if --findings is not passed).")
    pe.add_argument("--findings", default=None, help="JSON with already-generated findings.")
    pe.add_argument("--adjudications", default=None, help="JSON with adjudications (LLM judge + review).")
    pe.add_argument("--approach", default="b0", help="Approach: label, or the key to read from --run (default: b0).")
    pe.add_argument("--corpus", default="hax,pair", help="Corpus (default: hax,pair).")
    pe.add_argument("--out", default=None, help="Output .md file (default: stdout).")
    pe.set_defaults(func=cmd_evaluate)

    pi = sub.add_parser(
        "ingest",
        help="Turns filled templates (01/02/03) into a Dossier JSON. Deterministic, no API.",
    )
    pi.add_argument("--profile", action="append", default=[], help="Filled template 01 (repeatable: several technicians).")
    pi.add_argument("--experience", action="append", default=[], help="Filled template 02 (repeatable: several users).")
    pi.add_argument("--inventory", default=None, help="Filled template 03 (document inventory).")
    pi.add_argument("--system-name", default=None, help="System name (defaults to the one in the profile).")
    pi.add_argument("--domain", default=None, help="Domain (defaults to the one in the profile).")
    pi.add_argument("--out", default=None, help="dossier.json output file (default: stdout).")
    pi.set_defaults(func=cmd_ingest)

    pp = sub.add_parser(
        "prefill",
        help="Pre-fills a template (01/02) from a document (PDF/model card/interview) with the LLM. "
        "Requires ANTHROPIC_API_KEY unless LLM_BACKEND=ollama.",
    )
    pp.add_argument("--doc", required=True, help="Source document: .pdf, .md or .txt.")
    pp.add_argument(
        "--type",
        default="profile",
        choices=["profile", "experience"],
        help="Template to pre-fill: 'profile' (from a PDF/model card) or 'experience' (from a user "
        "interview transcript). The inventory (03) is a checkbox list: fill it by hand.",
    )
    pp.add_argument(
        "--template",
        default=None,
        help="Path to the template to use (overrides --type; to pre-fill any template).",
    )
    pp.add_argument("--model", default=None, help="Generator model (default: the LLM_BACKEND one).")
    pp.add_argument("--out", default=None, help="Output .md file (default: stdout).")
    pp.set_defaults(func=cmd_prefill)

    pc = sub.add_parser(
        "compare",
        help="Runs approaches k times, adjudicates with the LLM judge and compares (F2). Requires ANTHROPIC_API_KEY unless b0 only.",
    )
    pc.add_argument("--dossier", required=True, help="Dossier JSON (blind).")
    pc.add_argument("--golden", required=True, help="JSON with the list of GoldenIssue.")
    pc.add_argument("--approaches", default="b0,b1,b2", help="Comma-separated list (default: b0,b1,b2).")
    pc.add_argument("--k", type=int, default=3, help="Repetitions per approach (default: 3).")
    pc.add_argument("--corpus", default="hax,pair", help="Corpus (default: hax,pair).")
    pc.add_argument("--save", default=None, help="Path to save the raw JSON (e.g. runs/eii.json).")
    pc.add_argument("--out", default=None, help="Output .md file (default: stdout).")
    pc.set_defaults(func=cmd_compare)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
