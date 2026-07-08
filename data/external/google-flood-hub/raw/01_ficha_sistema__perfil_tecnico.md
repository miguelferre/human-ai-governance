# Template 01: System card

> Neutralizado a partir de fuentes públicas citadas (ver 00_LEEME_enfoque.md). Describe el sistema, no
> a personas reales.

---

## 0. Identification

- **System name:**
  ✍️ Google Flood Hub
  (sistema de previsión y alerta temprana de inundaciones de Google/DeepMind).
- **Domain / what it is used for:**
  ✍️ Alerta temprana de inundaciones fluviales.
  Da a organizaciones de acción anticipatoria, autoridades y población un pronóstico de crecida de ríos
  con varios días de antelación para preparar y decidir.
- **Status:** (idea / pilot / production / retired)
  ✍️ En producción. Operativo en más de 80 países (con expansión declarada hacia ~100, y hasta ~150 con
  "virtual gauges"), gratis y sin registro, con alcance declarado de unos 700 millones de personas.
- **Who is it aimed at?** (which profile uses it to decide)
  ✍️ Dos perfiles muy distintos con el mismo dato: (a) quien decide de forma profesional (oficiales de
  programas de acción anticipatoria, ONG, protección civil, gobiernos) que lo usan para disparar
  actuaciones; y (b) la población en zonas de riesgo, que recibe el aviso para protegerse.

---

## 1. What it does and what it does NOT do

- **What task does the model solve?**
  ✍️ Predice la crecida de los ríos: un modelo hidrológico estima el caudal y otro estima qué zonas se
  inundarán y a qué altura, con horizonte de hasta 7 días.
- **What exactly does it produce?**
  ✍️ Un nivel de severidad por tramo de río (con código de color), un hidrograma con la evolución
  prevista del caudal, y mapas de zonas inundables. Las alertas se difunden como avisos legibles.
- **Does the system decide or suggest?** Can the person choose not to follow it?
  ✍️ Informa; no decide ni ejecuta ninguna acción. Quien recibe el pronóstico decide qué hacer con él.
  La documentación pide expresamente no usarlo como fuente única en una emergencia.
- **What does it NOT do, even if someone might expect it to?**
  ✍️ No cubre inundaciones repentinas (flash floods) ni costeras, solo fluviales. No sustituye a las
  autoridades locales. En algunas regiones solo comparte el dato hidrológico, sin mapa de inundación,
  porque el modelo de inundación no muestra patrones claros allí.

---

## 2. Performance and limits

- **How well does it work?**
  ✍️ Se comunica con cifras globales de cobertura y de fiabilidad (el modelo publicado da avisos fiables
  hasta ~5-7 días para eventos extremos). El modelo es de aprendizaje automático (redes LSTM), entrenado
  con datos de unas 5.680 estaciones de aforo.
- **Where does it fail most or is least reliable?**
  ✍️ Opera en muchas cuencas **sin estación de aforo**, generalizando por transferencia de patrones. La
  fiabilidad varía de un sitio a otro y, según el propio trabajo publicado, las correlaciones entre los
  atributos de la cuenca y las puntuaciones de fiabilidad son en general bajas: es difícil saber de
  antemano dónde acertará mejor o peor. Una evaluación independiente (Li et al. 2026, metodológicamente
  discutida) cuestiona el acierto en los eventos más extremos.
- **Is performance measured by subgroup?**
  ✍️ El sistema distingue tramos de "confianza alta" y "confianza baja" según se pudiera validar el
  modelo con datos. No hay una medida de fiabilidad por región o comunidad que se traslade al aviso.

---

## 3. How the result is presented to the user

- **Where and how does the result appear?**
  ✍️ En el mapa de Flood Hub y, difundido, en el buscador de Google, en Maps y como notificaciones de
  Android (y avisos tipo SOS). En India y Bangladesh los avisos se ofrecen en 9 idiomas locales.
- **What exactly does the person see?** Describe the screen or the message.
  ✍️ Un mapa con el río coloreado en cuatro niveles del amarillo al rojo: Normal, Warning, Danger y
  Extreme, más "No data". Cada nivel corresponde a un periodo de retorno (aproximadamente evento de 2, 5
  y 20 años). Al abrir un tramo se ve un hidrograma con la tendencia pasada y el pronóstico, y los
  valores de agua que disparan cada nivel. Hay además una capa de probabilidad de inundación (azules más
  oscuros = más probable) y otra de inundación histórica.
- **Does any context appear alongside the result** or just the result on its own?
  ✍️ Aparece el hidrograma y los umbrales del tramo. El aviso difundido a la población (buscador, Maps,
  notificación) llega en forma más resumida que la vista completa del mapa.

---

## 4. Confidence and uncertainty

- **Is it shown when the system is unsure?** How?
  ✍️ Internamente el modelo es probabilístico: predice una distribución del caudal y muestra su valor
  central (la mediana). De cara al usuario, la incertidumbre se resume en una etiqueta de tramo de
  "confianza alta" o "confianza baja" y en una capa opcional de cobertura. Junto al valor pronosticado
  no se muestra una banda de incertidumbre ni una probabilidad numérica.
- **Are all outputs presented as equally confident**, or is the doubtful set apart?
  ✍️ El pronóstico se presenta como una única línea en el hidrograma y una categoría de severidad. La
  distinción de confianza alta/baja está en el mapa como una capa/opción, no pegada a cada aviso que
  recibe la persona.

---

## 5. The "why"

- **Can the person know why the system proposes what it proposes?** How?
  ✍️ El panel del tramo muestra el hidrograma y los umbrales que disparan cada nivel. No hay una
  explicación accesible de por qué el modelo predice que se cruzará un umbral en un evento concreto.
- **Is the explanation useful for deciding** or technical/decorative?
  ✍️ Lo que se ofrece es el dato (curva y umbrales), no una justificación del pronóstico que ayude a
  decidir cuánta confianza darle a ese aviso en particular.

---

## 6. When the person disagrees (override / correction)

- **Can the person change, overrule, or ignore the proposal?** How easy?
  ✍️ No aplica en el sentido clásico: no es una sugerencia que el usuario edite dentro del sistema, es un
  pronóstico. Quien decide actúa (o no) fuera del sistema. El usuario no "corrige" el pronóstico.
- **When they change it, is that change recorded anywhere?**
  ✍️ No hay registro dentro del sistema de la decisión que toma el usuario ni de su resultado.
- **Is the reason for the change recorded?**
  ✍️ No aplica: no se captura la acción del usuario.
- **What is that record used for?** Does the person know?
  ✍️ No existe ese registro de vuelta hacia el sistema.

---

## 7. Dismissal, timing, and alerts

- **Can they easily ignore or close the suggestion,** or does it reappear / nag?
  ✍️ Los avisos llegan por notificación, buscador o mapa, y hay suscripción por correo. No hay un ajuste
  por usuario para descartar o afinar qué avisos se reciben.
- **Does the system interrupt?** At what point?
  ✍️ El aviso aparece cuando el pronóstico cruza un umbral, con hasta varios días de antelación. Los
  umbrales bajos (evento de 2 años en "warning") implican avisos relativamente frecuentes.
- **How many alerts/warnings does it generate?** Saturation risk?
  ✍️ Depende del río y de la temporada; con umbrales bajos y varios días de antelación, un mismo episodio
  puede generar avisos repetidos. No hay control por usuario para modular esa frecuencia.

---

## 8. First contact (onboarding)

- **How does the person learn to use the system?**
  ✍️ No hay formación: el mapa es de acceso libre y hay páginas de ayuda que explican los niveles y las
  capas. Los dos perfiles (profesional y población) llegan al mismo dato con preparación muy distinta.
- **Are the limitations explained up front?**
  ✍️ Las páginas de ayuda y el mapa incluyen avisos: que es informativo, un trabajo en curso, y que no
  debe usarse como fuente única porque las condiciones reales pueden variar. Esos avisos viven en la
  ayuda y el mapa, no necesariamente en el aviso resumido que llega por notificación.

---

## 9. On insufficient data or failure

- **What does the system do if it lacks enough data or is unsure?**
  ✍️ Marca tramos como "No data" o de baja confianza, y en algunas regiones solo publica el dato
  hidrológico sin mapa de inundación. Un factor limitante declarado es la disponibilidad de registros
  históricos de caudal. Aun así, donde publica, emite una categoría de severidad.
- **If it fails or cannot act, what does the person see?**
  ✍️ Ausencia de dato o de mapa en ese tramo, más los avisos generales de "no fuente única". No hay un
  mensaje que explique, para un tramo concreto, por qué la señal es débil allí.

---

## 10. Oversight and subgroups

- **Who watches that the system keeps working well once deployed?**
  ✍️ El equipo de Google mantiene y actualiza los modelos y publica evaluaciones. Se apoya en partners
  (ONG, cruces rojas, agencias) que operacionalizan los pronósticos sobre el terreno.
- **Is that oversight automatic or manual?** How often?
  ✍️ El sistema clasifica tramos por confianza de forma automática. La verificación local de si el aviso
  correspondió con lo ocurrido queda del lado de los partners, caso por caso.
- **Is it watched that it does not harm some subgroup more than others?**
  ✍️ La fiabilidad no es predecible localmente y no hay una medida por comunidad que acompañe al aviso;
  las poblaciones peor conectadas son también a las que peor llega el aviso.

---

## 11. Changes and controls

- **When the system changes behavior (an update), are users notified?**
  ✍️ Los modelos se actualizan (por ejemplo, ampliación de cobertura y de horizonte entre versiones). Ese
  cambio se comunica en blogs y notas técnicas, no necesariamente en la superficie del aviso al usuario.
- **Can the person configure anything?**
  ✍️ Los umbrales de severidad están fijados globalmente (evento de ~2/5/20 años), salvo en India,
  Bangladesh y Brasil, donde los fija la agencia gubernamental. El usuario no puede definir su propio
  umbral operativo; para actuar, cada organización traduce a mano el nivel del sistema a su disparador
  (por ejemplo, un porcentaje del área o del pueblo pronosticado como inundable) cruzándolo con gauges
  oficiales y observación local.

---

## 12. Feedback

- **Is there any way for the person to give their opinion on a proposal?** With what detail?
  ✍️ Hay suscripción por correo para recibir avisos y una opción de confianza en el mapa, pero son de un
  solo sentido (sistema → usuario). No se ha encontrado un canal por el que quien decide o quien recibe
  el aviso reporte al sistema si fue acertado o una falsa alarma.

---

## What you already suspect (optional, keep it apart from the rest)

✍️
