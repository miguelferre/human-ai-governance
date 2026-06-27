# Plantilla 01 — Ficha del sistema

**Quién la rellena:** responsable técnico, data scientist o responsable de
producto/implantación.
**Tiempo aproximado:** 20–30 minutos.
**Cómo:** escribe tu respuesta debajo de cada pregunta, en el espacio `✍️`. Si
algo no aplica o no lo sabes, escríbelo (también es información útil).

> Recuerda: describe **cómo es** el sistema, no a sus usuarios reales. Sin datos
> personales (ver privacidad en el README).

---

## 0. Identificación

- **Nombre del sistema:**
  ✍️
- **Dominio / para qué se usa:**
  ✍️
- **Estado:** (idea / piloto / producción / retirado)
  ✍️
- **¿A quién va dirigido?** (qué perfil lo usa para decidir)
  ✍️

🎯 *Para qué:* situar el sistema y a su usuario. Sin esto, cualquier hallazgo
sería genérico.

---

## 1. Qué hace y qué NO hace

- **¿Qué tarea resuelve el modelo?** (en una o dos frases)
  ✍️
- **¿Qué produce exactamente?** (una puntuación, una categoría, un texto, una recomendación…)
  ✍️
- **¿El sistema decide o sugiere?** ¿La persona puede no seguirlo?
  ✍️
- **¿Qué cosas NO hace, aunque alguien pudiera esperar que sí?**
  ✍️

🎯 *Para qué:* comprobar si está claro el alcance y el reparto de responsabilidad
(persona vs sistema). Es la raíz de muchos malentendidos.

> Ejemplo: "Sugiere prioridad alta/media/baja de un ticket. No cierra ni asigna el
> ticket; el agente decide. No detecta tickets duplicados, aunque a veces se cree
> que sí."

---

## 2. Rendimiento y límites

- **¿Cómo de bien funciona?** (métricas que tengas: precisión, etc.)
  ✍️
- **¿Dónde falla más o es menos fiable?** (tipos de caso, poblaciones, situaciones)
  ✍️
- **¿Se mide el rendimiento por subgrupos?** (por tipo de caso, edad, sexo, idioma…)
  ✍️

🎯 *Para qué:* ver si los límites del sistema se conocen y, después, si se le
comunican a la persona que lo usa.

> Ejemplo: "Precisión global 0,82. Peor en tickets en catalán. No medimos
> rendimiento por categoría de ticket."

---

## 3. Cómo se presenta el resultado al usuario

- **¿Dónde y cómo aparece el resultado?** (pantalla, campo prerrellenado, aviso, correo…)
  ✍️
- **¿Qué ve la persona exactamente?** Describe la pantalla o el mensaje.
  ✍️
- **¿Aparece junto al resultado algún contexto** (factores, datos del caso) o solo el resultado a secas?
  ✍️

🎯 *Para qué:* el "cómo se muestra" condiciona enormemente cómo se decide. Un
número solo, prerrellenado, empuja a aceptarlo sin pensar.

---

## 4. Confianza e incertidumbre

- **¿Se muestra cuándo el sistema está poco seguro?** ¿Cómo? (un %, un color, un texto…)
  ✍️
- **¿Todas las salidas se presentan igual de seguras**, o se distingue lo dudoso?
  ✍️

🎯 *Para qué:* detectar riesgo de **exceso de confianza** (automation bias): si
todo se ve igual de firme, la persona no sabe cuándo dudar.

---

## 5. Explicación del "por qué"

- **¿La persona puede saber por qué el sistema propone eso?** ¿Cómo lo ve?
  ✍️
- Si hay explicación, **¿es útil para decidir** o es técnica/decorativa?
  ✍️

🎯 *Para qué:* sin un "por qué" accesible, la confianza no se puede calibrar.

---

## 6. Cuando la persona no está de acuerdo (override / corrección)

Este bloque es de los más importantes.

- **¿Puede la persona cambiar, anular o ignorar la propuesta?** ¿Cómo de fácil es?
  ✍️
- **Cuando lo cambia, ¿se registra ese cambio en algún sitio?**
  ✍️
- **¿Se registra el motivo del cambio?** ¿De forma libre o estructurada (categorías)?
  ✍️
- **¿Para qué se usa ese registro?** (supervisión, reentrenamiento, nada…) ¿Lo sabe la persona?
  ✍️

🎯 *Para qué:* el override mal capturado (o capturado pero que no se usa, o sin
motivo) es un anti-patrón clásico y silencioso.

> Ejemplo: "Puede cambiar la prioridad con un desplegable. Se guarda el cambio,
> pero no el motivo. Asumimos que sirve para reentrenar, aunque hoy nadie lo revisa."

---

## 7. Descarte, momento y alertas

- **¿Puede ignorar o cerrar la sugerencia fácilmente,** o reaparece / molesta?
  ✍️
- **¿El sistema interrumpe?** ¿En qué momento del flujo aparece?
  ✍️
- **¿Cuántos avisos/alertas genera?** ¿Hay riesgo de saturación (fatiga de alerta)?
  ✍️

🎯 *Para qué:* mala temporización y exceso de alertas hacen que la gente acabe
ignorándolo todo, incluido lo importante.

---

## 8. Primer contacto (onboarding)

- **¿Cómo aprende la persona a usar el sistema y a entender qué hace?** (formación, texto inicial, nada…)
  ✍️
- **¿Se le explican las limitaciones al principio?**
  ✍️

🎯 *Para qué:* un buen arranque fija expectativas correctas; su ausencia genera
modelos mentales equivocados.

---

## 9. Ante datos insuficientes o fallo

- **¿Qué hace el sistema si no tiene datos suficientes o no está seguro?** (¿se abstiene, avisa, igualmente propone algo?)
  ✍️
- **Si falla o no puede actuar, ¿qué ve la persona?** (mensaje claro / error técnico / nada)
  ✍️

🎯 *Para qué:* ver si el sistema "degrada con elegancia" o falla en silencio /
con confianza injustificada.

---

## 10. Supervisión y subgrupos

- **¿Quién vigila que el sistema siga funcionando bien una vez desplegado?**
  ✍️
- **¿Esa supervisión es automática o manual?** ¿Cada cuánto?
  ✍️
- **¿Se vigila que no perjudique a algún subgrupo** más que a otros?
  ✍️

🎯 *Para qué:* la supervisión manual o inexistente de subgrupos es un punto débil
frecuente y difícil de ver desde dentro.

---

## 11. Cambios y controles

- **Cuando el sistema cambia de comportamiento (actualización), ¿se avisa a los usuarios?**
  ✍️
- **¿La persona puede configurar algo** (umbrales, qué alertas recibe, activar/desactivar)?
  ✍️

🎯 *Para qué:* cambios silenciosos rompen la confianza; la falta de controles deja
a la persona sin margen.

---

## 12. Feedback

- **¿Existe alguna forma de que la persona dé su opinión sobre una propuesta?** ¿Con qué detalle?
  ✍️

🎯 *Para qué:* sin canales de feedback (o demasiado gruesos), el sistema no mejora
con el uso.

---

## Lo que tú ya sospechas (opcional, sepáralo del resto)

Si tienes una intuición de qué falla en la interacción, escríbela **aquí**, no
arriba. Nos sirve para contrastar, pero la queremos separada de la descripción.

✍️
