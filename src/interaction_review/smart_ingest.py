"""SMART ingestion: an arbitrary document (PDF, model card) -> pre-filled template.

Complements `ingest.py` (which parses OUR already-filled templates, no API). Here the
problem is the inverse and IRREDUCIBLE to code: reading heterogeneous documentation and
mapping its content to the template questions. That is done by the LLM (ADR-004: to the
model, only the irreducible part). The split:
  - CODE (deterministic): extract the text from the PDF, locate the ✍️ blanks in the
    template, rebuild the Markdown with the answers.
  - LLM: answer each question with what is in the document (and ONLY that).

The output is a template in OUR format (answers after ✍️), which a human reviews and then
`ingest` turns into a Dossier. The model pre-fills; the person validates.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from interaction_review import llm, prompts

_PEN = "✍"  # ✍ (with or without variation selector): marks the answer blank.

# Repo templates (resolved from the root; overridable with --template in the CLI).
_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"
TEMPLATE_FILES = {
    "profile": "01_system_card__technical_profile.md",
    "experience": "02_usage_experience__end_user.md",
    "inventory": "03_document_inventory.md",
}


def template_path(kind: str) -> Path:
    try:
        return _TEMPLATE_DIR / TEMPLATE_FILES[kind]
    except KeyError as e:
        raise ValueError(
            f"Unknown template type: {kind!r}. Use one of {sorted(TEMPLATE_FILES)}."
        ) from e


# --- Reading the document (deterministic) ----------------------------------- #
def read_document(path: str | Path) -> str:
    """Plain text of a document. PDF via pypdf; .md/.txt as-is."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Document does not exist: {p}")
    if p.suffix.lower() == ".pdf":
        return _read_pdf(p)
    return p.read_text(encoding="utf-8")


def _read_pdf(p: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:  # pragma: no cover
        raise ValueError("Reading PDF requires the 'pypdf' package (run `uv sync`).") from e
    reader = PdfReader(str(p))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    if not text.strip():
        raise ValueError(
            f"No text was extracted from {p.name}. Is it a scanned (image) PDF? The MVP does "
            "not do OCR; convert it to text or fill the template by hand."
        )
    return text


# --- Template blanks (deterministic) ---------------------------------------- #
@dataclass(frozen=True)
class TemplateSlot:
    index: int       # appearance order of the ✍️ (0-based)
    line_index: int  # line of the ✍️ in the template
    section: str     # active ## heading
    question: str    # last bold bullet (or "" if the blank hangs off the section)


def _clean_question(line: str) -> str:
    s = line.strip()
    if s.startswith("#"):
        return s.lstrip("#").strip()
    return s.lstrip("-*").strip().replace("**", "").strip()


def parse_template_slots(template_md: str) -> list[TemplateSlot]:
    """Locates each ✍️ blank with its section and its question (the bullet before it)."""
    slots: list[TemplateSlot] = []
    section = ""
    question = ""
    for i, line in enumerate(template_md.splitlines()):
        s = line.strip()
        if s.startswith("##"):
            section = _clean_question(line)
            question = ""  # new section: the active question resets
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
    """Collapses the answer to ONE line of plain text (robust for extract_answers)."""
    return " ".join(text.split())


def fill_template(template_md: str, answers: dict[int, str]) -> str:
    """Reinserts the answers after each ✍️, preserving the marker and the indentation."""
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


# --- Orchestration (LLM) ---------------------------------------------------- #
def prefill_template(
    doc_text: str,
    template_md: str,
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Pre-fills the template with the answers the document supports. One LLM call."""
    slots = parse_template_slots(template_md)
    if not slots:
        return template_md
    if len(doc_text) > prompts.PREFILL_MAX_CHARS:
        print(
            f"[prefill] warning: the document has {len(doc_text)} characters; only the first "
            f"{prompts.PREFILL_MAX_CHARS} are sent to the model. Content past that point will look "
            "'not stated' (blank slots). Split the document or fill those sections by hand.",
            file=sys.stderr,
        )
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
    kind: str = "profile",
    *,
    template_file: str | Path | None = None,
    model: str | None = None,
) -> str:
    """From a document to the `kind` template pre-filled (Markdown text)."""
    doc_text = read_document(doc_path)
    tpl = Path(template_file) if template_file else template_path(kind)
    template_md = tpl.read_text(encoding="utf-8")
    return prefill_template(doc_text, template_md, model=model)
