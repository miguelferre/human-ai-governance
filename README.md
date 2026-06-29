# Revisor de la capa de interacción humano-IA

Un motor de evaluación que, dada la descripción de un sistema de IA y de cómo
interactúa con su usuario, produce una **revisión estructurada de la capa de
interacción**: hallazgos atados a guidelines concretas (HAX-18 de Microsoft y PAIR
de Google), anti-patrones detectados y recomendaciones accionables.

> ¿Lo quieres en lenguaje llano, sin jerga, como se lo contarías a un cliente?
> [docs/PRODUCTO.md](docs/PRODUCTO.md) explica qué es y cómo sabemos que funciona.

Casi todas las herramientas de gobernanza (watsonx.governance, Fiddler, Arize)
auditan la **capa técnica** del modelo (métricas, sesgo, deriva, explicabilidad).
Casi nadie audita la **capa de interacción**: cómo se presenta el resultado a la
persona, cómo se calibra su confianza, si el diseño induce *automation bias*, cómo
se captura el *override*, la fatiga de alerta, el onboarding. Hoy eso se hace a
mano con una hoja de cálculo. Este proyecto explora si puede automatizarse.

## Esto es un experimento, no un producto asumido

La pregunta de partida no es "cómo construyo el agente", sino **si hace falta un
agente**. Antes de construir nada grande establecemos baselines simples y medimos.
La complejidad solo se justifica si **gana de forma medible**.

- **Escalera de complejidad:** B0 checklist determinista → B1 prompt único → B2
  few-shot → P3 pipeline determinista → A4 agente. Cada peldaño debe batir al
  anterior (ver [ADR-001](docs/adr/ADR-001-agente-o-no.md)).
- **Definición de éxito medible:** recall alto sobre problemas conocidos, precisión
  alta, **baja genericidad** (un hallazgo que valdría para cualquier sistema es un
  *fallo*) y batir a los baselines por encima del ruido entre ejecuciones
  (ver [ADR-002](docs/adr/ADR-002-diseno-evaluacion.md)).
- **Validación:** un caso clínico real ya trabajado (cribado de derivación AP →
  digestivo) es el *golden set* con respuestas conocidas. La pregunta: ¿los
  redescubre solo?

## Estado y resultado

Experimento **ejecutado y validado** (local con Ollama + nube con Claude). Escalera de
approaches: **B0** checklist determinista · **B1** prompt único · **B2** few-shot ·
**B1x** prompt único exhaustivo · **P3** pipeline determinista por bloques (no agente) ·
**A4** agente (bucle con control de flujo decidido por el modelo).

**Conclusión: un mapa condicional, no un ganador único** (detalle en
[docs/RESULTADOS.md](docs/RESULTADOS.md)):
- El LLM bate siempre a la checklist (B0 = suelo).
- **Caso fácil → el prompt único basta** (y es el más conciso).
- **Caso difícil → hace falta estructura:** el **pipeline determinista** es lo robusto; el agente solo
  iguala en el mejor caso (entrada completa) y **no tiene un nicho robusto** — pierde con entrada
  incompleta (ver C3 en [docs/TESTPLAN.md](docs/TESTPLAN.md)).
- **No es overfitting:** dos held-out documentados (HireVue no clínico, Epic clínico
  distinto) reproducen los patrones; y ningún approach inventa problemas en un sistema
  bien diseñado (control de falsos positivos, C1).
- Lección transversal: el **LLM-juez** (la medición) fue el eslabón frágil, no el
  generador → barandillas deterministas en código (ver ADR-004).

Plan de pruebas de validación/overfitting y su estado: [docs/TESTPLAN.md](docs/TESTPLAN.md).

## Instalación

```bash
uv sync --extra dev
```

## Uso

```bash
# Informe de hallazgos para un sistema descrito en un Dossier (JSON):
uv run interaction-review revisar --dossier ruta/dossier.json --approach b0

# Métricas contra un golden set (requiere adjudicaciones para recall/precisión):
uv run interaction-review evaluar --golden data/golden/answer_key.json \
    --dossier ruta/dossier.json --approach b0 --adjudications adj.json

# Experimento completo: corre B0/B1/B2 k veces, adjudica con el LLM-juez y compara
# (requiere ANTHROPIC_API_KEY; envía el dossier de-identificado a la nube):
export ANTHROPIC_API_KEY=...   # GEN_MODEL / JUDGE_MODEL opcionales
uv run interaction-review comparar \
    --dossier data/golden/caso-EII/dossier_blind.json \
    --golden  data/golden/caso-EII/answer_key.json \
    --approaches b0,b1,p3 --k 3 --save runs/eii.json
```

> **Nota de ejecución.** Para correr en **local** con [Ollama](https://ollama.com)
> antepón `LLM_BACKEND=ollama` (modelos por defecto `qwen2.5:14b` para generar y juzgar;
> ver [ADR-004](docs/adr/ADR-004-proveedor-llm-local.md)). Y si el Control de aplicaciones
> de Windows bloquea el lanzador `interaction-review.exe`, invoca el módulo directamente:
> `uv run python -m interaction_review.cli comparar ...` (usa `python.exe`, que sí está permitido).

## Estructura

```
src/interaction_review/
  schemas.py            Contrato de datos (Dossier, Finding, GoldenIssue, ...)
  guidelines/           HAX-18 y PAIR como datos enlazables + loader
  approaches/           Escalera de approaches (b0 hoy; b1/b2/p3/a4 después)
  metrics.py            recall, precisión, genericidad, grounding, F-beta
  report.py             Informes en markdown/texto
  cli.py                Comandos `revisar` y `evaluar`
docs/adr/               Decisiones de diseño (ADR-001..003)
data/golden/            PRIVADO, gitignored (caso clínico + answer key)
tests/                  Tests de esquemas, guidelines y métricas
```

## Privacidad

El material clínico es privado y **nunca se versiona** (`data/golden/`,
`data/private/`). Las llamadas al LLM envían datos a la nube, así que el dossier
debe estar **de-identificado** antes de cualquier corrida con datos reales
(ver [ADR-003](docs/adr/ADR-003-manejo-datos-phi.md)).

## Referencias

- Amershi et al. (2019), *Guidelines for Human-AI Interaction*, CHI. (HAX-18)
- Google PAIR, *People + AI Guidebook*.
