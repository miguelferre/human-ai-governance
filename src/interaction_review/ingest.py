"""Ingesta de las plantillas rellenas -> Dossier (determinista, offline).

Ataca el cuello de botella del caso de uso real: que construir la entrada no
cueste lo mismo que auditar a mano. El cliente rellena plantillas markdown
amigables (templates/01 tecnico, 02 usuario, 03 inventario) y esto las convierte
en el `Dossier` canonico que consumen los approaches, sin edicion manual de JSON.

Es un parser del formato CONTROLADO de nuestras plantillas (preguntas en negrita o
cabeceras `##`, respuesta tras el marcador ✍️), no un lector de documentos
arbitrarios: ingerir PDFs/model cards heterogeneos de forma inteligente necesita
el LLM y vive en otro sitio. Aqui, cero API.
"""

from __future__ import annotations

from pathlib import Path

from interaction_review.schemas import Dossier, Source, SourceKind

_PEN = "✍"  # ✍ (con o sin variation selector) = espacio para la respuesta.


def _is_structural(line: str) -> bool:
    """True si la linea corta una respuesta (nueva pregunta/seccion/instruccion)."""
    s = line.strip()
    if not s:
        return False  # las lineas en blanco NO cortan (respuestas multi-parrafo)
    return (
        s.startswith(("- ", "* ", "#", "---", ">", "**"))
        or s.startswith("\U0001f3af")  # 🎯 metainstruccion "Para que"
        or _PEN in s
    )


def _prompt_text(line: str) -> str:
    """Extrae el texto de una pregunta (bullet en negrita) o cabecera."""
    s = line.strip()
    if s.startswith("#"):
        return s.lstrip("#").strip()
    s = s.lstrip("-*").strip()
    return s.replace("**", "").strip()


def extract_answers(md: str) -> list[tuple[str, str]]:
    """(pregunta, respuesta) por cada ✍️ con respuesta no vacia, en orden.

    La respuesta es el texto tras el marcador ✍️ (resto de linea + lineas
    siguientes) hasta el proximo elemento estructural. Ignora la cabecera de
    instrucciones (todo lo anterior al primer separador `---`).
    """
    lines = md.splitlines()
    # Saltar la cabecera de la plantilla (hasta el primer '---').
    start = 0
    for i, ln in enumerate(lines):
        if ln.strip() == "---":
            start = i + 1
            break

    out: list[tuple[str, str]] = []
    last_prompt = ""
    i = start
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("#") or (s.startswith(("- ", "* ")) and _PEN not in s):
            last_prompt = _prompt_text(line)
            i += 1
            continue
        if _PEN in line:
            # Respuesta: resto de la linea tras el ✍️, mas lineas siguientes.
            # El marcador es ✍ (U+270D) + selector de variacion U+FE0F: lo quitamos.
            rest = line.split(_PEN, 1)[1].replace("️", "").strip()
            buf = [rest] if rest else []
            j = i + 1
            while j < len(lines) and not _is_structural(lines[j]):
                buf.append(lines[j].strip())  # las lineas de continuacion van indentadas
                j += 1
            answer = "\n".join(buf).strip()
            if answer:
                out.append((last_prompt, answer))
            i = j
            continue
        i += 1
    return out


def _format_source(answers: list[tuple[str, str]]) -> str:
    """Texto de la Source: cada pregunta respondida con su respuesta."""
    blocks = [f"**{q}**\n{a}" if q else a for q, a in answers]
    return "\n\n".join(blocks)


def _find(answers: list[tuple[str, str]], needle: str) -> str | None:
    needle = needle.lower()
    for q, a in answers:
        if needle in q.lower():
            return a.splitlines()[0].strip() or None
    return None


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def ingest_templates(
    *,
    ficha: list[str] | None = None,
    experiencia: list[str] | None = None,
    inventario: str | None = None,
    system_name: str | None = None,
    domain: str | None = None,
    summary: str = "",
) -> Dossier:
    """Construye un Dossier desde plantillas rellenas.

    `ficha`/`experiencia` aceptan varias rutas (varios tecnicos / usuarios). El
    nombre y el dominio se toman de la primera ficha si no se pasan explicitos.
    Lanza ValueError si no hay ninguna fuente con contenido.
    """
    ficha = ficha or []
    experiencia = experiencia or []
    sources: list[Source] = []

    for idx, path in enumerate(ficha, 1):
        answers = extract_answers(_read(path))
        if not answers:
            continue
        suffix = f"-{idx}" if len(ficha) > 1 else ""
        sources.append(
            Source(
                id=f"ficha-tecnica{suffix}",
                kind=SourceKind.TECHNICIAN,
                label="Ficha del sistema (perfil técnico)",
                content=_format_source(answers),
            )
        )
        if system_name is None:
            system_name = _find(answers, "nombre del sistema")
        if domain is None:
            domain = _find(answers, "dominio")

    for idx, path in enumerate(experiencia, 1):
        answers = extract_answers(_read(path))
        if not answers:
            continue
        suffix = f"-{idx}" if len(experiencia) > 1 else ""
        sources.append(
            Source(
                id=f"experiencia-usuario{suffix}",
                kind=SourceKind.END_USER,
                label="Experiencia de uso (usuario final)",
                content=_format_source(answers),
            )
        )

    if inventario:
        answers = extract_answers(_read(inventario))
        marcados = _checked_documents(_read(inventario))
        content = _format_source(answers)
        if marcados:
            content = ("Documentos disponibles:\n" + "\n".join(f"- {m}" for m in marcados)
                       + (("\n\n" + content) if content else ""))
        if content:
            sources.append(
                Source(
                    id="inventario-documentos",
                    kind=SourceKind.DOCUMENT,
                    label="Inventario de documentos aportados",
                    content=content,
                )
            )

    if not sources:
        raise ValueError(
            "Ninguna plantilla tenia respuestas. ¿Se rellenaron los espacios ✍️?"
        )

    return Dossier(
        system_name=system_name or "(sistema sin nombre)",
        domain=domain or "(dominio no especificado)",
        summary=summary,
        sources=sources,
    )


def _checked_documents(md: str) -> list[str]:
    """Documentos marcados con [x] en la plantilla de inventario."""
    out: list[str] = []
    for ln in md.splitlines():
        s = ln.strip()
        if s.lower().startswith(("- [x]", "* [x]")):
            text = s[5:].strip().replace("**", "")
            if text:
                out.append(text)
    return out
