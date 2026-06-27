"""Wrapper minimo sobre el SDK de Anthropic para llamadas con salida estructurada.

Aisla la dependencia del LLM: el resto del codigo trabaja con dicts/pydantic.
Los modelos se leen de variables de entorno para poder "empezar barato" y
cambiar sin tocar codigo (ADR-001/ADR-002).
"""

from __future__ import annotations

import os
import time
from typing import Any

# Defaults: generador barato; juez con modelo DISTINTO (no auto-evaluacion, ADR-002).
DEFAULT_GEN_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_JUDGE_MODEL = "claude-sonnet-4-6"


class LLMNotConfigured(RuntimeError):
    """No hay credenciales para llamar al LLM."""


def gen_model() -> str:
    return os.environ.get("GEN_MODEL", DEFAULT_GEN_MODEL)


def judge_model() -> str:
    return os.environ.get("JUDGE_MODEL", DEFAULT_JUDGE_MODEL)


def _client():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMNotConfigured(
            "Falta ANTHROPIC_API_KEY en el entorno. Exportala (o usa un .env) antes de "
            "ejecutar approaches con LLM o el juez. El dossier de-identificado se enviara "
            "a la nube de Anthropic (ver docs/adr/ADR-003)."
        )
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover
        raise LLMNotConfigured("El paquete 'anthropic' no esta instalado.") from e
    return anthropic.Anthropic()


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
    """Llama al modelo forzando el uso de `tool` y devuelve sus argumentos (dict).

    Reintenta ante errores transitorios con backoff simple.
    """
    client = _client()
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
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
        except Exception as e:  # noqa: BLE001 - reintento generico controlado
            last_err = e
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Llamada al LLM fallida tras {retries} intentos: {last_err}")
