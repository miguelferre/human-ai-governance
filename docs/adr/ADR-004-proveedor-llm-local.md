# ADR-004: Proveedor de LLM — backend local (Ollama) además de nube (Anthropic)

- **Estado:** Aceptada
- **Fecha:** 2026-06-27

## Contexto

El motor necesita un LLM para B1/B2 y para el juez. La nube (Anthropic) da máxima
capacidad y tool-use fiable, pero envía el dossier fuera del equipo (ADR-003). Para
un caso clínico, ejecutar **en local** elimina esa categoría de riesgo y encaja con
el ángulo de gobernanza del proyecto. El usuario dispone de hardware capaz
(RTX 5080 Laptop, 16 GB VRAM; 64 GB RAM) y eligió local.

## Decisión

Soportar **dos backends** tras una interfaz única (`llm.call_structured`),
seleccionables por entorno (`LLM_BACKEND`):

- **`anthropic`** (nube): tool-use forzado. Útil como "techo de referencia" de
  capacidad y para interpretar los resultados locales.
- **`ollama`** (local, por defecto en esta fase): llamadas a `/api/chat` con
  **salida estructurada por `format` (JSON-schema)** — decodificación restringida
  que garantiza JSON válido incluso en modelos pequeños (Gemma no es fiable en
  tool-calling, así que NO usamos tool-use en local).

Modelos por defecto en local (override con `GEN_MODEL`/`JUDGE_MODEL`):

- **Generador:** `qwen2.5:14b` (instruct) — entra entero en 16 GB, rápido, fuerte en
  seguimiento de instrucciones y JSON.
- **Juez:** `gemma3:12b` — **familia distinta** del generador, para no auto-evaluarse
  (ADR-002).
- **Escalada opcional** a `qwen2.5:32b` / `gemma3:27b` (offload parcial a RAM) como
  "mejor local", para medir cuánta capacidad mínima exige la tarea.

`OLLAMA_NUM_CTX` (def. 16384) evita truncar el dossier + catálogo de guidelines.

## Consecuencias

- **Privacidad:** en local el dato no sale del equipo; se relaja la presión de
  de-identificación de ADR-003 (aunque se mantiene la higiene de no meter PHI).
- **Confound de capacidad:** un modelo local débil puede fallar por capacidad, no
  porque el approach no sirva. Mitigación: usar el modelo local más capaz que dé el
  hardware y, opcionalmente, una corrida con Anthropic como techo de referencia.
- **Reversible / sin lock-in:** todos los runtimes compatibles-OpenAI (Ollama,
  LM Studio, llama.cpp-server, vLLM) sirven con el mismo código; Ollama se eligió por
  fricción mínima en Windows y `format` con JSON-schema.
- **Reproducibilidad:** pesos fijos + seed posibles en local; se registran modelos y
  `k` por corrida (ADR-002).
