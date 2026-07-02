"""Tests de la ingesta inteligente (documento -> plantilla prerrellena).

Lo determinista (parseo de huecos, reinsercion, cierre del circulo con extract_answers)
se prueba a fondo; la unica llamada al LLM va monkeypatcheada, sin API.
"""

import pytest

from interaction_review import llm, smart_ingest
from interaction_review.ingest import extract_answers

_TEMPLATE = """# Plantilla 01 - Ficha
**Cómo:** rellena debajo.
---
## 0. Identificación
- **Nombre del sistema:**
  ✍️
- **Dominio / para qué se usa:**
  ✍️
🎯 *Para qué:* situar.
---
## 3. Cómo se presenta el resultado
- **¿Dónde aparece?**
  ✍️
## Lo que tú ya sospechas (opcional)
✍️
"""


# --- parseo de huecos ------------------------------------------------------- #
def test_parse_slots_captures_question_and_section():
    slots = smart_ingest.parse_template_slots(_TEMPLATE)
    assert len(slots) == 4
    assert slots[0].section.startswith("0.")
    assert slots[0].question == "Nombre del sistema:"
    assert slots[2].question == "¿Dónde aparece?"
    # El ultimo hueco no tiene bullet: su pregunta queda vacia (cae a la seccion).
    assert slots[3].question == ""
    assert "sospechas" in slots[3].section.lower()


# --- reinsercion ------------------------------------------------------------ #
def test_fill_template_preserves_marker_and_leaves_blanks():
    slots = smart_ingest.parse_template_slots(_TEMPLATE)
    filled = smart_ingest.fill_template(_TEMPLATE, {0: "CribaTest", 1: "triaje a digestivo"})
    assert "✍️ CribaTest" in filled
    assert "✍️ triaje a digestivo" in filled
    # El numero de marcadores no cambia; los no respondidos quedan como hueco vacio.
    assert filled.count("✍") == len(slots)


def test_fill_collapses_multiline_answer():
    filled = smart_ingest.fill_template(_TEMPLATE, {0: "linea1\n  linea2\n\nlinea3"})
    assert "✍️ linea1 linea2 linea3" in filled


# --- cierre del circulo: prerrelleno -> extract_answers --------------------- #
def test_prefill_roundtrips_through_extract_answers(monkeypatch):
    monkeypatch.setattr(llm, "call_structured", lambda **kw: {"answers": [
        {"slot": 0, "answer": "CribaTest"},
        {"slot": 1, "answer": "triaje de derivaciones a digestivo"},
        {"slot": 2, "answer": ""},  # vacio: no consta -> no debe rellenar
    ]})
    filled = smart_ingest.prefill_template("doc...", _TEMPLATE)
    d = dict(extract_answers(filled))
    assert d["Nombre del sistema:"] == "CribaTest"
    assert d["Dominio / para qué se usa:"] == "triaje de derivaciones a digestivo"
    assert not any("Dónde aparece" in q for q in d)  # el slot vacio no reaparece


def test_prefill_ignores_invalid_slots(monkeypatch):
    monkeypatch.setattr(llm, "call_structured", lambda **kw: {"answers": [
        {"slot": 99, "answer": "fuera de rango"},
        {"slot": "x", "answer": "tipo malo"},
        {"slot": 0, "answer": "CribaTest"},
    ]})
    filled = smart_ingest.prefill_template("doc...", _TEMPLATE)
    assert "✍️ CribaTest" in filled
    assert "fuera de rango" not in filled


def test_prefill_empty_template_returns_as_is(monkeypatch):
    monkeypatch.setattr(llm, "call_structured", lambda **kw: {"answers": []})
    assert smart_ingest.prefill_template("doc", "# sin huecos\n") == "# sin huecos\n"


# --- lectura de documento --------------------------------------------------- #
def test_read_document_plaintext(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text("hola", encoding="utf-8")
    assert smart_ingest.read_document(str(p)) == "hola"


def test_read_document_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        smart_ingest.read_document(str(tmp_path / "nope.pdf"))


def test_template_path_unknown_type_raises():
    with pytest.raises(ValueError):
        smart_ingest.template_path("desconocido")


def test_template_paths_exist():
    # Las plantillas del repo estan donde el modulo las busca (contrato con --tipo).
    for tipo in smart_ingest.TEMPLATE_FILES:
        assert smart_ingest.template_path(tipo).exists()
