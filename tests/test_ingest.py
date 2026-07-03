"""Tests for template ingestion -> Dossier (ingest). Deterministic parser."""

import pytest

from interaction_review.ingest import extract_answers, ingest_templates
from interaction_review.schemas import SourceKind

_PROFILE = """# Template 01 - System card
**How:** write below each question.
> Remember: no personal data.
---
## 0. Identification
- **System name:**
  ✍️ CribaTest
- **Domain / what it is used for:**
  ✍️ triage of gastroenterology referrals
- **Status:** (idea / pilot / production)
  ✍️
## 1. What it does
- **What exactly does it produce?**
  ✍️ a risk score
  in three levels (high/medium/low)
"""

_EXPERIENCE = """# Template 02 - User
**How:** answer in your own words.
---
## 1. You and the tool
- **What is your role?**
  ✍️ family doctor
## 6. Do you trust it?
- **Do you accept even when unsure?**
  ✍️ sometimes yes, out of speed
"""


# --- extract_answers -------------------------------------------------------- #
def test_extracts_answered_questions_only():
    ans = extract_answers(_PROFILE)
    d = dict(ans)
    assert d["System name:"] == "CribaTest"
    assert d["Domain / what it is used for:"] == "triage of gastroenterology referrals"
    # "Status" was left unanswered (empty ✍️) -> does not appear.
    assert not any("Status" in q for q, _ in ans)


def test_answer_can_be_multiline():
    d = dict(extract_answers(_PROFILE))
    assert d["What exactly does it produce?"] == "a risk score\nin three levels (high/medium/low)"


def test_ignores_header_blockquote_and_instructions():
    ans = extract_answers(_PROFILE)
    joined = " ".join(q + " " + a for q, a in ans)
    assert "Remember" not in joined  # header blockquote
    assert "write below" not in joined  # **How:** instruction


def test_empty_template_yields_no_answers():
    empty = "# T\n---\n## 1. X\n- **question?**\n  ✍️\n"
    assert extract_answers(empty) == []


def test_answer_with_markdown_list_is_not_truncated():
    # A user answers with a Markdown list (natural in .md). Plain bullets are answer
    # content, not new questions: they must NOT truncate the answer (regression).
    md = (
        "# T\n---\n"
        "## 7. Alerts\n"
        "- **How many alerts does it generate?**\n"
        "  ✍️ Far too many. The main problems are:\n"
        "  - alert fatigue: ~40 popups per shift\n"
        "  - no way to silence repeated warnings\n"
        "  Nurses end up ignoring all of them.\n"
        "- **Does the system interrupt?**\n"
        "  ✍️ Yes, mid-task.\n"
    )
    d = dict(extract_answers(md))
    ans = d["How many alerts does it generate?"]
    assert "alert fatigue" in ans
    assert "no way to silence" in ans
    assert "Nurses end up ignoring" in ans  # the line AFTER the list also survives
    # the next bold question still cuts the answer and is captured on its own
    assert d["Does the system interrupt?"] == "Yes, mid-task."


# --- ingest_templates ------------------------------------------------------- #
def test_builds_dossier_with_correct_kinds(tmp_path):
    f = tmp_path / "profile.md"; f.write_text(_PROFILE, encoding="utf-8")
    e = tmp_path / "user.md"; e.write_text(_EXPERIENCE, encoding="utf-8")
    d = ingest_templates(profile=[str(f)], experience=[str(e)])

    assert d.system_name == "CribaTest"
    assert d.domain == "triage of gastroenterology referrals"
    kinds = {s.kind for s in d.sources}
    assert SourceKind.TECHNICIAN in kinds
    assert SourceKind.END_USER in kinds
    tech = next(s for s in d.sources if s.kind is SourceKind.TECHNICIAN)
    assert "a risk score" in tech.content


def test_multiple_users_get_distinct_ids(tmp_path):
    e1 = tmp_path / "u1.md"; e1.write_text(_EXPERIENCE, encoding="utf-8")
    e2 = tmp_path / "u2.md"; e2.write_text(_EXPERIENCE, encoding="utf-8")
    f = tmp_path / "profile.md"; f.write_text(_PROFILE, encoding="utf-8")
    d = ingest_templates(profile=[str(f)], experience=[str(e1), str(e2)])
    user_ids = sorted(s.id for s in d.sources if s.kind is SourceKind.END_USER)
    assert user_ids == ["end-user-experience-1", "end-user-experience-2"]


def test_inventory_extracts_checked_documents(tmp_path):
    inv = tmp_path / "inv.md"
    inv.write_text(
        "# Inv\n---\n## Documents\n- [x] **Screenshots**\n- [ ] Model card\n- [x] User manual\n",
        encoding="utf-8",
    )
    f = tmp_path / "profile.md"; f.write_text(_PROFILE, encoding="utf-8")
    d = ingest_templates(profile=[str(f)], inventory=str(inv))
    doc = next(s for s in d.sources if s.kind is SourceKind.DOCUMENT)
    assert "Screenshots" in doc.content
    assert "User manual" in doc.content
    assert "Model card" not in doc.content  # not checked


def test_explicit_name_domain_override(tmp_path):
    f = tmp_path / "profile.md"; f.write_text(_PROFILE, encoding="utf-8")
    d = ingest_templates(profile=[str(f)], system_name="Other", domain="other domain")
    assert d.system_name == "Other"
    assert d.domain == "other domain"


def test_raises_when_all_templates_empty(tmp_path):
    empty = tmp_path / "e.md"; empty.write_text("# T\n---\n- **x?**\n  ✍️\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ingest_templates(profile=[str(empty)])
