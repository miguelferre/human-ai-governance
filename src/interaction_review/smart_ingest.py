"""Ingesta INTELIGENTE: un documento arbitrario (PDF, model card) -> plantilla prerrellena.

Complementa a `ingest.py` (que parsea NUESTRAS plantillas ya rellenas, sin API). Aqui el
problema es el inverso y es IRREDUCIBLE al codigo: leer documentacion heterogenea y mapear su
contenido a las preguntas de la plantilla. Eso lo hace el LLM (ADR-004: al modelo solo lo
irreducible). El reparto:
  - CODIGO (determinista): extraer el texto del PDF, localizar los huecos ✍️ de la plantilla,
    reconstruir el markdown con las respuestas.
  - LLM: responder cada pregunta con lo que consta en el documento (y SOLO eso).

La salida es una plantilla markdown en NUESTRO formato (respuestas tras ✍️), que un humano
revisa y luego `ingerir` convierte en Dossier. El modelo prerrellena; la persona valida.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from interaction_review import llm, prompts

_PEN = "✍"  # ✍ (con o sin selector de variacion): marca el hueco de respuesta.

# Plantillas del repo (se resuelven desde la raiz; overridable con --plantilla en el CLI).
_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"
TEMPLATE_FILES = {
    "ficha": "01_ficha_sistema__perfil_tecnico.md",
    "experiencia": "02_experiencia_uso__usuario_final.md",
    "inventario": "03_inventario_documentos.md",
}


def template_path(tipo: str) -> Path:
    try:
        return _TEMPLATE_DIR / TEMPLATE_FILES[tipo]
    except KeyError as e:
        raise ValueError(
            f"Tipo de plantilla desconocido: {tipo!r}. Usa uno de {sorted(TEMPLATE_FILES)}."
        ) from e


# --- Lectura del documento (determinista) ----------------------------------- #
def read_document(path: str | Path) -> str:
    """Texto plano de un documento. PDF via pypdf; .md/.txt tal cual."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No existe el documento: {p}")
    if p.suffix.lower() == ".pdf":
        return _read_pdf(p)
    return p.read_text(encoding="utf-8")


def _read_pdf(p: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:  # pragma: no cover
        raise ValueError("Leer PDF requiere el paquete 'pypdf' (ejecuta `uv sync`).") from e
    reader = PdfReader(str(p))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    if not text.strip():
        raise ValueError(
            f"No se extrajo texto de {p.name}. ¿Es un PDF escaneado (imagen)? El MVP no hace "
            "OCR; conviertelo a texto o rellena la plantilla a mano."
        )
    return text


# --- Huecos de la plantilla (determinista) ---------------------------------- #
@dataclass(frozen=True)
class TemplateSlot:
    index: int       # orden de aparicion del ✍️ (0-based)
    line_index: int  # linea del ✍️ en la plantilla
    section: str     # cabecera ## vigente
    question: str    # ultimo bullet en negrita (o "" si el hueco cuelga de la seccion)


def _clean_question(line: str) -> str:
    s = line.strip()
    if s.startswith("#"):
        return s.lstrip("#").strip()
    return s.lstrip("-*").strip().replace("**", "").strip()


def parse_template_slots(template_md: str) -> list[TemplateSlot]:
    """Localiza cada hueco ✍️ con su seccion y su pregunta (el bullet que lo precede)."""
    slots: list[TemplateSlot] = []
    section = ""
    question = ""
    for i, line in enumerate(template_md.splitlines()):
        s = line.strip()
        if s.startswith("##"):
            section = _clean_question(line)
            question = ""  # nueva seccion: se reinicia la pregunta vigente
            continue
        if _PEN in line:
            slots.append(
                TemplateSlot(index=len(slots), line_index=i, section=section, question=question)
            )
            continue
        if s.startswith(("- ", "* ")) and "**" in s:
            question = _clean_question(line)
    return slots


def _one_line(text: str) -> str:
    """Colapsa la respuesta a UNA linea de texto plano (robusto para extract_answers)."""
    return " ".join(text.split())


def fill_template(template_md: str, answers: dict[int, str]) -> str:
    """Reinserta las respuestas tras cada ✍️, preservando el marcador y la indentacion."""
    lines = template_md.splitlines()
    slot_no = 0
    for i, line in enumerate(lines):
        if _PEN in line:
            ans = answers.get(slot_no, "")
            if ans:
                lines[i] = f"{line.rstrip()} {_one_line(ans)}"
            slot_no += 1
    tail = "\n" if template_md.endswith("\n") else ""
    return "\n".join(lines) + tail


# --- Orquestacion (LLM) ----------------------------------------------------- #
def prefill_template(
    doc_text: str,
    template_md: str,
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Prerrellena la plantilla con las respuestas que el documento sustente. Una llamada al LLM."""
    slots = parse_template_slots(template_md)
    if not slots:
        return template_md
    payload = [
        {"slot": s.index, "section": s.section, "question": s.question or s.section}
        for s in slots
    ]
    out = llm.call_structured(
        model=model or llm.gen_model(),
        system=prompts.PREFILL_SYSTEM,
        user=prompts.prefill_user(doc_text, payload),
        tool=prompts.PREFILL_TOOL,
        temperature=temperature,
    )
    valid = {s.index for s in slots}
    answers: dict[int, str] = {}
    if isinstance(out, dict):
        for a in out.get("answers", []):
            if not isinstance(a, dict):
                continue
            slot, ans = a.get("slot"), a.get("answer", "")
            if isinstance(slot, int) and slot in valid and isinstance(ans, str) and ans.strip():
                answers[slot] = ans.strip()
    return fill_template(template_md, answers)


def prefill_document(
    doc_path: str | Path,
    tipo: str = "ficha",
    *,
    template_file: str | Path | None = None,
    model: str | None = None,
) -> str:
    """De un documento a la plantilla `tipo` prerrellena (texto markdown)."""
    doc_text = read_document(doc_path)
    tpl = Path(template_file) if template_file else template_path(tipo)
    template_md = tpl.read_text(encoding="utf-8")
    return prefill_template(doc_text, template_md, model=model)
