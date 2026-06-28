"""Genera una hoja de adjudicacion humana a partir de una corrida guardada.

Para una corrida (indice de run), lista los hallazgos de B1 y B2 con el veredicto
propuesto por el LLM-juez y un hueco para el veredicto humano, mas los hallazgos
de B0 que el juez marco como "reales" (control de leniencia). El humano revisa y
corrige; lo que no toque se da por validado.

Uso:  uv run python scripts/export_adjudicacion.py [runs/eii_k3.json] [run_idx] [salida.md]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RUNS = sys.argv[1] if len(sys.argv) > 1 else "runs/eii_k3.json"
RUN_IDX = int(sys.argv[2]) if len(sys.argv) > 2 else 0
OUT = sys.argv[3] if len(sys.argv) > 3 else "data/golden/caso-EII/adjudicacion_corrida0.md"
GOLDEN = "data/golden/caso-EII/answer_key.json"


def main() -> None:
    data = json.loads(Path(RUNS).read_text(encoding="utf-8"))
    golden = json.loads(Path(GOLDEN).read_text(encoding="utf-8"))
    gdesc = {g["id"]: g["description"] for g in golden}

    L: list[str] = []
    L.append(f"# Hoja de adjudicación — caso EII (corrida #{RUN_IDX})")
    L.append("")
    L.append("Para cada hallazgo, el JUEZ ya propuso un veredicto. Marca **OK** si estás de "
             "acuerdo o **corrige**. Responde en el chat solo con las correcciones "
             "(p. ej. «b2-003 → fp_incorrect» o «b1-004 empareja con GI-09, no GI-07»); "
             "lo que no toques se da por validado.")
    L.append("")
    L.append("**Etiquetas:** `tp_match` (real y = a un golden) · `tp_new` (real pero NO en "
             "el golden) · `fp_generic` (genérico/no anclado) · `fp_incorrect` (concreto "
             "pero falso o no sustentado).")
    L.append("")

    def block(name: str, only_labels=None) -> None:
        det = data["runs"][name][RUN_IDX]
        adj = {a["finding_id"]: a for a in det["adjudications"]}
        items = det["findings"]
        if only_labels:
            items = [f for f in items if adj.get(f["id"], {}).get("label") in only_labels]
        L.append(f"## {name.upper()} — {len(items)} hallazgos a revisar")
        if not items:
            L.append("_(ninguno)_\n")
            return
        for f in items:
            a = adj.get(f["id"], {})
            lab = a.get("label", "?")
            mg = a.get("matched_golden_id") or ""
            gd = f"  →  **{mg}** ({gdesc.get(mg, '?')})" if mg else ""
            L.append(f"### {f['id']} · {f['title']}")
            L.append(f"- guideline(s) citada(s): {', '.join(f['guideline_ids']) or '—'}")
            L.append(f"- locus: {f['locus'] or '—'}")
            L.append(f"- evidencia: {f['evidence'] or '—'}")
            L.append(f"- **veredicto JUEZ:** `{lab}`{gd}")
            if a.get("judge_rationale"):
                L.append(f"  - razón: {a['judge_rationale']}")
            L.append("- **TU VEREDICTO:** ( ) OK   ( ) corregir → ______________")
            L.append("")

    # Golden y su estado en esta corrida (para revisar los 'perdidos')
    matched_here: set[str] = set()
    for name in ("b1", "b2"):
        for a in data["runs"][name][RUN_IDX]["adjudications"]:
            if a["label"] == "tp_match" and a.get("matched_golden_id"):
                matched_here.add(a["matched_golden_id"])
    L.append("## Golden: estado en ESTA corrida (¿los 'perdidos' lo están de verdad?)")
    for g in golden:
        mark = "DETECTADO" if g["id"] in matched_here else "—  PERDIDO"
        L.append(f"- [{mark}] {g['id']}: {g['description'][:75]}")
    L.append("")

    block("b1")
    block("b2")
    L.append("---")
    L.append("## B0 — control de leniencia del juez (solo los que llamó `tp_new`)")
    L.append("_B0 son ítems de checklist con locus/evidencia VACÍOS: deberían ser todos "
             "`fp_generic`. Si el juez marcó alguno `tp_new`, ¿le das la razón o es genérico?_")
    L.append("")
    block("b0", only_labels={"tp_new"})

    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT).write_text("\n".join(L), encoding="utf-8")
    print(f"Escrito: {OUT}  ({len(L)} líneas)")


if __name__ == "__main__":
    main()
