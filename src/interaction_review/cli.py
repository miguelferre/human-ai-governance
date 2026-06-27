"""CLI del revisor. Dos comandos: `revisar` (informe) y `evaluar` (metricas).

La salida v1 es por linea de comandos, nunca interfaz (ver plan).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from interaction_review.approaches import REGISTRY
from interaction_review.guidelines import all_guidelines
from interaction_review.metrics import aggregate, compute_run_metrics
from interaction_review.report import render_findings_md, render_metrics_md
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


def _select_guidelines(corpus_arg: str) -> list[Guideline]:
    wanted = {GuidelineCorpus(c.strip().upper()) for c in corpus_arg.split(",") if c.strip()}
    return [g for g in all_guidelines() if g.corpus in wanted]


def _emit(text: str, out: str | None) -> None:
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(f"Escrito: {out}")
    else:
        print(text)


def cmd_revisar(args: argparse.Namespace) -> int:
    dossier = Dossier.model_validate(_load_json(args.dossier))
    guidelines = _select_guidelines(args.corpus)
    approach = REGISTRY.get(args.approach)
    if approach is None:
        print(
            f"Approach '{args.approach}' no disponible. Disponibles: {sorted(REGISTRY)}",
            file=sys.stderr,
        )
        return 2
    findings = approach(dossier, guidelines)
    _emit(render_findings_md(dossier, findings, args.approach), args.out)
    return 0


def cmd_evaluar(args: argparse.Namespace) -> int:
    # Hallazgos: o se cargan de fichero, o se generan corriendo el approach.
    if args.findings:
        findings = [Finding.model_validate(x) for x in _load_json(args.findings)]
    else:
        dossier = Dossier.model_validate(_load_json(args.dossier))
        approach = REGISTRY.get(args.approach)
        if approach is None:
            print(f"Approach '{args.approach}' no disponible.", file=sys.stderr)
            return 2
        findings = approach(dossier, _select_guidelines(args.corpus))

    golden = [GoldenIssue.model_validate(x) for x in _load_json(args.golden)]

    if not args.adjudications:
        grounded = sum(1 for f in findings if f.is_grounded())
        n = len(findings)
        pct = (grounded / n * 100) if n else 0.0
        print(
            "Sin --adjudications no se pueden calcular recall/precision "
            "(requieren LLM-juez + revision, F2).\n"
            f"Solo grounding: {grounded}/{n} hallazgos anclados ({pct:.0f}%) sobre {len(golden)} golden."
        )
        return 0

    adjudications = [Adjudication.model_validate(x) for x in _load_json(args.adjudications)]
    run = compute_run_metrics(args.approach, findings, adjudications, golden)
    agg = aggregate([run])
    _emit(render_metrics_md([agg]), args.out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="interaction-review",
        description="Revisor de la capa de interaccion humano-IA (HAX-18 + PAIR).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pr = sub.add_parser("revisar", help="Genera un informe de hallazgos para un sistema.")
    pr.add_argument("--dossier", required=True, help="JSON con el Dossier del sistema.")
    pr.add_argument("--approach", default="b0", help="Approach a usar (def: b0).")
    pr.add_argument("--corpus", default="hax,pair", help="Corpus: hax, pair o ambos (def: hax,pair).")
    pr.add_argument("--out", default=None, help="Fichero de salida .md (def: stdout).")
    pr.set_defaults(func=cmd_revisar)

    pe = sub.add_parser("evaluar", help="Calcula metricas contra un golden set.")
    pe.add_argument("--golden", required=True, help="JSON con la lista de GoldenIssue.")
    pe.add_argument("--dossier", default=None, help="JSON del Dossier (si no se pasan --findings).")
    pe.add_argument("--findings", default=None, help="JSON con hallazgos ya generados.")
    pe.add_argument("--adjudications", default=None, help="JSON con adjudicaciones (LLM-juez + revision).")
    pe.add_argument("--approach", default="b0", help="Approach a usar si se generan hallazgos (def: b0).")
    pe.add_argument("--corpus", default="hax,pair", help="Corpus (def: hax,pair).")
    pe.add_argument("--out", default=None, help="Fichero de salida .md (def: stdout).")
    pe.set_defaults(func=cmd_evaluar)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
