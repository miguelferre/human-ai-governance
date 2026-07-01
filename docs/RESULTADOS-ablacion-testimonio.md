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

## Lo que falta para cerrarlo (necesita API)

Este conteo mide el **techo** (cuántos problemas dependen de la voz), no el **efecto** (cuánto
cae el recall del revisor al quitarle la voz). El cierre es una corrida con el motor sobre cada
dossier **con voz** y **sin voz** (retirando las fuentes `end_user`, `ablation.without_voice`) y
comparar el recall del subconjunto `user_only`. El andamiaje está listo:

```
uv run python scripts/ablacion_report.py compare \
    --golden data/external/asiana-214/answer_key.json \
    --voz runs/asiana_voz_k3.json --sin-voz runs/asiana_sinvoz_k3.json --approach p3
```

**Predicción pre-registrada (ADR-007):** el recall de `user_only` debería desplomarse sin voz
(el revisor no puede ver lo que ninguna fuente le cuenta). Si además el recall de `both` NO cae,
quedaría demostrado que el testimonio **descubre** la capa cognitiva y **refuerza** el resto.
Pendiente de reponer la API key (ver [TAREAS.md](TAREAS.md)).
