"""Tests de la ingesta de plantillas -> Dossier (ingest). Parser determinista."""

import pytest

from interaction_review.ingest import extract_answers, ingest_templates
from interaction_review.schemas import SourceKind

_FICHA = """# Plantilla 01 - Ficha
**Cómo:** escribe debajo de cada pregunta.
> Recuerda: sin datos personales.
---
## 0. Identificación
- **Nombre del sistema:**
  ✍️ CribaTest
- **Dominio / para qué se usa:**
  ✍️ triaje de derivaciones a digestivo
- **Estado:** (idea / piloto / producción)
  ✍️
🎯 *Para qué:* situar el sistema.
---
## 1. Qué hace
- **¿Qué produce exactamente?**
  ✍️ una puntuación de riesgo
  en tres niveles (alto/medio/bajo)
"""

_EXPERIENCIA = """# Plantilla 02 - Usuario
**Cómo:** responde con tus palabras.
---
## 1. Tú y la herramienta
- **¿Cuál es tu rol?**
  ✍️ médico de familia
## 6. ¿Te fías?
- **¿Aceptas aunque no estés seguro?**
  ✍️ a veces sí, por rapidez
"""


# --- extract_answers -------------------------------------------------------- #
def test_extracts_answered_questions_only():
    ans = extract_answers(_FICHA)
    d = dict(ans)
    assert d["Nombre del sistema:"] == "CribaTest"
    assert d["Dominio / para qué se usa:"] == "triaje de derivaciones a digestivo"
    # "Estado" quedo sin responder (✍️ vacio) -> no aparece.
    assert not any("Estado" in q for q, _ in ans)


def test_answer_can_be_multiline():
    d = dict(extract_answers(_FICHA))
    assert d["¿Qué produce exactamente?"] == "una puntuación de riesgo\nen tres niveles (alto/medio/bajo)"


def test_ignores_header_blockquote_and_metainstructions():
    ans = extract_answers(_FICHA)
    joined = " ".join(q + " " + a for q, a in ans)
    assert "Recuerda" not in joined  # blockquote de cabecera
    assert "Para qué" not in joined  # 🎯 metainstruccion
    assert "escribe debajo" not in joined  # instruccion **Cómo:**


def test_empty_template_yields_no_answers():
    empty = "# T\n---\n## 1. X\n- **¿pregunta?**\n  ✍️\n"
    assert extract_answers(empty) == []


# --- ingest_templates ------------------------------------------------------- #
def test_builds_dossier_with_correct_kinds(tmp_path):
    f = tmp_path / "ficha.md"; f.write_text(_FICHA, encoding="utf-8")
    e = tmp_path / "user.md"; e.write_text(_EXPERIENCIA, encoding="utf-8")
    d = ingest_templates(ficha=[str(f)], experiencia=[str(e)])

    assert d.system_name == "CribaTest"
    assert d.domain == "triaje de derivaciones a digestivo"
    kinds = {s.kind for s in d.sources}
    assert SourceKind.TECHNICIAN in kinds
    assert SourceKind.END_USER in kinds
    tech = next(s for s in d.sources if s.kind is SourceKind.TECHNICIAN)
    assert "una puntuación de riesgo" in tech.content


def test_multiple_users_get_distinct_ids(tmp_path):
    e1 = tmp_path / "u1.md"; e1.write_text(_EXPERIENCIA, encoding="utf-8")
    e2 = tmp_path / "u2.md"; e2.write_text(_EXPERIENCIA, encoding="utf-8")
    f = tmp_path / "ficha.md"; f.write_text(_FICHA, encoding="utf-8")
    d = ingest_templates(ficha=[str(f)], experiencia=[str(e1), str(e2)])
    user_ids = sorted(s.id for s in d.sources if s.kind is SourceKind.END_USER)
    assert user_ids == ["experiencia-usuario-1", "experiencia-usuario-2"]


def test_inventory_extracts_checked_documents(tmp_path):
    inv = tmp_path / "inv.md"
    inv.write_text(
        "# Inv\n---\n## Documentos\n- [x] **Capturas de pantalla**\n- [ ] Model card\n- [x] Manual de usuario\n",
        encoding="utf-8",
    )
    f = tmp_path / "ficha.md"; f.write_text(_FICHA, encoding="utf-8")
    d = ingest_templates(ficha=[str(f)], inventario=str(inv))
    doc = next(s for s in d.sources if s.kind is SourceKind.DOCUMENT)
    assert "Capturas de pantalla" in doc.content
    assert "Manual de usuario" in doc.content
    assert "Model card" not in doc.content  # no marcado


def test_explicit_name_domain_override(tmp_path):
    f = tmp_path / "ficha.md"; f.write_text(_FICHA, encoding="utf-8")
    d = ingest_templates(ficha=[str(f)], system_name="Otro", domain="otro dominio")
    assert d.system_name == "Otro"
    assert d.domain == "otro dominio"


def test_raises_when_all_templates_empty(tmp_path):
    empty = tmp_path / "e.md"; empty.write_text("# T\n---\n- **¿x?**\n  ✍️\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ingest_templates(ficha=[str(empty)])
