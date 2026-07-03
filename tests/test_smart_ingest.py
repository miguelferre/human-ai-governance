"""Tests for smart ingestion (document -> pre-filled template).

The deterministic part (blank parsing, reinsertion, closing the loop with extract_answers)
is tested thoroughly; the single LLM call is monkeypatched, no API.
"""

import pytest

from interaction_review import llm, smart_ingest
from interaction_review.ingest import extract_answers

_TEMPLATE = """# Template 01 - System card
**How:** fill below.
---
## 0. Identification
- **System name:**
  ✍️
- **Domain / what it is used for:**
  ✍️
🎯 *What for:* to place it.
---
## 3. How the result is presented
- **Where does it appear?**
  ✍️
## What you already suspect (optional)
✍️
"""


# --- blank parsing ---------------------------------------------------------- #
def test_parse_slots_captures_question_and_section():
    slots = smart_ingest.parse_template_slots(_TEMPLATE)
    assert len(slots) == 4
    assert slots[0].section.startswith("0.")
    assert slots[0].question == "System name:"
    assert slots[2].question == "Where does it appear?"
    # The last blank has no bullet: its question is empty (falls back to the section).
    assert slots[3].question == ""
    assert "suspect" in slots[3].section.lower()


# --- reinsertion ------------------------------------------------------------ #
def test_fill_template_preserves_marker_and_leaves_blanks():
    slots = smart_ingest.parse_template_slots(_TEMPLATE)
    filled = smart_ingest.fill_template(_TEMPLATE, {0: "CribaTest", 1: "gastro triage"})
    assert "✍️ CribaTest" in filled
    assert "✍️ gastro triage" in filled
    # The number of markers does not change; unanswered ones stay as an empty blank.
    assert filled.count("✍") == len(slots)


def test_fill_collapses_multiline_answer():
    filled = smart_ingest.fill_template(_TEMPLATE, {0: "line1\n  line2\n\nline3"})
    assert "✍️ line1 line2 line3" in filled


# --- closing the loop: prefill -> extract_answers --------------------------- #
def test_prefill_roundtrips_through_extract_answers(monkeypatch):
    monkeypatch.setattr(llm, "call_structured", lambda **kw: {"answers": [
        {"slot": 0, "answer": "CribaTest"},
        {"slot": 1, "answer": "triage of gastroenterology referrals"},
        {"slot": 2, "answer": ""},  # empty: not stated -> must not fill
    ]})
    filled = smart_ingest.prefill_template("doc...", _TEMPLATE)
    d = dict(extract_answers(filled))
    assert d["System name:"] == "CribaTest"
    assert d["Domain / what it is used for:"] == "triage of gastroenterology referrals"
    assert not any("appear" in q for q in d)  # the empty slot does not reappear


def test_prefill_ignores_invalid_slots(monkeypatch):
    monkeypatch.setattr(llm, "call_structured", lambda **kw: {"answers": [
        {"slot": 99, "answer": "out of range"},
        {"slot": "x", "answer": "bad type"},
        {"slot": 0, "answer": "CribaTest"},
    ]})
    filled = smart_ingest.prefill_template("doc...", _TEMPLATE)
    assert "✍️ CribaTest" in filled
    assert "out of range" not in filled


def test_prefill_empty_template_returns_as_is(monkeypatch):
    monkeypatch.setattr(llm, "call_structured", lambda **kw: {"answers": []})
    assert smart_ingest.prefill_template("doc", "# no blanks\n") == "# no blanks\n"


def test_prefill_warns_when_document_is_truncated(monkeypatch, capsys):
    # A document longer than PREFILL_MAX_CHARS must warn (was: silent truncation, so
    # answers past the cut looked "not stated").
    from interaction_review import prompts

    monkeypatch.setattr(llm, "call_structured", lambda **kw: {"answers": []})
    big = "x" * (prompts.PREFILL_MAX_CHARS + 100)
    smart_ingest.prefill_template(big, _TEMPLATE)
    assert "only the first" in capsys.readouterr().err.lower()


# --- document reading ------------------------------------------------------- #
def test_read_document_plaintext(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text("hello", encoding="utf-8")
    assert smart_ingest.read_document(str(p)) == "hello"


def test_read_document_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        smart_ingest.read_document(str(tmp_path / "nope.pdf"))


def test_template_path_unknown_type_raises():
    with pytest.raises(ValueError):
        smart_ingest.template_path("unknown")


def test_template_paths_exist():
    # The repo templates are where the module looks for them (contract with --type).
    for kind in smart_ingest.TEMPLATE_FILES:
        assert smart_ingest.template_path(kind).exists()
