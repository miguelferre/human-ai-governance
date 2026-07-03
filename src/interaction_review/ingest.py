"""Ingesting filled templates -> Dossier (deterministic, offline).

Attacks the bottleneck of the real use case: making the input cost less to build
than auditing by hand. The client fills friendly Markdown templates (templates/01
technical, 02 user, 03 inventory) and this turns them into the canonical `Dossier`
that the approaches consume, with no manual JSON editing.

It is a parser for the CONTROLLED format of our templates (questions in bold or `##`
headings, answer after the ✍️ marker), not a reader of arbitrary documents:
smartly ingesting heterogeneous PDFs/model cards needs the LLM and lives elsewhere.
Here, zero API.
"""

from __future__ import annotations

from pathlib import Path

from interaction_review.schemas import Dossier, Source, SourceKind

_PEN = "✍"  # ✍ (with or without variation selector) = space for the answer.


def _is_question_bullet(s: str) -> bool:
    """True if a stripped line is a TEMPLATE question bullet (not answer content).

    Template questions are **bold** bullets (`- **...**`) or inventory checkboxes
    (`- [ ]`/`- [x]`). A plain bullet (`- foo`) written by the user INSIDE an answer
    is content, not a new question: treating it as structural truncated multi-line
    answers that contained a Markdown list (silent data loss on the star input).
    """
    if s.startswith(("- ", "* ")):
        body = s[2:].lstrip()
        return body.startswith(("**", "["))
    return False


def _is_structural(line: str) -> bool:
    """True if the line cuts an answer (new question/section/instruction).

    Plain bullets do NOT cut: they may be list items the user wrote inside a
    multi-line answer. Only bold/checkbox question bullets, headings and the other
    markers below end an answer.
    """
    s = line.strip()
    if not s:
        return False  # blank lines do NOT cut (multi-paragraph answers)
    return (
        s.startswith(("#", "---", ">", "**"))
        or _is_question_bullet(s)
        or s.startswith("\U0001f3af")  # 🎯 "What for" meta-instruction
        or _PEN in s
    )


def _prompt_text(line: str) -> str:
    """Extracts the text of a question (bold bullet) or heading."""
    s = line.strip()
    if s.startswith("#"):
        return s.lstrip("#").strip()
    s = s.lstrip("-*").strip()
    return s.replace("**", "").strip()


def extract_answers(md: str) -> list[tuple[str, str]]:
    """(question, answer) for each ✍️ with a non-empty answer, in order.

    The answer is the text after the ✍️ marker (rest of the line + following
    lines) up to the next structural element. Ignores the instructions header
    (everything before the first `---` separator).
    """
    lines = md.splitlines()
    # Skip the template header (up to the first '---').
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
        if s.startswith("#") or (_is_question_bullet(s) and _PEN not in s):
            last_prompt = _prompt_text(line)
            i += 1
            continue
        if _PEN in line:
            # Answer: rest of the line after the ✍️, plus following lines.
            # The marker is ✍ (U+270D) + variation selector U+FE0F: we strip it.
            rest = line.split(_PEN, 1)[1].replace("️", "").strip()
            buf = [rest] if rest else []
            j = i + 1
            while j < len(lines) and not _is_structural(lines[j]):
                buf.append(lines[j].strip())  # continuation lines are indented
                j += 1
            answer = "\n".join(buf).strip()
            if answer:
                out.append((last_prompt, answer))
            i = j
            continue
        i += 1
    return out


def _format_source(answers: list[tuple[str, str]]) -> str:
    """Source text: each answered question with its answer."""
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
    profile: list[str] | None = None,
    experience: list[str] | None = None,
    inventory: str | None = None,
    system_name: str | None = None,
    domain: str | None = None,
    summary: str = "",
) -> Dossier:
    """Builds a Dossier from filled templates.

    `profile`/`experience` accept several paths (several technicians / users). The
    name and domain are taken from the first profile if not passed explicitly.
    Raises ValueError if there is no source with content.
    """
    profile = profile or []
    experience = experience or []
    sources: list[Source] = []

    for idx, path in enumerate(profile, 1):
        answers = extract_answers(_read(path))
        if not answers:
            continue
        suffix = f"-{idx}" if len(profile) > 1 else ""
        sources.append(
            Source(
                id=f"technical-profile{suffix}",
                kind=SourceKind.TECHNICIAN,
                label="System card (technical profile)",
                content=_format_source(answers),
            )
        )
        if system_name is None:
            system_name = _find(answers, "system name")
        if domain is None:
            domain = _find(answers, "domain")

    for idx, path in enumerate(experience, 1):
        answers = extract_answers(_read(path))
        if not answers:
            continue
        suffix = f"-{idx}" if len(experience) > 1 else ""
        sources.append(
            Source(
                id=f"end-user-experience{suffix}",
                kind=SourceKind.END_USER,
                label="Usage experience (end user)",
                content=_format_source(answers),
            )
        )

    if inventory:
        answers = extract_answers(_read(inventory))
        checked = _checked_documents(_read(inventory))
        content = _format_source(answers)
        if checked:
            content = ("Available documents:\n" + "\n".join(f"- {m}" for m in checked)
                       + (("\n\n" + content) if content else ""))
        if content:
            sources.append(
                Source(
                    id="document-inventory",
                    kind=SourceKind.DOCUMENT,
                    label="Inventory of provided documents",
                    content=content,
                )
            )

    if not sources:
        raise ValueError(
            "No template had answers. Were the ✍️ blanks filled in?"
        )

    return Dossier(
        system_name=system_name or "(unnamed system)",
        domain=domain or "(unspecified domain)",
        summary=summary,
        sources=sources,
    )


def _checked_documents(md: str) -> list[str]:
    """Documents marked with [x] in the inventory template."""
    out: list[str] = []
    for ln in md.splitlines():
        s = ln.strip()
        if s.lower().startswith(("- [x]", "* [x]")):
            text = s[5:].strip().replace("**", "")
            if text:
                out.append(text)
    return out
