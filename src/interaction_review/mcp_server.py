"""MCP server: exposes the human-AI interaction-layer reviewer over the Model Context Protocol.

Thin wrappers over the existing programmatic entry points (`approaches.REGISTRY`, `ingest`,
`report`, `regulatory`, `guidelines`). No CLI logic is duplicated. Every tool is **stateless**
(nothing depends on a previous call), so the migration to the 2026-07-28 stateless spec / SDK v2
(`FastMCP` -> `MCPServer`) is mechanical. See docs/adr/ADR-009-mcp-server.md.

Run: `interaction-review-mcp` (stdio transport). The model credentials are read from the process
environment (`ANTHROPIC_API_KEY`, or `LLM_BACKEND=ollama` for a fully local run); nothing loads a
`.env` here, so the key must be provided by the client's `env` block (see the README).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import anyio
from mcp.server.fastmcp import FastMCP

from interaction_review import ablation
from interaction_review.approaches import REGISTRY
from interaction_review.dedup import deduplicate
from interaction_review.dedup_llm import deduplicate_llm
from interaction_review.guidelines import all_guidelines
from interaction_review.guidelines.loader import load_corpus
from interaction_review.ingest import build_dossier
from interaction_review.llm import LLMNotConfigured, gen_model
from interaction_review.report import render_findings_md, render_regulatory_crosswalk
from interaction_review.report_html import render_findings_html
from interaction_review.router import route
from interaction_review.schemas import Dossier, Finding, Guideline, GuidelineCorpus
from interaction_review.smart_ingest import template_path

INSTRUCTIONS = (
    "Audit the human-AI interaction layer of an AI system: how it presents its results, whether the "
    "person can correct it, and whether its alerts fire at the right moment, scored against Microsoft's "
    "HAX-18 and Google's PAIR guidelines. Each finding is anchored in evidence and can be mapped to the "
    "EU AI Act and NIST AI RMF.\n\n"
    "Typical flow: get_template -> fill the blanks -> ingest_templates -> validate_dossier -> "
    "review_dossier -> render_report. Or start from the `audit_my_system` prompt. `review_dossier` "
    "needs a model unless approach='b0' (a free deterministic checklist); everything else is "
    "deterministic and free."
)

mcp = FastMCP("interaction-review", instructions=INSTRUCTIONS)

# Demo dossier: prefer the packaged copy (works when installed via uvx), fall back to the checkout.
_PKG_EXAMPLE = Path(__file__).parent / "examples" / "dossier_demo.json"
_REPO_EXAMPLE = Path(__file__).resolve().parents[2] / "data" / "examples" / "dossier_demo.json"


# --------------------------------------------------------------------------- #
# Helpers (pure, shared by the tools; mirror cli.py without importing its argparse layer).
# --------------------------------------------------------------------------- #
def _tool_version() -> str:
    try:
        return version("interaction-review")
    except PackageNotFoundError:
        return "dev"


def _provenance(approach: str) -> dict[str, str]:
    """The provenance block the CLI writes into reports (date / tool version / generator model)."""
    return {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "tool_version": _tool_version(),
        "model": "deterministic (no model)" if approach == "b0" else gen_model(),
    }


def _select_guidelines(corpus: str) -> list[Guideline]:
    """'hax', 'pair' or 'hax,pair' -> the guideline list.

    Raises ValueError (never SystemExit: this runs inside a long-lived server, not a CLI process).
    """
    valid = {c.value: c for c in GuidelineCorpus}  # {"HAX": ..., "PAIR": ...}
    wanted = set()
    for raw in corpus.split(","):
        c = raw.strip().upper()
        if not c:
            continue
        if c not in valid:
            raise ValueError(f"Unknown corpus {raw.strip()!r}. Use 'hax', 'pair' or 'hax,pair'.")
        wanted.add(valid[c])
    if not wanted:
        raise ValueError("No corpus selected. Use 'hax', 'pair' or 'hax,pair'.")
    return [g for g in all_guidelines() if g.corpus in wanted]


def _resolve_dossier(dossier: Dossier | None, dossier_path: str | None) -> Dossier:
    """Exactly one of an inline `Dossier` (already schema-validated by the transport) or a path."""
    if (dossier is None) == (dossier_path is None):
        raise ValueError("Pass exactly one of `dossier` (inline object) or `dossier_path`.")
    if dossier is not None:
        return dossier
    data = json.loads(Path(dossier_path).read_text(encoding="utf-8"))
    return Dossier.model_validate(data)


def _as_list(x: str | list[str] | None) -> list[str]:
    if x is None:
        return []
    return [x] if isinstance(x, str) else list(x)


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
@mcp.tool(
    description=(
        "Audit the human-AI interaction layer described in a dossier and return the findings report "
        "plus the structured findings. Uses an LLM unless approach='b0' (a free deterministic "
        "checklist). Provide EITHER `dossier` (an inline object) OR `dossier_path`. approach: 'p3' "
        "(default, the product), 'b1' (fast single prompt), 'b0' (free, no model), or 'auto' (router). "
        "format: 'md' or 'html'. A p3 review makes several model calls and can take a minute or two."
    )
)
async def review_dossier(
    dossier: Dossier | None = None,
    dossier_path: str | None = None,
    approach: str = "p3",
    corpus: str = "hax,pair",
    dedup: bool = True,
    dedup_llm: bool = False,
    crosswalk: bool = False,
    format: str = "md",
) -> dict[str, Any]:
    doss = _resolve_dossier(dossier, dossier_path)
    guidelines = _select_guidelines(corpus)
    if format not in ("md", "html"):
        raise ValueError("format must be 'md' or 'html'.")
    if approach != "auto" and approach not in REGISTRY:
        raise ValueError(f"Unknown approach {approach!r}. Available: {sorted(REGISTRY)} or 'auto'.")

    def _run() -> list[Finding]:
        if approach == "auto":
            findings, _choice = route(doss, guidelines)
        else:
            findings = REGISTRY[approach](doss, guidelines)
        if dedup_llm:
            return deduplicate_llm(findings)
        if dedup:
            return deduplicate(findings)
        return findings

    try:
        # Run the (blocking) pipeline off the event loop so the server keeps answering pings.
        findings = await anyio.to_thread.run_sync(_run)
    except LLMNotConfigured as e:
        raise ValueError(
            f"{e} Set ANTHROPIC_API_KEY in the server's env block, or use LLM_BACKEND=ollama for a "
            "fully local run. (Tip: approach='b0' needs no model at all.)"
        ) from e

    meta = _provenance(approach)
    if format == "html":
        report = render_findings_html(doss, findings, approach, include_crosswalk=crosswalk, meta=meta)
    else:
        report = render_findings_md(doss, findings, approach, meta=meta)
        if crosswalk:
            report = report + "\n" + render_regulatory_crosswalk(findings)
    return {
        "report": report,
        "format": format,
        "findings": [f.model_dump(mode="json") for f in findings],
        "meta": meta,
    }


@mcp.tool(
    description=(
        "Build a dossier JSON from filled-in template TEXT (deterministic, no LLM). Pass the Markdown "
        "CONTENT of the templates, not file paths (get them with get_template). `profile_md` and "
        "`experience_md` accept a string or a list of strings (several technicians / users)."
    )
)
def ingest_templates(
    profile_md: str | list[str] | None = None,
    experience_md: str | list[str] | None = None,
    inventory_md: str | None = None,
    system_name: str | None = None,
    domain: str | None = None,
    summary: str = "",
) -> dict[str, Any]:
    dossier = build_dossier(
        profile_texts=_as_list(profile_md),
        experience_texts=_as_list(experience_md),
        inventory_text=inventory_md,
        system_name=system_name,
        domain=domain,
        summary=summary,
    )
    return dossier.model_dump(mode="json")


@mcp.tool(
    description=(
        "Validate a dossier against the schema and report basic stats (source kinds, whether it "
        "carries end-user testimony). No LLM. Provide `dossier` or `dossier_path`."
    )
)
def validate_dossier(
    dossier: Dossier | None = None,
    dossier_path: str | None = None,
) -> dict[str, Any]:
    try:
        doss = _resolve_dossier(dossier, dossier_path)
    except Exception as e:  # invalid JSON / schema / bad args -> report, do not crash the tool
        return {"valid": False, "errors": [str(e)], "stats": {}}
    kinds: dict[str, int] = {}
    for s in doss.sources:
        kinds[s.kind.value] = kinds.get(s.kind.value, 0) + 1
    warnings: list[str] = []
    if not ablation.has_voice(doss):
        warnings.append(
            "No end_user source: the reviewer loses the problems that only the user's voice reveals "
            "(the product's differentiator). Add a filled 02_usage_experience template if you can."
        )
    if not doss.summary.strip():
        warnings.append("Empty summary: a one-paragraph overview of the interaction flow helps the reviewer.")
    return {
        "valid": True,
        "errors": [],
        "stats": {
            "system_name": doss.system_name,
            "domain": doss.domain,
            "n_sources": len(doss.sources),
            "kinds": kinds,
            "has_end_user_voice": ablation.has_voice(doss),
            "warnings": warnings,
        },
    }


@mcp.tool(
    description=(
        "Map a set of findings to the EU AI Act and NIST AI RMF requirements they touch (indicative, "
        "not a legal opinion). Returns Markdown. No LLM."
    )
)
def regulatory_crosswalk(findings: list[Finding]) -> str:
    return render_regulatory_crosswalk(findings)


@mcp.tool(
    description=(
        "Render already-generated findings into a report (Markdown or self-contained HTML), optionally "
        "with the regulatory crosswalk. No LLM: use it to get the HTML after a review, or to add the "
        "crosswalk, without paying for the model again. Provide `dossier` or `dossier_path`."
    )
)
def render_report(
    findings: list[Finding],
    dossier: Dossier | None = None,
    dossier_path: str | None = None,
    approach: str = "p3",
    format: str = "md",
    crosswalk: bool = False,
) -> dict[str, Any]:
    doss = _resolve_dossier(dossier, dossier_path)
    if format not in ("md", "html"):
        raise ValueError("format must be 'md' or 'html'.")
    meta = _provenance(approach)
    if format == "html":
        report = render_findings_html(doss, findings, approach, include_crosswalk=crosswalk, meta=meta)
    else:
        report = render_findings_md(doss, findings, approach, meta=meta)
        if crosswalk:
            report = report + "\n" + render_regulatory_crosswalk(findings)
    return {"report": report, "format": format}


@mcp.tool(
    description=(
        "Return the raw Markdown of one of the three input templates: 'profile' (technical), "
        "'experience' (end user, the piece that matters most), or 'inventory'. Fill the blanks after "
        "the pen marker, then pass the text to ingest_templates."
    )
)
def get_template(kind: str) -> str:
    return template_path(kind).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Resources (some clients prefer resources; the tools above mirror them for clients that do not).
# --------------------------------------------------------------------------- #
@mcp.resource(
    "template://{kind}",
    description="One of the three input templates: profile, experience or inventory.",
)
def template_resource(kind: str) -> str:
    return template_path(kind).read_text(encoding="utf-8")


@mcp.resource(
    "guidelines://{corpus}",
    mime_type="application/json",
    description="The HAX-18 (corpus=hax) or PAIR (corpus=pair) guideline corpus, as JSON.",
)
def guidelines_resource(corpus: str) -> str:
    try:
        c = GuidelineCorpus(corpus.strip().upper())
    except ValueError as e:
        raise ValueError(f"Unknown corpus {corpus!r}. Use 'hax' or 'pair'.") from e
    return json.dumps([g.model_dump(mode="json") for g in load_corpus(c)], ensure_ascii=False, indent=2)


@mcp.resource(
    "example://dossier",
    mime_type="application/json",
    description="A small synthetic demo dossier to try the tools on.",
)
def example_dossier_resource() -> str:
    path = _PKG_EXAMPLE if _PKG_EXAMPLE.is_file() else _REPO_EXAMPLE
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Prompts (guided flows).
# --------------------------------------------------------------------------- #
@mcp.prompt(
    name="audit_my_system",
    description="Guided flow to audit the human-AI interaction layer of your system from scratch.",
)
def audit_my_system(system_name: str = "", context: str = "") -> str:
    head = f"I want to audit the human-AI interaction layer of {system_name or 'my AI system'}."
    ctx = f" Context: {context}" if context else ""
    return (
        f"{head}{ctx}\n\n"
        "Please walk me through it:\n"
        "1. Call get_template('profile'), get_template('experience') and get_template('inventory'), "
        "and help me fill the blanks (after the pen marker), interviewing me where needed. The "
        "'experience' template is the end user's testimony and is the part that matters most.\n"
        "2. Call ingest_templates with the filled Markdown to build the dossier.\n"
        "3. Call validate_dossier and warn me if there is no end-user voice.\n"
        "4. Call review_dossier (approach='p3', crosswalk=true) to get the findings.\n"
        "5. Offer to call render_report with format='html' for a presentable, printable report."
    )


@mcp.prompt(
    name="review_from_files",
    description="Shortcut: review an existing dossier JSON on disk (Claude Code / IDEs with file access).",
)
def review_from_files(dossier_path: str) -> str:
    return (
        f"Review the human-AI interaction layer described in the dossier at '{dossier_path}'. "
        "Call validate_dossier(dossier_path=...) first, then review_dossier(dossier_path=..., "
        "approach='p3', crosswalk=true). Summarize the anchored findings by severity."
    )


def main() -> None:
    """Console-script entry point (`interaction-review-mcp`). stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
