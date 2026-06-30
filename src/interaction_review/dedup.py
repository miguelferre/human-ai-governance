"""Deduplicado de hallazgos: el paso de PRODUCTO que faltaba.

El anti-patron persistente de P3 (y peor en p3n): el barrido por bloques emite el
MISMO problema varias veces, normalmente citando una guideline distinta cada vez
(p. ej. "onboarding sin reciclaje" aparecio 7 veces via HAX-G1, HAX-G12, PAIR-UN-2,
PAIR-MM-1, PAIR-EF-2, PAIR-DE-1...). ~60-100 hallazgos para ~15 problemas reales.
Un auditor humano no quiere leer el mismo problema cinco veces.

Este paso COLAPSA hallazgos casi-duplicados en uno representativo que UNE las
guidelines de todos sus miembros. La salida es "un hallazgo por problema, anotado
con todas las guidelines que incumple" -> mas accionable, no menos.

Principios (coherentes con el proyecto, ver ADR-004): es DETERMINISTA y vive en el
CODIGO, sin LLM. No mira el golden ni las adjudicaciones (en produccion no existen):
agrupa solo por el CONTENIDO del hallazgo. La similitud es lexica (no semantica
profunda) a proposito: reproducible, auditable y sin coste. La validez del umbral se
mide aparte (scripts/dedup_report.py) contra adjudicaciones que este paso nunca ve:
no debe fundir problemas reales distintos (pureza) ni bajar la cobertura (recall).

La agrupacion es por REPRESENTANTE (no enlace-simple): cada hallazgo se compara con
los representantes de los clusters ya abiertos y se une al mas parecido por encima del
umbral, o abre cluster nuevo. Evita el encadenamiento transitivo (A~B, B~C => A~C) que
fundiria de mas. El resultado es estable respecto al orden de entrada (el de la pasada).
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from interaction_review.schemas import Finding, Severity

# Umbral de similitud para considerar dos hallazgos el MISMO problema. Calibrado
# offline (scripts/dedup_report.py) sobre los runs P3/p3n de EII: el valor mas
# agresivo que mantiene la PUREZA a 0 en p3 (no funde golden distintos) y conserva
# la cobertura. Por debajo de 0.60 empiezan las conflaciones; ver docs/RESULTADOS.md.
DEFAULT_THRESHOLD: float = 0.60

# Para que el ratio de titulo (que capta el mismo titulo reescrito) AYUDE, exigimos
# ademas un minimo de solape de vocabulario real. Sin esta guarda, titulos con la
# misma PLANTILLA pero distinto problema ("Falta de comunicacion de X al clinico")
# se fundian: la calibracion lo confirmo (variante 'max' -> impureza disparada).
_SEQ_REQUIRES_JACCARD: float = 0.25

# Palabras vacias (es) que sobreviven al filtro de longitud y solo anaden ruido a la
# similitud lexica. Lista corta y conservadora: solo funcionales, ningun termino de
# dominio (modelo/sistema/medico... SI discriminan y se conservan).
_STOPWORDS: frozenset[str] = frozenset(
    """del las los con por para una uno que sin mas muy pero como sus este esta esto
    ese esa eso entre sobre cuando donde ante tras desde hacia hasta son han hay ser
    sea fue era cada the and for""".split()
)

_SEVERITY_RANK = {Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1}


def _strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _norm(s: str) -> str:
    """Normaliza texto para comparar: sin acentos, minusculas, espacios colapsados."""
    return re.sub(r"\s+", " ", _strip_accents(s).lower()).strip()


def _tokens(s: str) -> set[str]:
    """Bolsa de tokens de contenido: sin acentos, >=3 chars, sin stopwords."""
    words = re.findall(r"[a-z0-9]+", _strip_accents(s).lower())
    return {w for w in words if len(w) >= 3 and w not in _STOPWORDS}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / len(a | b)


def text_similarity(a: str, b: str) -> float:
    """Jaccard de tokens de contenido entre dos textos libres (0..1).

    Reutilizable fuera del dedup: el juez la usa para AMPLIAR los candidatos del
    golden por similitud de texto (no solo por id de guideline compartido), que es
    la deuda de medicion documentada en TESTPLAN (un hallazgo que cita la guideline
    'equivocada' se quedaba sin candidato y daba un falso fallo).
    """
    return _jaccard(_tokens(a), _tokens(b))


def _signature_tokens(f: Finding) -> set[str]:
    # Titulo + locus: lo que identifica el PROBLEMA. La evidencia y el rationale son
    # largos y ruidosos (inflarian falsos parecidos); el titulo lleva el tema.
    return _tokens(f"{f.title} {f.locus}")


def similarity(a: Finding, b: Finding) -> float:
    """Cuanto se parecen dos hallazgos como 'mismo problema' (0..1).

    Combina dos senales:
    - Jaccard de tokens de (titulo+locus): solapamiento de vocabulario del problema.
    - Ratio de secuencia del titulo normalizado: capta el mismo titulo reescrito, pero
      SOLO si ya hay un minimo de solape de vocabulario (_SEQ_REQUIRES_JACCARD); si no,
      titulos con la misma plantilla y distinto problema se fundirian (ver calibracion).
    NO exige compartir guideline: el duplicado tipico cita una guideline DISTINTA.
    """
    jac = _jaccard(_signature_tokens(a), _signature_tokens(b))
    if jac < _SEQ_REQUIRES_JACCARD:
        return jac
    seq = SequenceMatcher(None, _norm(a.title), _norm(b.title)).ratio()
    return max(jac, seq)


def _union_guidelines(members: list[Finding]) -> list[str]:
    """Union de guideline_ids preservando el orden de primera aparicion."""
    seen: dict[str, None] = {}
    for f in members:
        for gid in f.guideline_ids:
            seen.setdefault(gid, None)
    return list(seen)


def _representative(members: list[Finding]) -> Finding:
    """El miembro mas completo del cluster: anclado > severo > rico en texto > primero."""

    def richness(f: Finding) -> int:
        return len(f.evidence) + len(f.rationale) + len(f.recommendation)

    return max(
        members,
        key=lambda f: (
            f.is_grounded(),
            _SEVERITY_RANK.get(f.severity, 0),
            richness(f),
        ),
    )


def _merge(members: list[Finding]) -> Finding:
    """Funde un cluster en un hallazgo: el representante + guidelines unidas.

    `merged_count` es ACUMULATIVO (cuantos hallazgos crudos representa en total), no
    "cuantos se unieron en esta pasada": asi re-deduplicar una lista ya deduplicada
    preserva el contador (idempotencia) y fundir hallazgos ya fundidos suma bien.
    """
    if len(members) == 1:
        return members[0]  # solo: se conserva tal cual (incluido su merged_count).
    rep = _representative(members)
    severity = max(members, key=lambda f: _SEVERITY_RANK.get(f.severity, 0)).severity
    anti = rep.anti_pattern or next((f.anti_pattern for f in members if f.anti_pattern), None)
    return rep.model_copy(
        update={
            "guideline_ids": _union_guidelines(members),
            "severity": severity,
            "anti_pattern": anti,
            "merged_count": sum(f.merged_count for f in members),
        }
    )


def deduplicate(
    findings: list[Finding], threshold: float = DEFAULT_THRESHOLD
) -> list[Finding]:
    """Colapsa hallazgos casi-duplicados. Estable respecto al orden de entrada.

    Devuelve un hallazgo por cluster (representante con guidelines unidas y
    `merged_count`), en el orden en que se abrio cada cluster. Idempotente:
    deduplicate(deduplicate(x)) == deduplicate(x).
    """
    clusters: list[list[Finding]] = []
    reps: list[Finding] = []  # representante provisional (el primero de cada cluster)
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
    return [_merge(c) for c in clusters]
