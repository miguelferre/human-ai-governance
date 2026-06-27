"""Construccion de prompts y esquemas de tool-use (funciones puras y testeables).

Separa la logica de prompting de la llamada al LLM (`llm.py`) para poder testear
que el prompt contiene lo que debe sin gastar API.
"""

from __future__ import annotations

from interaction_review.schemas import Dossier, GoldenIssue, Guideline


# --------------------------------------------------------------------------- #
# Formateo de entrada compartido por todos los approaches con LLM.
# --------------------------------------------------------------------------- #
def format_guidelines(guidelines: list[Guideline]) -> str:
    lines = []
    for g in guidelines:
        ap = f" | anti-patrones: {'; '.join(g.anti_patterns)}" if g.anti_patterns else ""
        lines.append(f"- {g.id} [{g.corpus.value}/{g.group}] {g.title}: {g.description}{ap}")
    return "\n".join(lines)


def format_dossier(dossier: Dossier) -> str:
    parts = [
        f"NOMBRE: {dossier.system_name}",
        f"DOMINIO: {dossier.domain}",
        f"RESUMEN: {dossier.summary}",
        "FUENTES:",
    ]
    for s in dossier.sources:
        parts.append(f"  [{s.kind.value}] {s.label} (id={s.id}):\n    {s.content}")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Generador de hallazgos (B1 / B2).
# --------------------------------------------------------------------------- #
GENERATOR_SYSTEM = """\
Eres un auditor experto en la CAPA DE INTERACCION humano-IA (no en la capa tecnica del modelo).
Tu trabajo: dada la descripcion de un sistema de IA y de como interactua con su usuario,
detectar problemas de interaccion atados a guidelines reconocidas (HAX-18 de Microsoft y PAIR de Google).

REGLA DE ORO (no negociable): cada hallazgo DEBE estar ANCLADO en tres cosas:
1) guideline_ids: al menos un id EXACTO del catalogo que se te da (p. ej. "HAX-G9", "PAIR-ET-2"). No inventes ids.
2) locus: un punto CONCRETO de ESTE sistema (no generico). Que parte de la interaccion descrita.
3) evidence: una cita literal o parafrasis MUY cercana tomada del dossier (resumen o fuentes).

Ademas: rationale (por que es un problema EN ESTE sistema) y recommendation (accion concreta).

PROHIBIDO: recomendaciones genericas que valdrian para cualquier sistema de IA
("muestra la incertidumbre", "evita el sesgo", "mejora la explicabilidad") sin anclarlas en el dossier.
Si no puedes apoyar un hallazgo en evidencia del dossier, NO lo reportes. Mejor pocos y solidos que muchos y vagos.
Devuelve TODO mediante la herramienta report_findings."""

_FEWSHOT = """\
EJEMPLO de lo que SI y lo que NO cuenta (de otro sistema distinto, solo para ilustrar el estandar):

BIEN (anclado) -> {
  "title": "El resumen no indica su fiabilidad",
  "guideline_ids": ["HAX-G2", "PAIR-ET-2"],
  "locus": "La tarjeta de resumen que el agente ve al abrir el caso",
  "evidence": "'el resumen aparece como texto plano, sin ninguna marca de fiabilidad' (fuente tech-1)",
  "rationale": "Sin senal de fiabilidad el agente no sabe cuando desconfiar y tendera a aceptarlo igual.",
  "recommendation": "Anadir un indicador de fiabilidad por resumen y degradar visualmente los de baja confianza.",
  "severity": "high"
}

MAL (generico, NO reportar asi) -> "Mostrar la incertidumbre del modelo."
  Motivo: no cita locus concreto ni evidencia del dossier; valdria para cualquier IA.
"""


def generator_user(dossier: Dossier, guidelines: list[Guideline], few_shot: bool) -> str:
    blocks = [
        "CATALOGO DE GUIDELINES (usa solo estos ids):",
        format_guidelines(guidelines),
        "",
        "DOSSIER DEL SISTEMA A REVISAR:",
        format_dossier(dossier),
        "",
    ]
    if few_shot:
        blocks += [_FEWSHOT, ""]
    blocks.append(
        "Revisa la capa de interaccion de ESTE sistema y reporta los hallazgos anclados via report_findings."
    )
    return "\n".join(blocks)


FINDINGS_TOOL = {
    "name": "report_findings",
    "description": "Reporta los hallazgos de la revision de la capa de interaccion.",
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "guideline_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Ids exactos del catalogo (HAX-Gn / PAIR-XX-n).",
                        },
                        "locus": {"type": "string", "description": "Punto concreto de ESTE sistema."},
                        "evidence": {"type": "string", "description": "Cita/parafrasis del dossier."},
                        "anti_pattern": {"type": "string"},
                        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                        "rationale": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": [
                        "title",
                        "guideline_ids",
                        "locus",
                        "evidence",
                        "severity",
                        "rationale",
                        "recommendation",
                    ],
                },
            }
        },
        "required": ["findings"],
    },
}


# --------------------------------------------------------------------------- #
# Juez / adjudicador (modelo y prompt distintos del generador: ADR-002).
# --------------------------------------------------------------------------- #
JUDGE_SYSTEM = """\
Eres un adjudicador IMPARCIAL. Recibes hallazgos de una revision de la capa de interaccion de un sistema,
junto con (a) el dossier del sistema y (b) un golden set de problemas conocidos. Clasifica CADA hallazgo:

- "tp_match": describe un problema REAL del sistema y se corresponde con uno del golden. Indica matched_golden_id.
- "tp_new": real y especifico de ESTE sistema (apoyado en el dossier), pero NO esta en el golden.
- "fp_generic": generico o no anclado; valdria para cualquier sistema, o no se apoya en evidencia del dossier.
- "fp_incorrect": especifico pero incorrecto o no sustentado por el dossier.

Se ESTRICTO: si un hallazgo solo repite una guideline sin locus concreto y sin evidencia del dossier, es fp_generic.
Un mismo problema del golden puede ser emparejado por varios hallazgos (cada uno tp_match con el mismo id).
Devuelve TODO mediante la herramienta report_adjudications, una entrada por hallazgo."""


def judge_user(findings_payload: list[dict], golden: list[GoldenIssue], dossier: Dossier) -> str:
    golden_lines = [
        f"- {g.id}: {g.description} [guidelines: {', '.join(g.guideline_ids)}]" for g in golden
    ]
    finding_lines = []
    for f in findings_payload:
        finding_lines.append(
            f"- id={f['id']} | guidelines={f.get('guideline_ids')} | locus={f.get('locus')!r} | "
            f"evidence={f.get('evidence')!r} | titulo={f.get('title')!r}"
        )
    return "\n".join(
        [
            "DOSSIER (para verificar que la evidencia es real):",
            format_dossier(dossier),
            "",
            "GOLDEN SET (problemas conocidos):",
            "\n".join(golden_lines),
            "",
            "HALLAZGOS A CLASIFICAR:",
            "\n".join(finding_lines),
            "",
            "Clasifica cada hallazgo via report_adjudications.",
        ]
    )


JUDGE_TOOL = {
    "name": "report_adjudications",
    "description": "Clasifica cada hallazgo frente al golden set.",
    "input_schema": {
        "type": "object",
        "properties": {
            "adjudications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "finding_id": {"type": "string"},
                        "label": {
                            "type": "string",
                            "enum": ["tp_match", "tp_new", "fp_generic", "fp_incorrect"],
                        },
                        "matched_golden_id": {"type": "string"},
                        "judge_rationale": {"type": "string"},
                    },
                    "required": ["finding_id", "label", "judge_rationale"],
                },
            }
        },
        "required": ["adjudications"],
    },
}
