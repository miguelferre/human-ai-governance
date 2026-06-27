# ADR-003: Manejo de datos y material clinico (PHI)

- **Estado:** Aceptada
- **Fecha:** 2026-06-27

## Contexto

El caso de validacion primaria es clinico y privado. El sistema, a partir de F2,
llama a un LLM en la nube (Anthropic). **Una llamada al LLM envia los datos fuera**
del equipo: pueden quedar en logs o caches del proveedor aunque luego se borren.
Esto es incompatible con enviar datos de pacientes sin tratar.

## Decision

- El material clinico real y el golden set viven bajo `data/golden/` y
  `data/private/`, **gitignored**. Nunca se versionan ni se publican.
- **De-identificacion previa obligatoria**: antes de cualquier llamada al LLM con
  datos del caso, el `Dossier` debe estar libre de PHI (sin identificadores de
  paciente). El dossier describe el **sistema y su interaccion**, no pacientes
  concretos; esto facilita cumplirlo.
- El usuario aporta el material necesario; **no se busca fuera** (`.gitignore` y
  esta nota lo dejan explicito).
- Los resultados crudos de corridas (`runs/`) tambien se gitignoran por si arrastran
  fragmentos del dossier.

## Consecuencias

- Si en el futuro se requiere procesar PHI sin de-identificar, habria que revisar
  el despliegue (p. ej. LLM on-prem o acuerdo de tratamiento de datos) en un ADR nuevo.
- El arnes de evaluacion funciona igual con un dossier de-identificado: la capa de
  interaccion no necesita datos de paciente para ser auditada.
