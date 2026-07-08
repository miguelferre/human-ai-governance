"""Tests for the MCP server.

Offline like the rest of the suite: the LLM path is monkeypatched, everything else is
deterministic. Exercises the real protocol in-memory (client <-> server in one process) plus
the pure helpers.
"""

from __future__ import annotations

import json

import anyio
import pytest
from mcp.shared.memory import create_connected_server_and_client_session as connect

from interaction_review import llm
from interaction_review.mcp_server import _as_list, _select_guidelines, mcp

_PROFILE = """# Template 01 - System card
---
## 0. Identification
- **System name:**
  ✍️ CribaTest
- **Domain / what it is used for:**
  ✍️ triage of gastroenterology referrals
## 1. What it does
- **What exactly does it produce?**
  ✍️ a bare risk score with two buttons
"""

_EXPERIENCE = """# Template 02 - User
---
## 1. You and the tool
- **What is your role?**
  ✍️ family doctor
- **Do you accept even when unsure?**
  ✍️ sometimes yes, out of speed
"""


def _run(coro_fn):
    return anyio.run(coro_fn)


def _json(result):
    return json.loads(result.content[0].text)


def _text(result):
    return result.content[0].text


# --- pure helpers (no protocol) -------------------------------------------- #
def test_as_list_normalizes():
    assert _as_list(None) == []
    assert _as_list("x") == ["x"]
    assert _as_list(["a", "b"]) == ["a", "b"]


def test_select_guidelines_and_errors():
    hax = _select_guidelines("hax")
    assert hax and all(g.corpus.value == "HAX" for g in hax)
    assert {g.corpus.value for g in _select_guidelines("hax,pair")} == {"HAX", "PAIR"}
    with pytest.raises(ValueError):
        _select_guidelines("nope")
    with pytest.raises(ValueError):
        _select_guidelines("")


# --- protocol: the six tools are exposed ------------------------------------ #
def test_lists_six_tools():
    async def go():
        async with connect(mcp._mcp_server) as client:
            return sorted(t.name for t in (await client.list_tools()).tools)

    assert _run(go) == sorted(
        [
            "review_dossier",
            "ingest_templates",
            "validate_dossier",
            "regulatory_crosswalk",
            "render_report",
            "get_template",
        ]
    )


# --- deterministic tools end-to-end ----------------------------------------- #
def test_get_template_ingest_validate_roundtrip():
    async def go():
        async with connect(mcp._mcp_server) as client:
            prof = _text(await client.call_tool("get_template", {"kind": "profile"}))
            assert "✍" in prof
            doss = _json(
                await client.call_tool(
                    "ingest_templates",
                    {"profile_md": _PROFILE, "experience_md": _EXPERIENCE},
                )
            )
            val = _json(await client.call_tool("validate_dossier", {"dossier": doss}))
            return doss, val

    doss, val = _run(go)
    assert doss["system_name"] == "CribaTest"
    assert val["valid"] is True
    assert val["stats"]["has_end_user_voice"] is True
    assert val["stats"]["kinds"].get("end_user") == 1


def test_validate_reports_bad_dossier_path():
    async def go():
        async with connect(mcp._mcp_server) as client:
            return _json(
                await client.call_tool("validate_dossier", {"dossier_path": "does/not/exist.json"})
            )

    val = _run(go)
    assert val["valid"] is False and val["errors"]


def test_resources_readable():
    async def go():
        async with connect(mcp._mcp_server) as client:
            ex = await client.read_resource("example://dossier")
            gl = await client.read_resource("guidelines://hax")
            tp = await client.read_resource("template://experience")
            return ex, gl, tp

    ex, gl, tp = _run(go)
    assert json.loads(ex.contents[0].text)["sources"]
    assert isinstance(json.loads(gl.contents[0].text), list)
    assert "✍" in tp.contents[0].text


def test_render_report_and_crosswalk_no_llm():
    finding = {
        "id": "f1",
        "title": "Score shown without an uncertainty band",
        "guideline_ids": ["HAX-G14"],
        "locus": "main screen",
        "evidence": "the score appears as a bare number",
        "severity": "high",
        "rationale": "invites over-trust",
        "recommendation": "show a confidence band",
    }

    async def go():
        async with connect(mcp._mcp_server) as client:
            rep = _json(
                await client.call_tool(
                    "render_report",
                    {
                        "dossier_path": "data/examples/dossier_demo.json",
                        "findings": [finding],
                        "format": "html",
                        "crosswalk": True,
                    },
                )
            )
            cw = _text(await client.call_tool("regulatory_crosswalk", {"findings": [finding]}))
            return rep, cw

    rep, cw = _run(go)
    assert rep["format"] == "html" and "<html" in rep["report"].lower()
    assert "Regulatory crosswalk" in cw


# --- review: b0 is free/deterministic; p3 goes through the mocked model ------ #
def test_review_b0_is_free_and_deterministic():
    async def go():
        async with connect(mcp._mcp_server) as client:
            return _json(
                await client.call_tool(
                    "review_dossier",
                    {"dossier_path": "data/examples/dossier_demo.json", "approach": "b0"},
                )
            )

    out = _run(go)
    assert out["meta"]["model"] == "deterministic (no model)"
    assert out["findings"] and "Interaction layer review" in out["report"]


def test_review_p3_with_mocked_generator(monkeypatch):
    def fake(**kwargs):
        return {
            "findings": [
                {
                    "title": "Score shown without an uncertainty band",
                    "guideline_ids": ["HAX-G11"],
                    "locus": "main screen",
                    "evidence": "the score appears as a bare number with two buttons",
                    "severity": "high",
                    "rationale": "invites over-trust",
                    "recommendation": "show a confidence band",
                }
            ]
        }

    monkeypatch.setattr(llm, "call_structured", fake)

    async def go():
        async with connect(mcp._mcp_server) as client:
            return _json(
                await client.call_tool(
                    "review_dossier",
                    {
                        "dossier_path": "data/examples/dossier_demo.json",
                        "approach": "p3",
                        "crosswalk": True,
                    },
                )
            )

    out = _run(go)
    assert out["findings"], "p3 should surface at least one finding with the mocked generator"
    assert out["meta"]["model"] == llm.gen_model()
    assert "Regulatory crosswalk" in out["report"]


def test_review_missing_key_is_actionable(monkeypatch):
    def boom(**kwargs):
        raise llm.LLMNotConfigured("Missing ANTHROPIC_API_KEY.")

    monkeypatch.setattr(llm, "call_structured", boom)

    async def go():
        async with connect(mcp._mcp_server) as client:
            return await client.call_tool(
                "review_dossier",
                {"dossier_path": "data/examples/dossier_demo.json", "approach": "b1"},
            )

    res = _run(go)
    assert res.isError
    assert "ANTHROPIC_API_KEY" in res.content[0].text and "ollama" in res.content[0].text
