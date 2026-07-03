"""Tests for the LLM wrapper: backend selection and Ollama payload construction.

Makes no real network calls: httpx.post is monkeypatched where an Ollama call is exercised.
"""

import httpx
import pytest

from interaction_review import llm
from interaction_review.prompts import FINDINGS_TOOL

_TOOL = {"name": "t", "input_schema": {"type": "object"}}


def test_backend_por_defecto_es_anthropic(monkeypatch):
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    monkeypatch.delenv("GEN_MODEL", raising=False)
    monkeypatch.delenv("JUDGE_MODEL", raising=False)
    assert llm.backend() == "anthropic"
    assert "claude" in llm.gen_model()
    assert "claude" in llm.judge_model()


def test_backend_ollama_cambia_modelos_por_defecto(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.delenv("GEN_MODEL", raising=False)
    monkeypatch.delenv("JUDGE_MODEL", raising=False)
    # qwen2.5:14b fits in 16 GB and judges well; 32b overflows (see ADR-004).
    assert "qwen2.5:14b" == llm.gen_model()
    assert "qwen2.5:14b" == llm.judge_model()


def test_env_override_de_modelos(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setenv("GEN_MODEL", "mi-modelo")
    assert llm.gen_model() == "mi-modelo"


def test_ollama_payload_lleva_schema_y_opciones(monkeypatch):
    monkeypatch.delenv("OLLAMA_NUM_CTX", raising=False)
    schema = FINDINGS_TOOL["input_schema"]
    p = llm.ollama_payload("qwen2.5:14b-instruct", "SYS", "USR", schema, 0.7)
    assert p["model"] == "qwen2.5:14b-instruct"
    assert p["format"] == schema          # decoding constrained to the JSON schema
    assert p["stream"] is False
    assert p["options"]["temperature"] == 0.7
    assert p["options"]["num_ctx"] == llm.DEFAULT_NUM_CTX
    roles = [m["role"] for m in p["messages"]]
    assert roles == ["system", "user"]


# --- Ollama error handling (config errors must not be retried as transient) --- #
def test_ollama_404_is_config_error(monkeypatch):
    # Model not pulled -> 404 -> LLMNotConfigured (NOT 3 retries then RuntimeError).
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    req = httpx.Request("POST", "http://localhost:11434/api/chat")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(404, request=req))
    with pytest.raises(llm.LLMNotConfigured) as ei:
        llm.call_structured(model="qwen2.5:14b", system="s", user="u", tool=_TOOL, temperature=0.0)
    assert "pull" in str(ei.value).lower()


def test_ollama_connect_error_message_interpolates_model(monkeypatch):
    # Regression: the 'ollama pull {model}' hint was a non-f-string literal.
    monkeypatch.setenv("LLM_BACKEND", "ollama")

    def boom(*a, **k):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(llm.LLMNotConfigured) as ei:
        llm.call_structured(model="my-model-xyz", system="s", user="u", tool=_TOOL, temperature=0.0)
    msg = str(ei.value)
    assert "my-model-xyz" in msg and "{model}" not in msg
