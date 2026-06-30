# Revisor de la capa de interacción humano-IA

**Audita el salpicadero de un sistema de IA, no el motor.**

![A reviewer for the human-AI interaction layer — audits how an AI presents itself to its users, anchored to HAX-18 and PAIR.](docs/assets/portada.svg)

Las herramientas de gobernanza de IA que existen hoy (watsonx.governance, Fiddler, Arize…)
auditan el **motor**: sesgo, precisión, deriva, explicabilidad técnica. Casi nadie mira el
**salpicadero**: cómo el sistema le presenta el resultado a la persona, cómo se calibra su
confianza, si el diseño induce *automation bias*, cómo se captura el *override*, la fatiga de
alerta, el onboarding. Y el salpicadero es justo donde un profesional decide si se fía del
modelo, lo corrige o lo ignora. Hoy eso se revisa a mano, con una hoja de cálculo. Este
proyecto lo automatiza.

> ¿Lo quieres en lenguaje llano, como se lo contarías a un cliente? → **[docs/PRODUCTO.md](docs/PRODUCTO.md)**

## Qué hace

Le das la descripción de un sistema —qué hace, cómo se le presenta al usuario y **qué cuentan
los que lo usan**— y te devuelve una lista de problemas de la capa de interacción. No problemas
de manual: cada hallazgo va **anclado a tres cosas**:

1. una **guía reconocida** que incumple,
2. el **punto concreto** del sistema donde ocurre,
3. la **evidencia** sacada de la propia documentación.

Si no puede apoyar un hallazgo en evidencia, no lo suelta. Un informe lleno de "mejora la
explicabilidad" no sirve, porque vale para cualquier sistema; esto señala "aquí, en esta
pantalla, el score aparece prerrellenado y empuja al médico a aceptarlo sin pensar".

Las guías van **masticadas**: usa las 18 de Microsoft (**HAX-18**) y el guidebook de Google
(**PAIR**) —el estándar de facto— traducidas a hallazgos accionables. No necesitas conocerlas.

## Cómo se alimenta: tres plantillas

No hace falta redactar un informe. El sistema se nutre de **tres plantillas** que rellenan las
partes interesadas:

- **[Perfil técnico](templates/01_ficha_sistema__perfil_tecnico.md)** — quien implementa o mantiene el sistema.
- **[Experiencia de uso](templates/02_experiencia_uso__usuario_final.md)** — **el usuario final**. Esta es la pieza que nadie más audita: el testimonio real de quien convive con la IA (¿la acepta por inercia? ¿puede corregirla? ¿la ignora?).
- **[Inventario de documentos](templates/03_inventario_documentos.md)**.

Esas tres respuestas **son** la entrada. El diferencial está en la segunda: cruzar lo que el
equipo técnico *cree* que pasa con lo que el usuario *vive* — porque ese desajuste es, en sí
mismo, una señal de la capa de interacción.

## ¿Funciona?

Sí, y está medido contra **casos held-out documentados por fuentes independientes**, en
**6 sectores** (sanidad, aviación, justicia, finanzas, administración pública, RRHH):

| Prueba | Resultado |
|---|---|
| Caso clínico real (golden de un experto humano) | redescubre **13-14 de 15** problemas; precisión ~100% |
| 5+ held-out (justicia, aviación, RRHH, sanidad, moderación) | recall **0.80-1.00** — no es overfitting |
| Sistema **bien diseñado** (control de falsos positivos) | **0 hallazgos** — no inventa para parecer productivo |
| Robustez al fraseo (mismo caso, otras palabras) | recall estable — entiende, no pesca palabras clave |
| **Test duro**: golden de la *Royal Commission* + dossier en bruto | **9/10** — recupera lo que un órgano humano independiente señaló |

Y lo hace con un **modelo barato**: no necesita la maquinaria más cara para funcionar.

Detalle y método: **[docs/RESULTADOS.md](docs/RESULTADOS.md)** (el experimento) ·
**[docs/RESULTADOS-testimonio.md](docs/RESULTADOS-testimonio.md)** (7 casos con testimonio real, 6 sectores).

## Es un experimento con método, no humo

La pregunta de partida no fue "cómo construyo el agente" sino **si hace falta uno**. Antes de
construir nada grande se establecieron baselines simples y se midió: la complejidad solo se
justifica si **gana de forma medible**.

- Escalera: **B0** checklist determinista → **B1** prompt único → **P3** pipeline determinista → **A4** agente.
- Conclusión —un mapa, no un ganador único—: el **pipeline determinista + deduplicado** es lo
  robusto. El **agente moderno no se paga solo**: iguala en el mejor caso, pero pierde cuando la
  entrada se degrada (lo normal en una auditoría).
- Lección transversal: el eslabón frágil fue el **LLM-juez** (la medición), no el generador →
  barandillas deterministas en código.

Decisiones de diseño en **[docs/adr/](docs/adr/)**; plan de validación y limitaciones honestas
en **[docs/TESTPLAN.md](docs/TESTPLAN.md)**.

## Instalación

```bash
uv sync --extra dev
```

## Uso

```bash
# Informe de hallazgos para un sistema descrito en un Dossier (JSON):
uv run interaction-review revisar --dossier data/examples/dossier_demo.json --approach p3 --dedup

# 'auto' (router de producto): b1 si el caso es fácil, p3+dedup si es difícil:
uv run interaction-review revisar --dossier ruta/dossier.json --approach auto

# Métricas contra un golden set (con LLM-juez):
uv run interaction-review comparar \
    --dossier ruta/dossier.json --golden ruta/answer_key.json \
    --approaches b0,b1,p3 --k 3 --save runs/salida.json
```

Approaches: `b0` (checklist, sin LLM) · `b1` (prompt único) · `p3` (pipeline, **el producto**) ·
`a4` (agente). `--dedup` consolida casi-duplicados (determinista); `--dedup-llm` es la capa
semántica opcional (gasta API). El comando `comparar` requiere `ANTHROPIC_API_KEY` (salvo solo `b0`).

> **Local / Windows.** Para correr en local con [Ollama](https://ollama.com) antepón
> `LLM_BACKEND=ollama`. Si el Control de aplicaciones de Windows bloquea el lanzador `.exe`,
> invoca el módulo directamente: `uv run python -m interaction_review.cli ...`.

## Estructura

```
src/interaction_review/
  schemas.py        Contrato de datos (Dossier, Finding, GoldenIssue, ...)
  guidelines/       HAX-18 y PAIR como datos enlazables (hax18.yaml, pair.yaml)
  approaches/       Escalera de approaches (b0/b1/b2/p3/p3n/a4)
  dedup.py          Consolidación determinista de hallazgos (producto)
  dedup_llm.py      Capa semántica opcional (LLM)
  router.py         Enrutado 'auto' por dificultad
  metrics.py        recall, precisión, genericidad, grounding, F-beta
  cli.py            Comandos revisar / evaluar / comparar
docs/adr/           Decisiones de diseño (ADR-001..006)
data/external/      Casos held-out públicos (dossier + golden por caso)
data/golden/        PRIVADO, gitignored (caso clínico real)
templates/          Las tres plantillas de entrada
```

## Privacidad

El material clínico es privado y **nunca se versiona** (`data/golden/`, `data/private/`). Las
llamadas al LLM envían datos a la nube, así que el dossier debe estar **de-identificado** antes
de cualquier corrida con datos reales (ver [ADR-003](docs/adr/ADR-003-manejo-datos-phi.md)).

## Referencias

- Amershi et al. (2019), *Guidelines for Human-AI Interaction*, CHI. (HAX-18)
- Google PAIR, *People + AI Guidebook*.
