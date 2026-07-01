"""Tests del informe HTML (report_html): HTML valido, contenido, escapado y crosswalk."""

from interaction_review.report_html import render_findings_html
from interaction_review.schemas import Dossier, Finding, Severity, Source, SourceKind


def _dossier() -> Dossier:
    return Dossier(
        system_name="Sistema X",
        domain="cribado",
        sources=[Source(id="d", kind=SourceKind.DOCUMENT, label="ficha", content="c")],
    )


def _finding(**kw) -> Finding:
    base = dict(id="f1", title="Score prerrellenado", guideline_ids=["HAX-G2"],
                locus="pantalla", evidence="el score aparece marcado", severity=Severity.HIGH)
    base.update(kw)
    return Finding(**base)


def test_is_self_contained_html_document():
    html = render_findings_html(_dossier(), [_finding()], "p3")
    assert html.startswith("<!doctype html>")
    assert html.rstrip().endswith("</html>")
    assert "<style>" in html  # CSS embebido, sin dependencias externas
    assert "http://" not in html and "https://" not in html  # sin recursos de red


def test_contains_system_and_finding_content():
    html = render_findings_html(_dossier(), [_finding()], "p3")
    assert "Sistema X" in html
    assert "Score prerrellenado" in html
    assert "HAX-G2" in html
    assert "el score aparece marcado" in html


def test_escapes_html_in_dynamic_content():
    """Texto libre del dossier/hallazgo no debe inyectar markup."""
    evil = _finding(title="<script>alert(1)</script>", evidence="a & b < c")
    html = render_findings_html(_dossier(), [evil], "p3")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert "a &amp; b &lt; c" in html


def test_grounded_vs_generic_badge():
    grounded = render_findings_html(_dossier(), [_finding()], "p3")
    assert "Anclado" in grounded
    bare = render_findings_html(_dossier(), [_finding(guideline_ids=[], locus="", evidence="")], "b0")
    assert "Sin anclar" in bare


def test_stats_counts():
    findings = [_finding(id="a"), _finding(id="b", severity=Severity.LOW), _finding(id="c", guideline_ids=[], locus="", evidence="")]
    html = render_findings_html(_dossier(), findings, "p3")
    assert ">3<" in html  # 3 hallazgos
    # 2 de 3 anclados = 67%
    assert "67%" in html


def test_crosswalk_optional():
    with_cw = render_findings_html(_dossier(), [_finding()], "p3", include_crosswalk=True)
    without = render_findings_html(_dossier(), [_finding()], "p3", include_crosswalk=False)
    assert "Crosswalk normativo" in with_cw
    assert "Crosswalk normativo" not in without
    assert "no dictamen legal" in with_cw.lower()


def test_empty_findings_message():
    html = render_findings_html(_dossier(), [], "b0")
    assert "Sin hallazgos" in html
    assert ">0<" in html  # 0 hallazgos en las stats


def test_merged_count_shown():
    html = render_findings_html(_dossier(), [_finding(merged_count=4)], "p3")
    assert "Consolida 4" in html
