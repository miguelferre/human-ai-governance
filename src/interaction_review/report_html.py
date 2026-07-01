"""Informe HTML autocontenido de la revision (un solo .html, CSS embebido, sin red).

Pensado para el comprador de gobernanza/calidad: serio, editorial, imprime a PDF.
Complementa el markdown de `report.py`; consume los mismos `Finding`. Todo el
contenido dinamico se escapa con html.escape (texto libre del dossier/hallazgos).
"""

from __future__ import annotations

import html

from interaction_review.schemas import Dossier, Finding, Severity

# --------------------------------------------------------------------------- #
# Estilo: documento de auditoria editorial. Papel calido + tinta + azul pizarra.
# Fuentes del sistema con aire editorial (sin dependencias de red). Print-friendly.
# --------------------------------------------------------------------------- #
_CSS = """
:root {
  --paper: #f7f5ef; --surface: #fffefb; --ink: #20232b; --ink-soft: #5c5f68;
  --accent: #274060; --accent-2: #3a5a80; --line: #e3ded2;
  --sev-high: #8f2d3b; --sev-medium: #9a6a1e; --sev-low: #3f6079;
  --ok: #356b52; --warn: #9a6a1e;
  --serif: "Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,"Times New Roman",serif;
  --sans: "Avenir Next","Avenir","Segoe UI",Tahoma,"Helvetica Neue",sans-serif;
  --mono: "Cascadia Code","SF Mono",ui-monospace,Consolas,"Liberation Mono",monospace;
}
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  margin: 0; background: var(--paper); color: var(--ink);
  font-family: var(--serif); font-size: 17px; line-height: 1.62;
}
.sheet { max-width: 860px; margin: 0 auto; padding: 0 32px 96px; }

/* Cabecera */
.masthead { padding: 56px 0 28px; border-bottom: 2px solid var(--ink); margin-bottom: 40px; }
.kicker {
  font-family: var(--mono); font-size: 12px; letter-spacing: .22em; text-transform: uppercase;
  color: var(--accent-2); margin: 0 0 18px;
}
.masthead h1 { font-size: 40px; line-height: 1.1; margin: 0 0 12px; font-weight: 600; letter-spacing: -.01em; }
.masthead .domain { font-size: 19px; color: var(--ink-soft); font-style: italic; margin: 0; }
.masthead .meta {
  margin-top: 22px; font-family: var(--sans); font-size: 13px; color: var(--ink-soft);
  display: flex; flex-wrap: wrap; gap: 6px 22px;
}
.masthead .meta b { color: var(--ink); font-weight: 600; }

/* Resumen: tira de cifras */
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--line);
  border: 1px solid var(--line); margin-bottom: 12px; }
.stat { background: var(--surface); padding: 16px 18px; }
.stat .n { font-size: 30px; font-weight: 600; letter-spacing: -.02em; }
.stat .l { font-family: var(--sans); font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
  color: var(--ink-soft); margin-top: 2px; }
.sev-bar { display: flex; height: 8px; border: 1px solid var(--line); overflow: hidden; margin-bottom: 46px; }
.sev-bar span { display: block; }
.sev-bar .s-high { background: var(--sev-high); }
.sev-bar .s-medium { background: var(--sev-medium); }
.sev-bar .s-low { background: var(--sev-low); }

section.findings > h2, section.crosswalk > h2 {
  font-family: var(--sans); font-size: 12px; letter-spacing: .18em; text-transform: uppercase;
  color: var(--accent); border-bottom: 1px solid var(--line); padding-bottom: 8px; margin: 0 0 8px;
}

/* Hallazgo */
.finding { display: grid; grid-template-columns: 46px 1fr; gap: 20px; padding: 26px 0;
  border-bottom: 1px solid var(--line); break-inside: avoid; }
.finding .idx { font-size: 28px; color: var(--accent); font-variant-numeric: tabular-nums;
  line-height: 1; padding-top: 4px; }
.finding.generic .idx { color: var(--warn); }
.f-head { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.f-head h3 { font-size: 21px; margin: 0; font-weight: 600; line-height: 1.28; flex: 1 1 320px; }
.pill { font-family: var(--sans); font-size: 10.5px; font-weight: 700; letter-spacing: .07em;
  text-transform: uppercase; padding: 3px 9px; border-radius: 2px; white-space: nowrap;
  display: inline-flex; align-items: center; gap: 6px; }
.pill::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: currentColor; opacity: .9; }
.pill.high { color: #fff; background: var(--sev-high); }
.pill.medium { color: #fff; background: var(--sev-medium); }
.pill.low { color: #fff; background: var(--sev-low); }
.tag { font-family: var(--sans); font-size: 11px; padding: 2px 8px; border-radius: 2px;
  border: 1px solid; }
.tag.ok { color: var(--ok); border-color: var(--ok); }
.tag.warn { color: var(--warn); border-color: var(--warn); }
.gids { font-family: var(--mono); font-size: 12.5px; color: var(--accent-2); margin: 0 0 14px; }
.gids .g { background: rgba(58,90,128,.09); padding: 1px 6px; border-radius: 3px; margin-right: 4px; }
dl.f-body { margin: 0; display: grid; grid-template-columns: 128px 1fr; gap: 7px 18px; }
dl.f-body dt { font-family: var(--sans); font-size: 11px; letter-spacing: .06em; text-transform: uppercase;
  color: var(--ink-soft); padding-top: 3px; }
dl.f-body dd { margin: 0; }
dl.f-body dd.evidence { font-style: italic; color: #33363f;
  border-left: 2px solid var(--line); padding-left: 12px; }
.merged { font-family: var(--sans); font-size: 11px; color: var(--ink-soft); margin-top: 10px; }

/* Crosswalk */
section.crosswalk { margin-top: 52px; break-inside: avoid; }
.cw-note { font-family: var(--sans); font-size: 13px; color: var(--ink-soft); margin: 10px 0 22px; }
.cw-fw { margin-bottom: 24px; }
.cw-fw h3 { font-size: 17px; margin: 0 0 10px; color: var(--accent); font-weight: 600; }
.cw-row { display: grid; grid-template-columns: 168px 1fr; gap: 6px 16px; padding: 7px 0;
  border-top: 1px solid var(--line); }
.cw-row .ref { font-family: var(--mono); font-size: 13px; font-weight: 600; }
.cw-row .g { font-family: var(--mono); font-size: 12px; color: var(--ink-soft); }

footer { margin-top: 40px; padding-top: 18px; border-top: 2px solid var(--ink);
  font-family: var(--sans); font-size: 11.5px; color: var(--ink-soft); }

/* Aparicion suave (solo pantalla) */
@media screen {
  .finding, .stat, .cw-fw { animation: rise .5s ease both; }
  .finding:nth-child(2) { animation-delay: .04s; } .finding:nth-child(3) { animation-delay: .08s; }
  .finding:nth-child(4) { animation-delay: .12s; } .finding:nth-child(5) { animation-delay: .16s; }
  @keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
}
@media print {
  body { background: #fff; font-size: 11pt; }
  .sheet { max-width: none; padding: 0; }
  .stats, .finding, .cw-fw, .sev-bar { break-inside: avoid; }
  a { color: inherit; text-decoration: none; }
}
"""

_SEV_LABEL = {Severity.HIGH: "Alta", Severity.MEDIUM: "Media", Severity.LOW: "Baja"}


def _esc(text: str) -> str:
    return html.escape(text or "")


def _row(dt: str, value: str, *, cls: str = "") -> str:
    dd = f'<dd class="{cls}">' if cls else "<dd>"
    return f"<dt>{dt}</dt>{dd}{_esc(value)}</dd>"


def _finding_html(f: Finding, idx: int) -> str:
    grounded = f.is_grounded()
    sev = f.severity.value
    parts: list[str] = []
    parts.append(f'<article class="finding{"" if grounded else " generic"}">')
    parts.append(f'<div class="idx">{idx:02d}</div>')
    parts.append('<div class="f-main">')

    parts.append('<div class="f-head">')
    parts.append(f"<h3>{_esc(f.title)}</h3>")
    parts.append(f'<span class="pill {sev}">{_SEV_LABEL.get(f.severity, sev)}</span>')
    if grounded:
        parts.append('<span class="tag ok">Anclado</span>')
    else:
        parts.append('<span class="tag warn">Sin anclar</span>')
    parts.append("</div>")

    if f.guideline_ids:
        chips = "".join(f'<span class="g">{_esc(g)}</span>' for g in f.guideline_ids)
        parts.append(f'<p class="gids">{chips}</p>')

    parts.append('<dl class="f-body">')
    parts.append(_row("Locus", f.locus or "(sin locus concreto)"))
    parts.append(_row("Evidencia", f.evidence or "(sin evidencia)", cls="evidence"))
    if f.anti_pattern:
        parts.append(_row("Anti-patrón", f.anti_pattern))
    if f.rationale:
        parts.append(_row("Por qué importa", f.rationale))
    if f.recommendation:
        parts.append(_row("Recomendación", f.recommendation))
    parts.append("</dl>")

    if f.merged_count > 1:
        parts.append(f'<p class="merged">Consolida {f.merged_count} hallazgos crudos.</p>')

    parts.append("</div></article>")
    return "".join(parts)


def _crosswalk_html(findings: list[Finding]) -> str:
    from interaction_review.regulatory import crosswalk, framework_names

    cw = crosswalk(findings)
    if not cw:
        return ""
    names = framework_names()
    parts: list[str] = ['<section class="crosswalk">']
    parts.append("<h2>Crosswalk normativo</h2>")
    parts.append(
        '<p class="cw-note">Requisitos que tocan los hallazgos, con la guideline que los ancla. '
        "Orientativo, <b>no dictamen legal</b> (ADR-008): la aplicabilidad depende del rol y de si "
        "el sistema es de alto riesgo.</p>"
    )
    for fw, items in cw.items():
        parts.append('<div class="cw-fw">')
        parts.append(f"<h3>{_esc(names.get(fw, fw))}</h3>")
        for ref, gids in items:
            parts.append(
                f'<div class="cw-row"><span class="ref">{_esc(ref)}</span>'
                f'<span class="g">{_esc(", ".join(gids))}</span></div>'
            )
        parts.append("</div>")
    parts.append("</section>")
    return "".join(parts)


def render_findings_html(
    dossier: Dossier,
    findings: list[Finding],
    approach: str,
    *,
    include_crosswalk: bool = False,
) -> str:
    """Informe HTML autocontenido. `include_crosswalk` anexa el mapeo normativo."""
    n = len(findings)
    grounded = sum(1 for f in findings if f.is_grounded())
    pct = round(grounded / n * 100) if n else 0
    raw = sum(f.merged_count for f in findings)
    sev_counts = {s: sum(1 for f in findings if f.severity is s) for s in Severity}

    doc: list[str] = []
    doc.append("<!doctype html><html lang='es'><head><meta charset='utf-8'>")
    doc.append("<meta name='viewport' content='width=device-width, initial-scale=1'>")
    doc.append(f"<title>Revisión — {_esc(dossier.system_name)}</title>")
    doc.append(f"<style>{_CSS}</style></head><body><main class='sheet'>")

    # Cabecera
    doc.append("<header class='masthead'>")
    doc.append("<p class='kicker'>Revisión de la capa de interacción humano–IA</p>")
    doc.append(f"<h1>{_esc(dossier.system_name)}</h1>")
    doc.append(f"<p class='domain'>{_esc(dossier.domain)}</p>")
    doc.append(
        f"<div class='meta'><span><b>Approach:</b> {_esc(approach)}</span>"
        f"<span><b>Fuentes:</b> {len(dossier.sources)}</span>"
        f"<span><b>Guías:</b> HAX-18 · PAIR</span></div>"
    )
    doc.append("</header>")

    # Resumen
    dedup_note = (
        f"{raw}→{n}" if raw > n else "—"
    )
    doc.append("<div class='stats'>")
    doc.append(f"<div class='stat'><div class='n'>{n}</div><div class='l'>Hallazgos</div></div>")
    doc.append(
        f"<div class='stat'><div class='n'>{pct}%</div><div class='l'>Anclados</div></div>"
    )
    doc.append(
        f"<div class='stat'><div class='n'>{sev_counts[Severity.HIGH]}</div>"
        f"<div class='l'>Severidad alta</div></div>"
    )
    doc.append(
        f"<div class='stat'><div class='n'>{dedup_note}</div><div class='l'>Consolidación</div></div>"
    )
    doc.append("</div>")

    # Barra de severidad proporcional
    if n:
        doc.append("<div class='sev-bar'>")
        for s, klass in ((Severity.HIGH, "s-high"), (Severity.MEDIUM, "s-medium"), (Severity.LOW, "s-low")):
            w = sev_counts[s] / n * 100
            if w:
                doc.append(f"<span class='{klass}' style='width:{w:.1f}%'></span>")
        doc.append("</div>")

    # Hallazgos
    doc.append("<section class='findings'><h2>Hallazgos</h2>")
    if findings:
        for i, f in enumerate(findings, 1):
            doc.append(_finding_html(f, i))
    else:
        doc.append("<p><em>Sin hallazgos: el sistema no presenta problemas de interacción detectables.</em></p>")
    doc.append("</section>")

    # Crosswalk normativo
    if include_crosswalk:
        doc.append(_crosswalk_html(findings))

    doc.append(
        "<footer>Generado por el revisor de la capa de interacción humano–IA · "
        "hallazgos anclados a HAX-18 (Microsoft) y PAIR (Google). "
        "El crosswalk normativo es orientativo, no dictamen legal.</footer>"
    )
    doc.append("</main></body></html>")
    return "".join(doc)
