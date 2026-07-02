# Revisor de la capa de interacción humano-IA

> **Audita el salpicadero de un sistema de IA, no el motor.**

![El ecosistema de la capa de interacción humano-IA: los datos alimentan el modelo; el modelo mueve las herramientas conectadas y guía a la persona; la persona actúa y se adapta; los resultados vuelven para mejorar el modelo, todo bajo una capa de gobernanza.](docs/assets/human-ai-ecosystem.jpg)

Cuando una IA ayuda a decidir a una persona (un médico, un piloto, un funcionario), el punto donde
más cosas se tuercen no suele ser el modelo, es **cómo el sistema le habla a esa persona**: si le
presenta el resultado de forma que se fíe de más, si puede corregirlo, si el aviso salta en buen
momento. Esta herramienta audita esa capa, la de la interacción, y te devuelve una lista de
problemas concretos, cada uno atado a una guía de diseño reconocida y a la evidencia que lo sostiene.

> ¿Lo prefieres en lenguaje llano, como se lo contarías a un cliente? Está en **[docs/PRODUCTO.md](docs/PRODUCTO.md)**.

## El problema: se mira el motor, no el salpicadero

Me gusta explicarlo con el coche. Cuando compras uno, todo el mundo mira el motor: potencia,
consumo, lo que contamina. Está medido y regulado hasta el último tornillo. Pero casi nadie te
pregunta si el salpicadero está bien pensado: si el aviso del ángulo muerto salta cuando toca o te
despista justo al girar, si puedes silenciar una alerta que no paras de ver, si entiendes lo que te
dice el coche o te fías a ciegas.

Con la IA pasa lo mismo. Las herramientas de gobernanza que hay hoy (watsonx.governance, Fiddler,
Arize) auditan el motor: sesgo, precisión, deriva, explicabilidad técnica. El salpicadero no lo mira
casi nadie. Y el salpicadero, cómo se le presenta el resultado a la persona, es justo donde se cuela
el exceso de confianza en la máquina, la fatiga de alerta, el *override* que nadie captura, el aviso a
destiempo. Ahí es donde un profesional decide si se fía del modelo, lo corrige o lo ignora. Hoy eso
se revisa a mano, con una hoja de cálculo. Esto lo automatiza.

## Qué hace

Le das la descripción de un sistema (qué hace, cómo se le muestra al usuario y **qué cuentan los que
lo usan**) y te devuelve una lista de problemas de esa capa. Pero no problemas de manual. Cada
hallazgo va **atado a tres cosas**:

1. una **guía de diseño reconocida** que incumple,
2. el **punto concreto** del sistema donde ocurre,
3. la **evidencia** sacada de la propia documentación.

Si no puede apoyar un hallazgo en evidencia, no lo suelta. Un informe lleno de "mejora la
explicabilidad" no vale, porque sirve para cualquier sistema. Esto señala "aquí, en esta pantalla, el
score aparece prerrellenado y empuja al médico a aceptarlo sin pensar". Eso sí lo puedes accionar.

Las guías van **masticadas**: uso las 18 de Microsoft (**HAX-18**) y el guidebook de Google (**PAIR**),
que son el estándar de facto, traducidas a hallazgos concretos. No necesitas conocerlas.

## Cómo funciona

El sistema se alimenta de **tres plantillas** que rellenan las partes interesadas, las convierte en un
expediente (un *dossier*) y sobre él genera el informe.

### Las tres plantillas

- **[Perfil técnico](templates/01_ficha_sistema__perfil_tecnico.md)**: quien construye o mantiene el sistema.
- **[Experiencia de uso](templates/02_experiencia_uso__usuario_final.md)**: **el usuario final**. Esta es la pieza que nadie más audita, el testimonio real de quien convive con la IA (¿la acepta por inercia? ¿puede corregirla? ¿la ignora?).
- **[Inventario de documentos](templates/03_inventario_documentos.md)**: qué documentación hay disponible.

Esas tres respuestas **son** la entrada. El diferencial está en la segunda: cruzar lo que el equipo
técnico *cree* que pasa con lo que el usuario *vive*, porque ese desajuste es, en sí mismo, una señal
de la capa de interacción.

### De la entrada al informe

No hay que tocar JSON. Rellenas las plantillas en markdown y `ingerir` te arma el expediente solo, así
construir la entrada no cuesta lo mismo que auditar a mano. ¿Ya tienes un PDF, una model card o la
transcripción de una entrevista? `prerrellenar` se lo pasa al modelo para que rellene la plantilla (la
ficha desde el documento técnico, la experiencia desde la entrevista) con lo que consta, y solo eso:
lo que no aparece lo deja en blanco, no se lo inventa. Tú revisas, corriges, y de ahí a `revisar`, que
es quien genera el informe de hallazgos.

### Determinista por defecto, modelo solo donde hace falta, y local si quieres

El trabajo está repartido a propósito: **lo mecánico al código, al modelo solo lo que no se puede hacer
con reglas**.

- **Sin modelo de lenguaje, deterministas** (mismo resultado siempre, sin conexión): convertir las
  plantillas en el expediente (`ingerir`), consolidar duplicados (`dedup`), el mapeo normativo
  (`crosswalk`), el informe HTML, las métricas, y el approach **B0**, una checklist que sirve de suelo
  de control.
- **Necesitan un modelo**: generar los hallazgos a partir del expediente, el prerrelleno inteligente de
  plantillas, y el juez que puntúa en la evaluación. Es el eslabón irreducible: detectar un problema de
  interacción y anclarlo en evidencia no se hace con una regla.

Y ese modelo **puede ser local**: con `LLM_BACKEND=ollama` todo el pipeline corre en tu máquina con un
modelo abierto (qwen, gemma...), sin que ningún dato salga a la nube. Es lo que quieres cuando la
privacidad manda.

## ¿Funciona?

Sí, y está medido contra **casos held-out documentados por fuentes independientes**, en **8 sectores**
(sanidad, aviación, justicia, finanzas, administración pública, RRHH, bienestar, discapacidad):

| Prueba | Resultado |
|---|---|
| Caso clínico real (golden de un experto humano) | redescubre **13-14 de 15** problemas, precisión ~100% |
| Held-out en varios sectores | recall **0.80-1.00**, no es overfitting |
| Sistema **bien diseñado** (control de falsos positivos) | **0 hallazgos**, no inventa para parecer productivo |
| Robustez al fraseo (mismo caso, otras palabras) | recall estable, entiende y no pesca palabras clave |
| **Test duro**, n=3: golden de un órgano independiente (Royal Commission, un auditor estatal, un tribunal federal) + dossier en bruto, manos separadas | recall **0.70-0.90** (media ~0.79): recupera lo que señalaron sin verlo |
| **Número del producto**, con el pipeline reproducible y un **juez independiente** (otro modelo), k=3 | p3: recall **0.91 ± 0.055**, precisión **0.965** |

El último es el que más me importa, porque no lo mide el mismo motor que genera: el juez es otro modelo
y el flujo es reproducible. Y lo hace con un **modelo barato** de generador. Repetido tres veces por
caso, el número aguanta y la barra entre casos se estrecha, así que no era suerte de una sola corrida.

**Y lo del testimonio no es una corazonada, está medido.** Si al expediente le quitas la voz del usuario
y dejas solo la documentación técnica, el revisor pierde recall justo en los problemas que solo esa voz
revela: cae de **0.83 a 0.56**, mientras los controles no se mueven. Y los más vivenciales, la
deferencia a la máquina, sentirse culpable ante el sistema, la confianza erosionada, caen **a cero** sin
la voz, porque ninguna ficha técnica los insinúa. Cuánto baja el agregado depende de cuánto infiera el
generador de la propia doc (con un modelo más conservador la caída llegaba a 0.33), pero el núcleo duro,
lo que la persona vive, solo lo trae la voz. Ese es el argumento del diferencial, ya con dato.

Detalle y método: **[docs/RESULTADOS.md](docs/RESULTADOS.md)** (el experimento) ·
**[docs/RESULTADOS-testimonio.md](docs/RESULTADOS-testimonio.md)** (casos con testimonio real, test duro
n=3 y el número reproducible) · **[docs/RESULTADOS-ablacion-testimonio.md](docs/RESULTADOS-ablacion-testimonio.md)**
(el efecto de la voz).

## Para quien firma la compra

HAX y PAIR son el estándar de diseño, pero quien aprueba la compra (gobernanza, calidad, cumplimiento) no
razona en HAX-G2, razona en AI Act y NIST. Así que el informe se traduce solo. Con `--crosswalk`, cada
hallazgo sale también mapeado a los artículos del **EU AI Act** (el 13 de transparencia, el 14 de
supervisión humana, que nombra el *automation bias* de forma explícita, el 86 de derecho a explicación) y
a las subcategorías del **NIST AI RMF**. Deja de ser una crítica de diseño y pasa a ser evidencia de
conformidad que entra en su expediente. Es orientativo, no dictamen legal, y así está dicho en el propio
informe. Y si hay que enseñarlo, `--format html` saca un informe autocontenido y presentable que imprime a
PDF sin depender de nada externo.

Dicho con precisión: esto es una **auditoría para la gobernanza**, no un sistema que gobierne en tiempo
real. Produce la evidencia que alimenta el expediente de cumplimiento y la decisión de qué arreglar. No
se queda vigilando el sistema ni interviene solo (ver [Qué es y qué no es](#qué-es-y-qué-no-es)).

## Un experimento con método, no humo

La pregunta de partida no fue "cómo construyo el agente" sino **si hace falta uno**. Antes de construir
nada grande se establecieron baselines simples y se midió: la complejidad solo se justifica si **gana de
forma medible**.

- Escalera: **B0** checklist determinista, **B1** prompt único, **P3** pipeline determinista, **A4** agente.
- Conclusión, que es un mapa y no un ganador único: el **pipeline determinista + deduplicado** es lo
  robusto. El **agente moderno no se paga solo**: iguala en el mejor caso, pero pierde cuando la entrada
  se degrada (lo normal en una auditoría).
- Lección transversal: el eslabón frágil fue el **LLM-juez** (la medición), no el generador, así que la
  medición se blindó con barandillas deterministas en código.

Decisiones de diseño en **[docs/adr/](docs/adr/)**; plan de validación y limitaciones honestas en
**[docs/TESTPLAN.md](docs/TESTPLAN.md)**.

## Qué es y qué no es

Para que nadie se lleve una idea equivocada:

- **Es una auditoría, no gobernanza en tiempo real.** Te da una foto rigurosa de la capa de interacción
  en un momento dado, con hallazgos accionables. No se queda enganchado al sistema vigilándolo ni
  interviene solo. Su sitio es alimentar la gobernanza, no sustituirla.
- **El testimonio capta lo que la persona vive y sabe contar, no lo que ni ella percibe.** Es su mayor
  fuerza y su límite honesto: alguien con exceso de confianza en la máquina que no es consciente de ello
  no lo va a narrar, y ahí la entrevista no llega. El complemento natural es la **telemetría objetiva**:
  cuánto tarda en aceptar una recomendación frente a lo que tardaría en leerla, la tasa real de
  corrección, cuántas alertas ignora. Hoy eso se puede aportar como registros de uso (plantilla 03);
  integrarlo como una fuente que se cruza con el resto es la dirección por la que el producto crece.
- **Da la foto; aún falta cerrar el ciclo.** El informe es una lista de problemas anclados. Registrar qué
  se corrigió y volver a medir para demostrar que el riesgo bajó es el siguiente paso, todavía no está.
- **La generación de hallazgos necesita un modelo de lenguaje**, y eso es a propósito (es lo irreducible),
  no una dependencia accidental. Todo lo demás es determinista y corre sin nube; el modelo, además, puede
  ser local. Así que "sin API no funciona nada" no es cierto: la ingesta, el dedup, el crosswalk, el HTML
  y el canario B0 van sin conexión.

## Instalación

```bash
uv sync --extra dev
```

## Uso

```bash
# (Opcional) De un documento a una plantilla prerrellena con el modelo (revísala luego):
uv run interaction-review prerrellenar --doc ruta/model_card.pdf --tipo ficha       --out templates/01_relleno.md
uv run interaction-review prerrellenar --doc ruta/entrevista.txt  --tipo experiencia --out templates/02_relleno.md

# De las tres plantillas rellenas al expediente (determinista, sin API):
uv run interaction-review ingerir \
    --ficha templates/01_relleno.md --experiencia templates/02_relleno.md \
    --inventario templates/03_relleno.md --out ruta/dossier.json

# Informe de hallazgos, con el mapeo normativo y en HTML listo para imprimir a PDF:
uv run interaction-review revisar --dossier ruta/dossier.json --approach p3 --dedup \
    --crosswalk --format html --out informe.html

# 'auto' (router de producto): b1 si el caso es fácil, p3+dedup si es difícil:
uv run interaction-review revisar --dossier ruta/dossier.json --approach auto

# Métricas contra un golden set (con LLM-juez):
uv run interaction-review comparar \
    --dossier ruta/dossier.json --golden ruta/answer_key.json \
    --approaches b0,b1,p3 --k 3 --save runs/salida.json
```

Approaches: `b0` (checklist, sin modelo) · `b1` (prompt único) · `p3` (pipeline, **el producto**) ·
`a4` (agente). `--dedup` consolida casi-duplicados (determinista); `--dedup-llm` es la capa semántica
opcional (usa modelo). `--crosswalk` añade el mapeo a EU AI Act / NIST; `--format html` saca el informe
presentable. El comando `comparar` requiere `ANTHROPIC_API_KEY` (salvo solo `b0`), o corre entero en
local con `LLM_BACKEND=ollama`.

> **Local / Windows.** Para correr en local con [Ollama](https://ollama.com) antepón `LLM_BACKEND=ollama`.
> Si el Control de aplicaciones de Windows bloquea el lanzador `.exe`, invoca el módulo directamente:
> `uv run python -m interaction_review.cli ...`.

## Estructura

```
src/interaction_review/
  schemas.py        Contrato de datos (Dossier, Finding, GoldenIssue, ...)
  guidelines/       HAX-18 y PAIR como datos enlazables + regulatory_map.yaml (AI Act / NIST)
  approaches/       Escalera de approaches (b0/b1/b2/p3/p3n/a4)
  ingest.py         Plantillas rellenas -> expediente (determinista, sin API)
  smart_ingest.py   Documento (PDF/model card/entrevista) -> plantilla prerrellena (modelo; el humano revisa)
  dedup.py          Consolidación determinista de hallazgos (producto)
  dedup_llm.py      Capa semántica opcional (modelo)
  router.py         Enrutado 'auto' por dificultad
  regulatory.py     Crosswalk de los hallazgos a EU AI Act / NIST AI RMF
  ablation.py       Ablación del testimonio (dossier con voz vs sin voz)
  metrics.py        recall, precisión, genericidad, grounding, F-beta, recall por fuente
  report.py         Informe markdown · report_html.py Informe HTML autocontenido
  cli.py            Comandos prerrellenar / ingerir / revisar / evaluar / comparar
docs/adr/           Decisiones de diseño (ADR-001..008)
data/external/      Casos held-out públicos (dossier + golden por caso)
data/golden/        PRIVADO, gitignored (caso clínico real)
templates/          Las tres plantillas de entrada
```

## Privacidad

El material clínico es privado y **nunca se versiona** (`data/golden/`, `data/private/`). Las llamadas al
modelo en la nube envían datos fuera, así que el dossier debe estar **de-identificado** antes de cualquier
corrida con datos reales (ver [ADR-003](docs/adr/ADR-003-manejo-datos-phi.md)). Si eso no es suficiente,
el backend local (`LLM_BACKEND=ollama`) mantiene todo dentro de tu máquina.

## Referencias

- Amershi et al. (2019), *Guidelines for Human-AI Interaction*, CHI. (HAX-18)
- Google PAIR, *People + AI Guidebook*.
