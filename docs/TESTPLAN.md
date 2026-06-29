# Plan de pruebas — validez y overfitting de los resultados

Motivado por una pregunta de Miguel: ¿P3 (el pipeline) parece tan bueno por **overfitting**?
Este documento registra la batería de pruebas para distinguir señal real de artefacto, y
para evaluar si esto sirve como **producto** (no solo como ganador de un benchmark de un caso).

## Riesgos de overfitting identificados

- **R-A. Bloques de P3 diseñados a mano** conociendo guidelines/caso → ventaja que no generaliza.
- **R-B. Cantidad, no calidad:** P3 emite ~25 hallazgos vs ~6 de B1 → más tiros a emparejar.
- **R-C. n=1 caso:** todo (dossier, golden, bloques, prompts, juez) se afinó alrededor del caso clínico.
- **R-D. Juez algo indulgente / artefactos del corrector** (ver hallazgo en B2 abajo).
- **R-E. Golden y dossier co-evolucionados** con el equipo evaluador.

## Resultado base a validar (v2, k=1)

B1 (prompt único) 0.38  <  A4 (agente) 0.67  <  P3 (pipeline fijo) 0.80  (todos precisión ~1.00).
Lectura provisional: el pipeline gana; el agente NO se justifica. Falta validar contra los riesgos.

## Batería de pruebas

### A. ¿Generaliza? (lo más importante)
- **A1 — Casos externos held-out.** Buscar en literatura/web 2-3 casos reales con problemas de
  interacción DOCUMENTADOS por fuentes independientes (golden objetivo, no nuestra interpretación);
  construir dossier + golden y correr B1/P3/A4. Es LA prueba de overfitting. _Estado: BUSCANDO casos
  (agente de investigación en curso)._
- **A2 — Bloques alternativos.** Re-correr P3 con una agrupación neutral (4 fases HAX + capítulos
  PAIR, sin mano). Si P3 aguanta, la ventaja es la *descomposición*, no mis bloques. _Estado: pendiente._

### B. ¿Son reales los números?
- **B1 — ¿Estructura o cantidad?** Un "B1-exhaustivo" (prompt único pidiendo MUCHOS hallazgos, una
  pasada). Si iguala a P3, la ventaja era cantidad; si no, la estructura aporta. _Estado: pendiente._
- **B2 — Adjudicación humana de P3.** _Estado: HECHO (2026-06-29)._
  - **Resultado:** los 12 matches distintos son legítimos → **0.80 real, no inflado**.
  - **Hallazgo importante:** P3 está **infravalorado**. De los 3 "perdidos", GI-13 (onboarding) y
    GI-06 (automation bias) **sí se encontraron**, pero el corrector no los emparejó porque el
    hallazgo citó una guideline distinta de la del golden (sin solape → no candidato). **P3 real
    ≈ 14/15.**
  - **Bug derivado (afecta a todos por igual):** el filtro por guideline del corrector produce
    FALSOS FALLOS cuando el generador cita la guideline "equivocada". Mitigación posible: ampliar
    candidatos por grupo/capítulo o por similitud semántica, no solo por id exacto. Sube el recall
    de todos los approaches; la comparación relativa se mantiene.

### C. ¿Es buen producto (no solo gana el benchmark)?
- **C1 — Falsos positivos en un sistema "bueno".** Dar a P3 el dossier de un sistema bien diseñado
  (pocos problemas). ¿Se calla o inventa para llenar bloques? Un auditor que siempre encuentra 25
  fallos es inútil. _Estado: pendiente (requiere dossier sintético de sistema "bueno")._
- **C2 — Robustez al formato de entrada.** Variar el dossier (menos detalle, fraseo distinto) y ver
  si los hallazgos aguantan. _Estado: pendiente._
- **C3 — El nicho del agente.** A4 vs P3 con **entrada incompleta** (info repartida/ausente): único
  régimen donde la autonomía debería ganar. _Estado: pendiente._

### Confirmación con varianza
- **k=3** de los approaches clave (P3 y A4 al menos) una vez cerradas las pruebas anteriores, para
  aplicar la regla `beats` formalmente. _Estado: pendiente (coste alto en máquina local lenta)._

## Estado a 2026-06-29 (ejecutado en NUBE Claude; síntesis en RESULTADOS.md)

- **B2** adjudicación humana de P3: ✅ HECHO (0.80 real, infravalorado; bug del corrector documentado).
- **A1** generalización: ✅ HECHO con 2 held-out (HireVue no clínico, Epic clínico distinto) → **NO era overfitting** (patrones reproducidos). Faltan 3 held-out documentados sin construir (moderación, aviación, COMPAS).
- **B1** estructura vs cantidad: ✅ respondido por el mapa — la estructura aporta **reliability** en casos difíciles (B1 inestable, una corrida a 0), no solo cantidad; en casos fáciles B1≈P3. (El approach `b1x` quedó implementado; su corrida local se abortó por lentitud.)
- **C1** falsos positivos en sistema bueno: ✅ HECHO — B1/P3/A4 devuelven **0 hallazgos**; no inventan. La verbosidad de P3 es redundancia, no fabricación.
- **A2** bloques alternativos, **C2** robustez de entrada, **C3** nicho del agente (entrada incompleta): ⬜ pendientes (refinamiento).
- **k=3 confirmación**: ✅ hecho en nube (todas las corridas de la tabla son k=3).

**Conclusión validada en [RESULTADOS.md](RESULTADOS.md): mapa condicional** (la complejidad que paga depende de dificultad×modelo), no un ganador único.

## Notas de método
- Máquina local lenta (~10 min/llamada cuando se usa el equipo) → runs en segundo plano con watchdog
  y checkpoint de generación. Suspensión pausa runs (desactivar o vigilar).
- Todo crudo se guarda en `runs/` (gitignored). Material del caso en `data/golden/` (privado).
