"""Reporte de la ablacion del testimonio del usuario (ADR-007).

Dos modos:

  dist    OFFLINE, sin API. Dado uno o varios answer_key etiquetados con
          `revealed_by`, imprime la distribucion (user_only / tech_only / both)
          por caso y agregada. Es el TECHO del aporte del testimonio al recall:
          si casi no hay user_only, la voz no puede aportar mucho recall aunque
          quisiera. Resultado honesto por si solo.

  compare Necesita runs ya juzgados (los produce `comparar`, gasta API). Dado el
          golden etiquetado y dos runs -CON voz y SIN voz (dossier sin END_USER)-,
          imprime el recall por subconjunto en cada condicion y el delta en
          user_only, que es la pregunta de fondo: ¿cae el recall al quitar la voz?

Uso:
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
    # data/external/<caso>/answer_key.json -> <caso>
    return Path(path).parent.name or Path(path).stem


# --------------------------------------------------------------------------- #
# Modo dist: distribucion revealed_by (offline).
# --------------------------------------------------------------------------- #
def cmd_dist(args: argparse.Namespace) -> int:
    rows: list[tuple[str, dict[RevealedBy, int]]] = []
    omitidos: list[str] = []
    for path in args.goldens:
        try:
            golden = _golden(path)
        except FileNotFoundError:
            print(f"(aviso) no existe: {path}")
            continue
        dist = revealed_by_distribution(golden)
        # Un caso donde TODO es unknown no esta etiquetado -> no participa en la ablacion.
        # (Asi un glob sobre data/external/* se queda solo con los casos con testimonio.)
        etiquetados = sum(v for rb, v in dist.items() if rb is not RevealedBy.UNKNOWN)
        if etiquetados == 0:
            omitidos.append(_case_name(path))
            continue
        rows.append((_case_name(path), dist))

    if not rows:
        print("No se cargo ningun golden etiquetado con revealed_by.")
        return 1

    print("# Ablacion del testimonio - distribucion del golden (offline, ADR-007)\n")
    print("Cuantos GoldenIssue revela cada tipo de fuente. `user_only` es el techo del "
          "aporte del testimonio al recall.\n")
    header = "| caso | total | user_only | both | tech_only | unknown | %voz-dependiente |"
    print(header)
    print("|---|---|---|---|---|---|---|")

    tot = {rb: 0 for rb in RevealedBy}
    total_issues = 0
    for name, dist in rows:
        n = sum(dist.values())
        total_issues += n
        for rb in RevealedBy:
            tot[rb] += dist[rb]
        # "voz-dependiente" = user_only (solo la voz lo revela). Techo de recall del testimonio.
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
        f"\n> Lectura: {tot[RevealedBy.USER_ONLY]}/{total_issues} problemas "
        f"({pct_tot:.0f}%) solo los revela la voz del usuario; "
        f"{tot[RevealedBy.BOTH]} los revelan voz Y documentacion (ahi el testimonio "
        f"aporta grounding, no recall)."
    )
    if omitidos:
        print(
            f"\n> Omitidos {len(omitidos)} casos sin etiquetar (no participan en la ablacion): "
            f"{', '.join(sorted(omitidos))}."
        )
    return 0


# --------------------------------------------------------------------------- #
# Modo compare: recall por subconjunto con voz vs sin voz (necesita runs).
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
    """Media (y std) del recall por subconjunto sobre k runs. Devuelve {rb: (mean, std, n_golden)}."""
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
            f"No hay adjudicaciones para approach '{args.approach}' en uno de los runs. "
            "¿Se corrio `comparar` con --save sobre ambos dossiers (con voz y sin voz)?"
        )
        return 1

    print(f"# Ablacion del testimonio - recall por subconjunto ({args.approach}, ADR-007)\n")
    print("| revealed_by | n | recall CON voz | recall SIN voz | delta |")
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

    # El titular: el delta en user_only.
    if RevealedBy.USER_ONLY in voz:
        mv = voz[RevealedBy.USER_ONLY][0]
        ms = sin.get(RevealedBy.USER_ONLY, (0.0, 0.0, 0))[0]
        drop = mv - ms
        print(
            f"\n> **Titular:** en los problemas que solo revela la voz, el recall pasa de "
            f"{mv:.2f} (con voz) a {ms:.2f} (sin voz), delta {drop:+.2f}. "
            + (
                "El testimonio SI aporta recall."
                if drop >= 0.15
                else "El testimonio aporta poco recall (su valor esta en el grounding)."
            )
        )
    else:
        print("\n> No hay subconjunto user_only en este golden: nada que aislar aqui.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Reporte de la ablacion del testimonio (ADR-007).")
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("dist", help="Distribucion revealed_by del golden (offline, sin API).")
    pd.add_argument("goldens", nargs="+", help="Rutas a answer_key.json etiquetados.")
    pd.set_defaults(func=cmd_dist)

    pc = sub.add_parser("compare", help="Recall por subconjunto con voz vs sin voz (necesita runs).")
    pc.add_argument("--golden", required=True, help="answer_key.json etiquetado.")
    pc.add_argument("--voz", required=True, help="runs/*.json del dossier CON voz.")
    pc.add_argument("--sin-voz", required=True, dest="sin_voz", help="runs/*.json del dossier SIN voz.")
    pc.add_argument("--approach", default="p3", help="Approach a comparar (def: p3).")
    pc.set_defaults(func=cmd_compare)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
