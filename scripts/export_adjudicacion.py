"""Generates a human adjudication sheet from a saved run.

For a run (run index), lists the B1 and B2 findings with the verdict proposed by
the LLM judge and a slot for the human verdict, plus the B0 findings the judge
marked as "real" (leniency control). The human reviews and corrects; whatever they
do not touch is taken as validated.

Usage:  uv run python scripts/export_adjudicacion.py [runs/eii_k3.json] [run_idx] [output.md]
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
    L.append(f"# Adjudication sheet - EII case (run #{RUN_IDX})")
    L.append("")
    L.append("For each finding, the JUDGE already proposed a verdict. Mark **OK** if you "
             "agree or **correct** it. Reply in the chat with the corrections only "
             "(e.g. \"b2-003 -> fp_incorrect\" or \"b1-004 matches GI-09, not GI-07\"); "
             "whatever you do not touch is taken as validated.")
    L.append("")
    L.append("**Labels:** `tp_match` (real and = a golden) · `tp_new` (real but NOT in "
             "the golden) · `fp_generic` (generic/not anchored) · `fp_incorrect` (concrete "
             "but false or unsupported).")
    L.append("")

    def block(name: str, only_labels=None) -> None:
        det = data["runs"][name][RUN_IDX]
        adj = {a["finding_id"]: a for a in det["adjudications"]}
        items = det["findings"]
        if only_labels:
            items = [f for f in items if adj.get(f["id"], {}).get("label") in only_labels]
        L.append(f"## {name.upper()} - {len(items)} findings to review")
        if not items:
            L.append("_(none)_\n")
            return
        for f in items:
            a = adj.get(f["id"], {})
            lab = a.get("label", "?")
            mg = a.get("matched_golden_id") or ""
            gd = f"  ->  **{mg}** ({gdesc.get(mg, '?')})" if mg else ""
            L.append(f"### {f['id']} · {f['title']}")
            L.append(f"- cited guideline(s): {', '.join(f['guideline_ids']) or '-'}")
            L.append(f"- locus: {f['locus'] or '-'}")
            L.append(f"- evidence: {f['evidence'] or '-'}")
            L.append(f"- **JUDGE verdict:** `{lab}`{gd}")
            if a.get("judge_rationale"):
                L.append(f"  - rationale: {a['judge_rationale']}")
            L.append("- **YOUR VERDICT:** ( ) OK   ( ) correct -> ______________")
            L.append("")

    # Golden and its status in this run (to review the 'missed' ones)
    matched_here: set[str] = set()
    for name in ("b1", "b2"):
        for a in data["runs"][name][RUN_IDX]["adjudications"]:
            if a["label"] == "tp_match" and a.get("matched_golden_id"):
                matched_here.add(a["matched_golden_id"])
    L.append("## Golden: status in THIS run (are the 'missed' ones really missed?)")
    for g in golden:
        mark = "DETECTED" if g["id"] in matched_here else "-  MISSED"
        L.append(f"- [{mark}] {g['id']}: {g['description'][:75]}")
    L.append("")

    block("b1")
    block("b2")
    L.append("---")
    L.append("## B0 - judge leniency control (only those it called `tp_new`)")
    L.append("_B0 are checklist items with EMPTY locus/evidence: they should all be "
             "`fp_generic`. If the judge marked any as `tp_new`, do you agree or is it generic?_")
    L.append("")
    block("b0", only_labels={"tp_new"})

    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT).write_text("\n".join(L), encoding="utf-8")
    print(f"Written: {OUT}  ({len(L)} lines)")


if __name__ == "__main__":
    main()
