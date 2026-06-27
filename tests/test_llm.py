"""Tests del wrapper LLM: seleccion de backend y construccion del payload de Ollama.

No hace llamadas de red: solo logica determinista (env -> modelo, dict del payload).
"""

from interaction_review import llm
from interaction_review.prompts import FINDINGS_TOOL


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
    assert "qwen2.5" in llm.gen_model()
    assert "gemma3" in llm.judge_model()  # familia distinta -> no auto-evaluacion


def test_env_override_de_modelos(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setenv("GEN_MODEL", "mi-modelo")
    assert llm.gen_model() == "mi-modelo"


def test_ollama_payload_lleva_schema_y_opciones(monkeypatch):
    monkeypatch.delenv("OLLAMA_NUM_CTX", raising=False)
    schema = FINDINGS_TOOL["input_schema"]
    p = llm.ollama_payload("qwen2.5:14b-instruct", "SYS", "USR", schema, 0.7)
    assert p["model"] == "qwen2.5:14b-instruct"
    assert p["format"] == schema          # decodificacion restringida al JSON-schema
    assert p["stream"] is False
    assert p["options"]["temperature"] == 0.7
    assert p["options"]["num_ctx"] == llm.DEFAULT_NUM_CTX
    roles = [m["role"] for m in p["messages"]]
    assert roles == ["system", "user"]
