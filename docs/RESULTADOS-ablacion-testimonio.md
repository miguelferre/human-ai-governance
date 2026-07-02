# Resultados — ablación del testimonio: ¿aporta la voz del usuario?

El diferenciador comercial del revisor es incorporar el **testimonio del usuario final**, no
solo auditar el diseño en abstracto. Pero era una promesa **sin demostrar**: el control C3
(RESULTADOS.md) mostró que, en recall **global**, el dossier con voz y sin voz rinden casi
igual. Eso no la refuta —el valor de la voz podría estar en un subconjunto de problemas que
*solo* ella revela— pero obliga a medirlo en vez de afirmarlo. Esto es esa medición dirigida.

Diseño completo en [ADR-007](adr/ADR-007-ablacion-del-testimonio.md). En una frase: etiquetamos
cada problema conocido por **la fuente que lo revela** y separamos el recall de los problemas
que solo revela la voz.

## Qué se midió

Sobre cada `GoldenIssue` de los **7 casos con testimonio real** (64 problemas en 6 sectores),
se etiquetó a mano —leyendo el contenido de cada fuente del dossier— de dónde es *detectable*:

- **`user_only`** — solo lo sustenta el testimonio de un usuario final. Sin esa voz, el
  problema es invisible en el dossier.
- **`tech_only`** — solo lo sustenta la documentación o el perfil técnico.
- **`both`** — lo describe la documentación **y** lo vive el usuario.

El etiquetado va en el answer key (fuera del dossier ciego; el revisor no lo ve). Se hizo con
anotadores independientes por caso y el criterio del ADR (ser estricto: si un usuario no
menciona de verdad el problema, no cuenta como que lo sustenta). Es reproducible con
`scripts/ablacion_report.py dist`.

## Resultado offline: cuánto del golden depende de la voz

Este conteo **no gasta API** y es informativo por sí solo: es el **techo** de lo que el
testimonio puede aportar al recall. Si casi no hubiera `user_only`, la voz no podría aportar
mucho aunque quisiéramos.

| caso | total | user_only | both | tech_only | unknown | % voz-dependiente |
|---|---|---|---|---|---|---|
| robodebt-hard | 10 | 0 | 4 | 5 | 1 | 0% |
| concern-cds | 9 | 0 | 7 | 2 | 0 | 0% |
| alert-fatigue-ehr | 8 | 2 | 5 | 1 | 0 | 25% |
| post-office-horizon | 9 | 2 | 5 | 2 | 0 | 22% |
| toeslagenaffaire | 10 | 2 | 4 | 4 | 0 | 20% |
| asiana-214 | 9 | 3 | 3 | 3 | 0 | 33% |
| cierre-cuentas-bancarias | 9 | 3 | 3 | 3 | 0 | 33% |
| **TOTAL** | **64** | **12 (19%)** | **31 (48%)** | **20 (31%)** | **1** |  |

## Lectura honesta

**1. La voz sí aporta, pero no como recall masivo: es 1 de cada 5 problemas.** El 19% de los
problemas conocidos **solo** los revela el testimonio. No es cero (matiza el titular de C3, que
miraba solo el recall global) ni es la mayoría. El grueso del valor de la voz (el 48% `both`)
es **grounding**: da evidencia vívida y creíble a problemas que la documentación ya revela.

**2. El aporte depende de cuán documentado esté el caso.** Los dos casos con **0 `user_only`**
—robodebt y CONCERN— son los más cubiertos por informes oficiales o fichas técnicas
exhaustivas: ahí ya está casi todo por escrito y el testimonio solo confirma. En cambio, donde
la fuente viva es el operador o el piloto (Asiana, cierre de cuentas: **3/9**), un tercio de
los problemas se perdería sin la voz. **Implicación de producto:** cuanto menos documentado
esté un sistema —el caso normal en una auditoría real— más aporta el testimonio.

**3. Lo que *solo* revela la voz es sistemáticamente la capa cognitiva.** Los 12 `user_only`
no son aleatorios; son casi siempre el mismo tipo de problema:

- **Automation bias / deferencia a la máquina** — cerrar la alerta sin leerla (alert-fatigue),
  "acabo confiando en que la máquina tendrá razón" (cierre de cuentas), "llegué a dudar de mí
  mismo antes que del programa" (Post Office).
- **Modelo mental erróneo del automatismo** — el piloto que da por hecho que el A/T mantiene la
  velocidad, o que importa una expectativa de protección de otro avión (Asiana).
- **Temporización vivida** — la alerta que salta en el peor momento y corta la tarea
  (alert-fatigue).
- **Erosión de confianza / carga de la prueba percibida** — "pierdes la confianza en el propio
  gobierno", "eres tú quien tiene que demostrar que no eres una defraudadora" (Toeslagen).

La documentación técnica revela la **estructura** (opacidad del modelo, falta de captura del
override, umbrales mal calibrados). El testimonio revela la **vivencia y la cognición**: el
exceso de confianza, el modelo mental, la fatiga, el mal momento. Y esa capa cognitiva es
justamente la más peligrosa en un sistema clínico y la que ninguna ficha técnica va a declarar.

## El efecto: recall con voz vs sin voz (corrida hecha)

El conteo de arriba mide el **techo** (cuántos problemas dependen de la voz). Esta corrida mide
el **efecto**: cuánto cae el recall del revisor cuando le quitamos el testimonio. Diseño
**within-subject** sobre los 5 casos con `user_only` (45 problemas):

- **Generador ciego** (Sonnet): produce hallazgos anclados sobre el dossier **con voz** y, por
  separado, sobre el **mismo dossier sin las fuentes `end_user`** (`ablation.without_voice`).
  Mismo prompt; no ve el golden ni conoce la hipótesis.
- **Juez independiente** (Opus, otro rol y modelo, ciego a `revealed_by`): adjudica qué golden
  cubre cada conjunto, con el mismo rasero en ambas condiciones.

Datos en `ablacion-voz/consolidado_k1.json` (recalcula la tabla) y `ablacion-voz/raw/` (hallazgos y veredictos crudos).

| revealed_by | n | recall CON voz | recall SIN voz | Δ |
|---|---|---|---|---|
| **user_only** | 12 | **0.83** | **0.33** | **−0.50** |
| both (control) | 20 | 0.90 | 0.85 | −0.05 |
| tech_only (control) | 13 | 0.85 | 1.00 | +0.15 |
| **global** | 45 | 0.87 | 0.76 | −0.11 |

**Confirma la predicción pre-registrada (ADR-007).** El recall de los problemas que solo revela
la voz **se desploma a la mitad** (0.83 → 0.33) al retirar el testimonio, mientras los controles
apenas se mueven: `both` −0.05 (la documentación los sostiene) y `tech_only` ni baja (el revisor
sin voz se concentra en lo documental). El efecto está localizado en `user_only`, que es
exactamente lo que la hipótesis predecía. El global cae solo −0.11 porque `user_only` es 12 de 45
— coherente con C3, que miraba el agregado y por eso no veía el efecto.

**Por qué el delta es defendible pese a hacerse con el propio modelo.** La circularidad (Claude
construyó los casos y aquí genera/juzga) infla el recall *absoluto*, pero es el **mismo generador
ciego en ambas condiciones**: la única diferencia es la presencia de la voz, así que el delta
−0.50 es atribuible al testimonio, no al modelo. Los controles planos (both, tech_only) lo
confirman: si fuera un artefacto del modelo, también habrían caído.

**Matiz honesto (cierre-cuentas).** Es el único caso donde `user_only` no cae (3 → 3): tiene un
*ex-programador* (fuente técnica) tan elocuente sobre el automation bias que hace de voz
sustituta. Mismo patrón que el conteo offline (robodebt/CONCERN con 0 `user_only` por estar
hiperdocumentados): **cuando un técnico "habla como usuario", la voz del usuario aporta menos**.
No lo esconde el resultado; lo explica.

**Salvedades de esta corrida (asistida).** Fue **asistida** con subagentes (roles separados), no con el
pipeline-código `comparar`, y **k=1**. Para cerrarlo se rehízo con el pipeline-código reproducible y k=3
(ver abajo), que confirma la dirección y recalibra la magnitud. Dos `user_only` no se detectaron ni con voz
(PO-09 formación, TO-10 pérdida de confianza): el generador ciego no los reportó aun teniendo la voz, y por
eso el recall con voz es 0.83 y no 1.00.

## Confirmación con el pipeline-código (k=3, 2026-07-02)

Se rehízo la corrida con el flujo **reproducible** (pipeline-código `comparar`, no subagentes), approach p3,
**generador Haiku / juez Sonnet independiente**, k=3, sobre los mismos 5 casos. Datos en
`docs/ablacion-voz/consolidado_k3.json` (+ raws por caso y condición).

| revealed_by | n | recall CON voz | recall SIN voz | Δ (sin − con) |
|---|---|---|---|---|
| **user_only** | 12 | **0.83** | **0.56** | **−0.28** |
| both (control) | 20 | 0.97 | 0.95 | −0.02 |
| tech_only (control) | 13 | 0.95 | 1.00 | +0.05 |
| **global** | 45 | 0.93 | 0.86 | −0.07 |

**La dirección se confirma; la magnitud se recalibra.** El efecto sigue **localizado en `user_only`** (los
controles no se mueven), pero cae **−0.28** en vez del −0.50 asistido. La diferencia es el **generador**: la
corrida asistida usaba Sonnet (conservador, que sin la voz no reportaba lo cognitivo); esta usa **Haiku, que
infiere de la documentación técnica** parte de esos problemas. Parte del −0.50 era artefacto del generador
conservador, no efecto puro del testimonio.

**Issue a issue** —en cuántas de las 3 corridas SIN voz sigue detectándose cada `user_only`— sale una lectura
más fina y más útil:

- **Caen a cero sin la voz (0/3), los puramente vivenciales:** la deferencia a la máquina (PO-01, *"llegué a
  dudar de mí mismo antes que del programa"*), la carga de la prueba invertida y vivida (TO-04, *"eres tú
  quien tiene que demostrar que no eres una defraudadora"*), la erosión de confianza (TO-10). Ningún generador
  los infiere de una ficha técnica: **solo la voz los revela**.
- **Haiku los recupera sin la voz (3/3), los cognitivo-estructurales:** automation bias donde la doc dice que
  se cierran alertas (AF-02, cc-04), fatiga donde dice alertas horarias (AF-04), falta de override donde no
  hay apelación (cc-03), expectativa de protección (AS-05). Ahí la voz aporta **grounding**, no
  descubrimiento: un modelo capaz los deduce de la estructura ya documentada.

**Conclusión refinada.** El testimonio es **imprescindible para la capa vivencial-emocional** (invisible en
cualquier documento; cae a cero sin la voz en ambas corridas) y **aporta grounding para la capa
cognitivo-estructural** (que un generador capaz infiere de la doc). Por eso la magnitud del efecto depende de
cuán inferente sea el generador —de ahí el −0.50 con Sonnet frente al −0.28 con Haiku— pero el diferencial del
testimonio se sostiene medido con método independiente, y su núcleo duro (lo que la persona *vive* y ninguna
ficha declara) es exactamente lo que desaparece sin ella.
