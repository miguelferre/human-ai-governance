"""Esquemas de datos del revisor de la capa de interaccion humano-IA.

Estos modelos son el contrato comun que consumen TODOS los approaches (B0, B1,
B2, y mas adelante P3/A4), de modo que la comparacion entre ellos sea justa:
todos reciben el mismo `Dossier` y todos emiten `Finding`s con el mismo esquema.

Ver el plan v0 y docs/adr/ para el porque de cada decision.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------------------------------- #
# Entrada: el sistema bajo revision, normalizado a un "dossier".
# --------------------------------------------------------------------------- #
class SourceKind(str, Enum):
    """Procedencia de una fuente del dossier.

    La procedencia es de primera clase: un desajuste entre lo que el TECHNICIAN
    cree que hace el sistema y lo que el END_USER vive es, en si mismo, una
    senal de la capa de interaccion (ver plan, seccion 2).
    """

    DOCUMENT = "document"      # documentacion importada sobre el modelo/sistema
    TECHNICIAN = "technician"  # texto de un perfil tecnico (implementa/mantiene)
    END_USER = "end_user"      # texto de un usuario final (usa el sistema)
    OTHER = "other"


class Source(BaseModel):
    """Una pieza de informacion sobre el sistema, con su procedencia."""

    id: str = Field(..., description="Identificador estable, p.ej. 'doc-ficha' o 'user-medico-1'.")
    kind: SourceKind
    label: str = Field(..., description="Etiqueta legible de la fuente.")
    content: str = Field(..., description="Texto bruto o transcrito de la fuente.")


class Dossier(BaseModel):
    """Representacion canonica del sistema de IA y de su interaccion.

    Es la entrada normalizada que consumen todos los approaches. Se construye a
    partir de fuentes heterogeneas (documentos, texto de tecnicos y de usuarios)
    via `ingest`.
    """

    system_name: str
    domain: str = Field(..., description="Dominio, p.ej. 'cribado de derivacion AP->digestivo'.")
    summary: str = Field("", description="Resumen breve del sistema y su flujo de interaccion.")
    sources: list[Source] = Field(default_factory=list)

    @field_validator("sources")
    @classmethod
    def _at_least_one_source(cls, v: list[Source]) -> list[Source]:
        if not v:
            raise ValueError("El dossier necesita al menos una fuente.")
        return v


# --------------------------------------------------------------------------- #
# Guidelines (HAX-18 / PAIR) codificadas como datos enlazables.
# --------------------------------------------------------------------------- #
class GuidelineCorpus(str, Enum):
    HAX = "HAX"    # Microsoft, Amershi et al. 2019 (18 guidelines)
    PAIR = "PAIR"  # Google People + AI Guidebook


class Guideline(BaseModel):
    """Un item atomico y enlazable de un corpus de guidelines."""

    id: str = Field(..., description="Id estable, p.ej. 'HAX-G1' o 'PAIR-FC-2'.")
    corpus: GuidelineCorpus
    group: str = Field(..., description="Fase (HAX) o capitulo (PAIR) al que pertenece.")
    title: str
    description: str
    good_example: str = Field(..., description="Ejemplo de buen cumplimiento.")
    bad_example: str = Field(..., description="Ejemplo de incumplimiento / anti-patron.")
    anti_patterns: list[str] = Field(
        default_factory=list,
        description="Anti-patrones concretos asociados, para deteccion.",
    )


# --------------------------------------------------------------------------- #
# Salida: hallazgos. Mismo esquema para todos los approaches.
# --------------------------------------------------------------------------- #
class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Finding(BaseModel):
    """Un hallazgo sobre la capa de interaccion.

    El nucleo del proyecto: un hallazgo util esta ANCLADO en tres cosas
    (ver `is_grounded`). Un hallazgo sin anclaje es generico y, por la definicion
    de exito del plan, cuenta como fallo, no como acierto.
    """

    id: str
    title: str
    guideline_ids: list[str] = Field(
        default_factory=list,
        description="Guidelines concretas que respalda/incumple (ancla 1).",
    )
    locus: str = Field(
        "",
        description="Punto CONCRETO del sistema al que se refiere el hallazgo (ancla 2).",
    )
    evidence: str = Field(
        "",
        description="Cita o referencia textual de la entrada que lo sustenta (ancla 3).",
    )
    anti_pattern: str | None = Field(None, description="Anti-patron detectado, si aplica.")
    severity: Severity = Severity.MEDIUM
    rationale: str = Field("", description="Por que es un problema en ESTE sistema.")
    recommendation: str = Field("", description="Accion concreta recomendada.")
    merged_count: int = Field(
        1,
        ge=1,
        description="Cuantos hallazgos crudos consolida (1 = sin consolidar). Lo fija el "
        "paso de deduplicado; un valor >1 significa que varias pasadas describian el mismo "
        "problema (a menudo citando guidelines distintas) y se han unido en este.",
    )

    def is_grounded(self) -> bool:
        """True si el hallazgo tiene los tres anclajes (guideline + locus + evidencia).

        Es el criterio operativo de no-genericidad usado por `metrics`.
        """
        return bool(self.guideline_ids) and bool(self.locus.strip()) and bool(self.evidence.strip())


# --------------------------------------------------------------------------- #
# Golden set y adjudicacion (evaluacion).
# --------------------------------------------------------------------------- #
class GoldenIssue(BaseModel):
    """Un problema de interaccion conocido del caso golden (answer key).

    Material derivado de informacion privada del usuario: vive bajo data/golden/
    (gitignored). El sistema NO lo ve durante la ejecucion ciega.
    """

    id: str
    description: str
    guideline_ids: list[str] = Field(default_factory=list)
    locus: str = ""
    severity: Severity = Severity.MEDIUM


class AdjudicationLabel(str, Enum):
    """Etiqueta de un hallazgo reportado frente al golden set."""

    TP_MATCH = "tp_match"          # real y coincide con un GoldenIssue conocido
    TP_NEW = "tp_new"              # real pero NO estaba en el golden (descubrimiento)
    FP_GENERIC = "fp_generic"      # generico / no anclado: vale para cualquier sistema
    FP_INCORRECT = "fp_incorrect"  # concreto pero incorrecto


class Adjudication(BaseModel):
    """Veredicto sobre un `Finding`.

    Lo produce primero el LLM-juez y lo revisa/corrige el humano. `human_confirmed`
    permite distinguir el veredicto automatico del validado.
    """

    finding_id: str
    label: AdjudicationLabel
    matched_golden_id: str | None = Field(
        None, description="Id del GoldenIssue emparejado, si label == TP_MATCH."
    )
    judge_rationale: str = ""
    human_confirmed: bool = False
