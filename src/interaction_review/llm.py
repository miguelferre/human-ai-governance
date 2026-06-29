"""Wrapper sobre el LLM con dos backends: Anthropic (nube) y Ollama (local).

Aisla la dependencia del LLM: el resto del codigo trabaja con dicts/pydantic y
no sabe que backend hay detras. Se elige con la variable de entorno LLM_BACKEND
('anthropic' por defecto, o 'ollama'). Los modelos se eligen con GEN_MODEL /
JUDGE_MODEL. Ver docs/adr/ADR-001, ADR-002 y ADR-004.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

# --- Defaults por backend ---
DEFAULT_GEN_MODEL = "claude-haiku-4-5-20251001"     # Anthropic: generador barato
DEFAULT_JUDGE_MODEL = "claude-sonnet-4-6"           # Anthropic: juez (modelo distinto)
DEFAULT_OLLAMA_GEN = "qwen2.5:14b"                  # Local: generador (lo que se evalua)
DEFAULT_OLLAMA_JUDGE = "qwen2.5:14b"                # Local: cabe entero en 16 GB y juzga bien.
# Nota (ADR-004): qwen2.5:32b seria el juez ideal por capacidad, pero NO cabe en 16 GB de
# VRAM (pesa ~24 GB) y se desborda a memoria compartida -> lentisimo, inutilizable iterando.
# gemma3:12b cabe pero es demasiado flojo para el emparejamiento. qwen2.5:14b es el unico
# que cabe Y juzga bien (verificado). Compromiso: gen = juez = qwen2.5:14b; la independencia
# (ADR-002) se mitiga con el anclaje al golden, y queda disponible un re-juicio independiente
# (p. ej. phi4:14b, otra familia que tambien cabe).

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_NUM_CTX = 16384  # el dossier + catalogo de guidelines no cabe en 2k


class LLMNotConfigured(RuntimeError):
    """No hay backend de LLM disponible (sin API key, o Ollama no responde)."""


def backend() -> str:
    return os.environ.get("LLM_BACKEND", "anthropic").lower()


def _is_ollama() -> bool:
    return backend() in ("ollama", "local")


def gen_model() -> str:
    default = DEFAULT_OLLAMA_GEN if _is_ollama() else DEFAULT_GEN_MODEL
    return os.environ.get("GEN_MODEL", default)


def judge_model() -> str:
    default = DEFAULT_OLLAMA_JUDGE if _is_ollama() else DEFAULT_JUDGE_MODEL
    return os.environ.get("JUDGE_MODEL", default)


# --------------------------------------------------------------------------- #
# Backend Anthropic (nube): tool-use forzado.
# --------------------------------------------------------------------------- #
def _anthropic_client():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMNotConfigured(
            "Falta ANTHROPIC_API_KEY. Exportala o usa LLM_BACKEND=ollama para local "
            "(ver docs/adr/ADR-003 y ADR-004)."
        )
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover
        raise LLMNotConfigured("El paquete 'anthropic' no esta instalado.") from e
    return anthropic.Anthropic()


def _call_anthropic(model, system, user, tool, temperature, max_tokens) -> dict[str, Any]:
    client = _anthropic_client()
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)
    raise RuntimeError("El modelo no devolvio un bloque tool_use.")


# --------------------------------------------------------------------------- #
# Backend Ollama (local): salida estructurada por `format` (JSON-schema).
# --------------------------------------------------------------------------- #
def ollama_payload(model, system, user, schema, temperature) -> dict[str, Any]:
    """Construye el cuerpo de /api/chat (funcion pura, testeable sin red)."""
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "format": schema,  # decodificacion restringida al JSON-schema
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": int(os.environ.get("OLLAMA_NUM_CTX", DEFAULT_NUM_CTX)),
        },
    }


def _call_ollama(model, system, user, tool, temperature) -> dict[str, Any]:
    import httpx

    base = os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL).rstrip("/")
    payload = ollama_payload(model, system, user, tool["input_schema"], temperature)
    timeout = float(os.environ.get("LLM_TIMEOUT", "900"))  # 15 min; en local lento conviene holgura
    try:
        resp = httpx.post(f"{base}/api/chat", json=payload, timeout=timeout)
        resp.raise_for_status()
    except httpx.ConnectError as e:
        raise LLMNotConfigured(
            f"Ollama no responde en {base}. Instala Ollama y/o arranca el servicio "
            "(`ollama serve`), y descarga el modelo (`ollama pull {model}`)."
        ) from e
    content = resp.json()["message"]["content"]
    return json.loads(content)


# --------------------------------------------------------------------------- #
# Interfaz unica.
# --------------------------------------------------------------------------- #
def call_structured(
    *,
    model: str,
    system: str,
    user: str,
    tool: dict[str, Any],
    temperature: float,
    max_tokens: int = 8000,
    retries: int = 3,
) -> dict[str, Any]:
    """Llama al LLM (segun LLM_BACKEND) y devuelve un dict conforme al esquema de `tool`."""
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            if _is_ollama():
                return _call_ollama(model, system, user, tool, temperature)
            return _call_anthropic(model, system, user, tool, temperature, max_tokens)
        except LLMNotConfigured:
            raise  # error de configuracion: no tiene sentido reintentar
        except Exception as e:  # noqa: BLE001 - reintento controlado ante fallos transitorios
            last_err = e
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Llamada al LLM fallida tras {retries} intentos: {last_err}")
