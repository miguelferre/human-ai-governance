# Resultados — casos held-out con testimonio de usuario real

Validación adicional (2026-06-30) sobre **7 casos reales con testimonio de usuario documentado**,
en 6 sectores, que complementa el experimento principal ([RESULTADOS.md](RESULTADOS.md)). Motivación:
los held-out previos eran reconstrucciones desde literatura *sin* voz de usuario primaria; el
diferencial del producto es justamente incorporar el **testimonio de quien usa el sistema**, así que
hacía falta probarlo sobre casos que lo tuvieran.

**Cómo se midió.** Generador (el revisor) = modelo barato (Haiku), **ciego**: solo ve el dossier,
nunca el golden. Adjudicación por mapeo transparente golden↔hallazgo. Los dossiers y goldens de cada
caso viven en `data/external/<caso>/`.

> **Nota honesta de método.** Esta tanda se ejecutó de forma **asistida** (con subagentes), no con el
> pipeline-código `comparar`. El número reproducible con juez LLM independiente queda pendiente de la
> corrida-código (ver [TAREAS.md](TAREAS.md)). Por eso el resultado que de verdad cuenta es el **test
> duro** de más abajo, diseñado para eliminar el sesgo de que el mismo motor construya y detecte.

## Los 6 casos construidos para la prueba

| Caso | Sector | Golden | Recall | Precisión |
|---|---|---|---|---|
| Alert fatigue en alertas del EHR | Sanidad | 8 | 8/8 | alta · +5 descubrimientos |
| CONCERN (CDS predictivo ML) | Sanidad | 9 | 8/9 (+1 parcial) | alta |
| Asiana 214 (autothrottle, cabina) | Aviación | 9 | 9/9 | alta |
| Cierre algorítmico de cuentas bancarias | Finanzas | 9 | 9/9 | alta |
| Post Office Horizon | Operador (UK) | 9 | 9/9 | alta |
| Toeslagenaffaire (subsidios) | Admin. pública (NL) | 10 | 9/10 (+1 parcial) | alta |
| **Total** | **5 sectores** | **54** | **52/54 claros + 2 parciales ≈ 0.96–1.00** | ~0.9–1.0 |

Haiku bastó en los 6; no hizo falta un modelo más caro.

**Salvedad — circularidad.** En estos 6, el mismo tipo de modelo (Claude) construyó los dossiers+goldens
*y* generó los hallazgos → el generador encuentra con facilidad lo que otro modelo anotó. Esto **infla el
recall**. Para medirlo, el test duro de abajo rompe ese sesgo.

## Test duro — Robodebt (circularidad rota)

Diseño con **manos separadas**:
- **Golden** ← derivado de la **Royal Commission into the Robodebt Scheme** (informe Holmes 2023),
  Commonwealth Ombudsman y Victoria Legal Aid, por un agente que **no vio el dossier**.
- **Dossier** ← hechos crudos + testimonios reales literales (Masterton, Amato, Colleen Taylor, Holmes),
  por otro agente que **no vio el golden** y con prohibición explícita de etiquetar problemas.
- Generador Haiku ciego · adjudicación transparente.

Rompe los dos sesgos que más inflaban: golden propio + dossier curado.

**Recall = 9/10 = 0.90.** El único miss (las anulaciones del tribunal AAT que el esquema ignoró) es
porque **esa información no estaba en el dossier crudo** — el revisor no podía verla y **no la inventó**.
La caída no es ceguera, es falta de dato.

| Fallo señalado por la Royal Commission | Recuperado |
|---|---|
| Aviso sin explicar el cálculo | ✅ |
| Teléfono omitido deliberadamente | ✅ |
| Canal solo-online forzado | ✅ |
| Carga de la prueba invertida | ✅ |
| Sin revisión humana previa | ✅ |
| Deuda ficticia por promediado de ingresos | ✅ |
| Documentación de 5 años imposible de aportar | ✅ |
| Deuda sin comunicar incertidumbre | ✅ |
| Ignorar las anulaciones del tribunal (AAT) | ❌ (no estaba en el dossier) |
| Tono intimidatorio / trauma | ✅ |

## Lectura

Rompiendo la circularidad —golden humano externo + dossier en bruto + manos separadas—, el revisor
recupera **9/10 de los fallos que un órgano humano independiente identificó**, desde hechos crudos y
testimonios reales, con el modelo más barato, **sin inventar**. La circularidad inflaba **poco**
(~0.08: de ~0.98 a 0.90).

**Limitaciones que quedan** (en [TAREAS.md](TAREAS.md), no como respaldo sino como trabajo planificado):
sigue siendo Claude el generador (no se elimina del todo "el modelo piensa como el modelo"); es **un**
caso duro (n=1); y falta la corrida-código con juez LLM independiente para el número reproducible.
