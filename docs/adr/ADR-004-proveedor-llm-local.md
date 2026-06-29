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
- **Juez:** `qwen2.5:14b` — el único modelo que **cabe entero en 16 GB de VRAM** y a la
  vez **juzga bien** (verificado: empareja 5/5).
  - **Por qué no `qwen2.5:32b`** (juez ideal por capacidad): pesa ~24 GB, NO cabe en
    16 GB y Ollama lo desborda a memoria compartida vía PCIe. Una corrida `k=3` quedó
    ~4 h arrastrándose sin terminar. **Inutilizable para iterar** en este hardware.
  - **Por qué no `gemma3:12b`** (cabe en VRAM): se probó como juez y **falló el
    emparejamiento** (etiquetaba todo `tp_new` aun reconociendo la correspondencia en su
    razonamiento). Demasiado flojo.
  - **Independencia (ADR-002):** generador y juez acaban siendo el mismo modelo. Es un
    compromiso consciente, mitigado porque el juez empareja contra una verdad fija (el
    golden), no "puntúa libremente". Queda disponible un **re-juicio independiente** sobre
    los hallazgos ya guardados con otra familia que también quepa (p. ej. `phi4:14b`),
    sin necesidad de re-generar.

### Hallazgo de diseño: el ORDEN de campos del esquema importa

Con decodificación restringida (`format`), el modelo genera los campos del JSON en el
orden del esquema. Si `label` va antes que el razonamiento, el modelo **decide la
etiqueta a ciegas** y luego escribe una razón que la contradice (se vio: razonaba
"se corresponde con GI-03" pero etiquetaba `tp_new`). Reordenar (`judge_rationale`
primero) ayudó con B1, pero **con B2 (12 hallazgos por llamada) el modelo recaía**:
seguía etiquetando `tp_new` aun nombrando el golden correcto en su razón. Esto
infravaloraba el recall e inflaba la varianza (era artefacto del juez, no del generador).

**Fix robusto:** el modelo ya NO emite la etiqueta. Da sub-respuestas atómicas
(`corresponde_a_golden`, `es_generico`, `es_real`) y la **etiqueta se deriva en código**
(`judge.py`). Así no puede contradecirse. Lección general: con salida estructurada, no
pidas una conclusión que dependa de un razonamiento que aún no ha escrito; pide hechos
atómicos y compón la conclusión tú.

**Tercer endurecimiento — genericidad estructural:** en una corrida el juez empezó a
emparejar los ítems de B0 (checklist con locus/evidencia VACÍOS) a golden POR LA GUIDELINE
citada, contaminando el suelo (B0 recall 0,80). Causa: en la derivación, un match por
guideline ganaba a la genericidad. Fix: **gate duro en código** — un hallazgo sin anclaje
(`is_grounded()==False`) es `fp_generic` SIEMPRE, antes de mirar al juez; solo los anclados
se adjudican. **B0 es el canario**: si B0 puntúa > 0, la medición está rota. Patrón: mueve
al código todo juicio que pueda ser determinista; deja al modelo solo lo que exige criterio.

### Addendum (2026-06-29): la batería de validación se ejecutó en NUBE

El 14B local se volvió inusable para una batería grande (~10-30 min/llamada cuando el
equipo se usa; corridas pausadas por suspensión). Decisión: **mantener local como prueba
de "corre en tu hardware", pero ejecutar la batería de validación (held-out, k=3, casos
externos) en NUBE (Claude: `GEN_MODEL` Haiku, `JUDGE_MODEL` Sonnet)**. Los datos lo
permiten: el caso clínico va de-identificado y los held-out son públicos (ADR-003).
Resultó además **clave para la conclusión**: en local (modelo débil) el agente perdía;
en nube (modelo fuerte) el agente se justifica → la respuesta depende de la capacidad del
modelo (ver RESULTADOS.md). Robustez añadida para el backend nube: el tool-use de Anthropic
no garantiza la estructura como el `format` local, así que se filtran items no-dict.
La key vive en `.env` (gitignored).

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
