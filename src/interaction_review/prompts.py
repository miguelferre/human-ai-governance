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
Si no puedes apoyar un hallazgo en evidencia del dossier, NO lo reportes.

SE EXHAUSTIVO: recorre TODAS las areas de la interaccion (presentacion del resultado, confianza e
incertidumbre, explicacion del porque, correccion/override, descarte y temporizacion de alertas, onboarding,
comportamiento ante datos insuficientes o fallo, supervision por subgrupos, cambios y controles, feedback) y
reporta CADA problema real y anclado que detectes; no te limites a unos pocos. Pero cada hallazgo DEBE pasar
la regla de oro: si no esta anclado, no va. Vale mas un hallazgo solido que diez genericos.
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


def generator_user(dossier: Dossier, guidelines: list[Guideline], few_shot: bool, extra: str = "") -> str:
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
    if extra:
        blocks += [extra, ""]
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
Eres un adjudicador IMPARCIAL. Para CADA hallazgo te damos los CANDIDATOS del golden, con los
mas probables PRIMERO (marcados con [comparte guideline]); el resto va despues por si el hallazgo
describe ese problema aunque cite otra guideline. Tu tarea: mirar si el hallazgo describe el
MISMO problema que alguno de SUS candidatos (mira tambien los no marcados, no solo los primeros).

Por hallazgo, EN ESTE ORDEN:
1) judge_rationale: razonamiento breve.
2) corresponde_a_candidato: si el hallazgo describe el MISMO problema que uno de SUS candidatos,
   pon su id EXACTO (uno de los que se listan para ESE hallazgo); si ninguno encaja, pon "ninguno".
3) es_real: SOLO importa si corresponde_a_candidato es "ninguno". true si aun asi el hallazgo es un
   problema real y especifico apoyado en el dossier (descubrimiento nuevo); false si es incorrecto o
   no sustentado. (Si hay candidato, deja es_real en true.)

No decides la etiqueta: la derivamos de tus respuestas. Devuelve TODO mediante report_adjudications,
una entrada por hallazgo."""


def judge_user(payload: list[dict], dossier: Dossier) -> str:
    """`payload`: lista de hallazgos, cada uno con sus 'candidates' preseleccionados."""
    blocks = ["DOSSIER (para verificar que la evidencia es real):", format_dossier(dossier), ""]
    blocks.append("HALLAZGOS Y SUS CANDIDATOS:")
    for f in payload:
        blocks.append(f"\n- HALLAZGO {f['id']}: {f.get('title')!r}")
        blocks.append(f"    locus: {f.get('locus')!r} | evidencia: {f.get('evidence')!r}")
        cands = f.get("candidates", [])
        if cands:
            blocks.append("    candidatos del golden (elige uno o 'ninguno'; [*]=comparte guideline):")
            for c in cands:
                mark = " [*]" if c.get("shares_guideline") else ""
                blocks.append(f"      * {c['id']}{mark}: {c['description']}")
        else:
            blocks.append("    candidatos: (ninguno) -> solo puede ser nuevo o incorrecto")
    blocks.append("\nClasifica cada hallazgo via report_adjudications.")
    return "\n".join(blocks)


JUDGE_TOOL = {
    "name": "report_adjudications",
    "description": "Para cada hallazgo, indica si corresponde a uno de SUS candidatos del golden.",
    "input_schema": {
        "type": "object",
        "properties": {
            "adjudications": {
                "type": "array",
                "items": {
                    "type": "object",
                    # La ETIQUETA se deriva en codigo (judge.py): corresponde_a_candidato valido
                    # -> tp_match; si "ninguno" -> tp_new/fp_incorrect segun es_real. Razonar primero.
                    "properties": {
                        "finding_id": {"type": "string"},
                        "judge_rationale": {"type": "string", "description": "Razonamiento; escribelo primero."},
                        "corresponde_a_candidato": {
                            "type": "string",
                            "description": "Id de uno de SUS candidatos, o 'ninguno'.",
                        },
                        "es_real": {"type": "boolean", "description": "Solo si 'ninguno': true=nuevo real, false=incorrecto."},
                    },
                    "required": ["finding_id", "judge_rationale", "corresponde_a_candidato", "es_real"],
                },
            }
        },
        "required": ["adjudications"],
    },
}


# --------------------------------------------------------------------------- #
# Consolidador semantico (dedup LLM): el residual que el dedup lexico no junta.
# --------------------------------------------------------------------------- #
SEMANTIC_DEDUP_SYSTEM = """\
Eres un consolidador de hallazgos de una auditoria de la capa de interaccion humano-IA.
Te dan una lista numerada de hallazgos (titulo + locus + guidelines citadas). Algunos describen
EL MISMO problema subyacente aunque esten redactados distinto o citen una guideline distinta
(p. ej. "onboarding sin reciclaje" dicho via HAX-G1, PAIR-MM-1, PAIR-EF-2...).

Tu tarea: agrupar SOLO los hallazgos que sean LITERALMENTE el mismo defecto descrito dos veces.

REGLA POR DEFECTO: NO agrupar. Solo agrupa un par si un auditor diria "esto es el MISMO problema
en el MISMO punto del sistema, redactado distinto", no solo "estan relacionados" o "son del mismo area".
- Mismo problema = mismo fenomeno en el mismo locus (mismo punto/pantalla/paso del sistema).
- NO agrupes dos problemas DISTINTOS del mismo area. Ejemplos de lo que va SEPARADO:
  * "no muestra la confianza por subgrupo" vs "no notifica las recalibraciones": ambos de monitorizacion,
    pero problemas DISTINTOS.
  * "no explica por que" (falta de explicacion) vs "no se puede anular" (falta de override): DISTINTOS.
- Ante la MENOR duda, deja los hallazgos SEPARADOS. Fundir dos problemas reales en uno es peor que
  dejar un duplicado: el duplicado solo molesta, la fusion OCULTA un problema.

Devuelve solo los grupos (de 2+ miembros) que cumplan esto, via consolidar. Lo que no menciones queda solo."""


def semantic_dedup_user(findings_payload: list[dict]) -> str:
    """`findings_payload`: lista de {id, title, locus, guideline_ids}."""
    lines = ["HALLAZGOS A CONSOLIDAR:"]
    for f in findings_payload:
        gl = ", ".join(f.get("guideline_ids", []))
        lines.append(f"- [{f['id']}] {f.get('title')!r} | locus: {f.get('locus')!r} | guidelines: {gl}")
    lines.append("\nAgrupa los que sean el MISMO problema via consolidar (solo grupos de 2+ miembros).")
    return "\n".join(lines)


SEMANTIC_DEDUP_TOOL = {
    "name": "consolidar",
    "description": "Agrupa los hallazgos que describen el mismo problema subyacente.",
    "input_schema": {
        "type": "object",
        "properties": {
            "groups": {
                "type": "array",
                "description": "Grupos de hallazgos que son el MISMO problema (solo grupos de 2+).",
                "items": {
                    "type": "object",
                    "properties": {
                        "finding_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Ids de los hallazgos del grupo (2 o mas).",
                        },
                        "reason": {"type": "string", "description": "Por que son el mismo problema."},
                    },
                    "required": ["finding_ids", "reason"],
                },
            }
        },
        "required": ["groups"],
    },
}


# --------------------------------------------------------------------------- #
# Agente A4: decision autonoma de cobertura (que investigar / cuando parar).
# --------------------------------------------------------------------------- #
AGENT_GAPS_SYSTEM = """\
Eres un revisor de la capa de interaccion que decide si su revision esta COMPLETA o le
falta cubrir areas. Tienes el catalogo de guidelines y los hallazgos que llevas hasta ahora.

Identifica que AREAS (guidelines del catalogo) NO has cubierto aun, o has cubierto de forma
debil, y que merezcan una pasada enfocada adicional sobre ESTE dossier. Decide:
- seguir: true si merece la pena otra pasada dirigida; false si ya has cubierto lo relevante.
- guideline_ids: ids EXACTOS del catalogo a investigar ahora (vacio si seguir=false).
- motivo: por que.
Se honesto: si los hallazgos ya cubren los problemas reales del dossier, para (seguir=false).
Devuelve via decidir_cobertura."""


def agent_gaps_user(guidelines, findings_payload: list[dict]) -> str:
    gl = "\n".join(f"- {g.id}: {g.title}" for g in guidelines)
    cubiertas = sorted({gid for f in findings_payload for gid in f.get("guideline_ids", [])})
    fl = "\n".join(f"- {f.get('title')!r} [{', '.join(f.get('guideline_ids', []))}]" for f in findings_payload)
    return "\n".join(
        [
            "CATALOGO DE GUIDELINES:",
            gl,
            "",
            f"GUIDELINES YA TOCADAS por los hallazgos: {', '.join(cubiertas) or '(ninguna)'}",
            "",
            "HALLAZGOS HASTA AHORA:",
            fl or "(ninguno)",
            "",
            "Decide si seguir investigando y que areas, via decidir_cobertura.",
        ]
    )


AGENT_GAPS_TOOL = {
    "name": "decidir_cobertura",
    "description": "Decide si la revision necesita otra pasada y sobre que guidelines.",
    "input_schema": {
        "type": "object",
        "properties": {
            "motivo": {"type": "string", "description": "Razonamiento; escribelo primero."},
            "guideline_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ids del catalogo a investigar ahora (vacio si seguir=false).",
            },
            "seguir": {"type": "boolean", "description": "true si merece otra pasada dirigida."},
        },
        "required": ["motivo", "guideline_ids", "seguir"],
    },
}
