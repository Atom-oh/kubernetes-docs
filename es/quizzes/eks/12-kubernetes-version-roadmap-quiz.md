# Cuestionario sobre las funciones y la hoja de ruta de versiones de Kubernetes

> **Última actualización**: 12 de septiembre de 2026

Consulta el [capítulo fuente](../../eks/12-kubernetes-version-roadmap.md) para ver los requisitos previos específicos de cada versión y los límites de la evidencia de auditoría.

1. ¿Cuál es la cadencia de versiones menores de Kubernetes?

   - A) Una versión de funciones al año
   - B) Aproximadamente tres versiones menores al año, separadas por unos cuatro meses
   - C) Versiones menores mensuales
   - D) Un calendario fijo alineado con las conferencias de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aproximadamente tres versiones menores al año, separadas por unos cuatro meses**

Las versiones menores upstream suelen publicarse unas tres veces al año; las versiones de parche siguen otra cadencia. La política upstream de soporte para ramas de parches dura aproximadamente 14 meses (12 de mantenimiento normal y 2 de mantenimiento adicional). El soporte estándar de EKS también dura 14 meses, pero empieza cuando la versión está disponible en EKS; no hay que confundir ambos calendarios.

</details>

---

2. ¿En qué se diferencian las tarifas de soporte estándar y extendido de versiones de EKS?

   - A) El soporte estándar es gratuito
   - B) Estándar: 14 meses a $0.10 por clúster-hora; extendido: 12 meses más a $0.60 por clúster-hora en total
   - C) El soporte extendido cubre para siempre todas las versiones antiguas
   - D) El soporte extendido no incluye parches de seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Estándar: 14 meses a $0.10 por clúster-hora; extendido: 12 meses más a $0.60 por clúster-hora en total**

Estas son tarifas de soporte de versión, no el costo total de cómputo, almacenamiento y redes. EXTENDED es la política de actualización predeterminada; STANDARD puede provocar una actualización automática cuando termina el soporte estándar. El soporte extendido también incluye los parches de seguridad pertinentes. Consulta el calendario de versiones actual y considera la fecha real de fin del soporte y el riesgo de las cargas de trabajo.

</details>

---

3. ¿Cuándo se volvieron estables los sidecars nativos?

   - A) 1.28
   - B) 1.31
   - C) 1.33
   - D) 1.35

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 1.33**

La progresión fue alfa en 1.28, beta en 1.29 y estable en 1.33. Los contenedores init reiniciables usan `restartPolicy: Always`. El orden de inicio depende del estado `started` y de `startupProbe`; el apagado gradual usa el presupuesto de terminación compartido del Pod. Llegar a GA no garantiza que todos los contenedores auxiliares terminen de forma ordenada ni que una imagen de proxy esté configurada correctamente.

</details>

---

4. ¿Qué permite el redimensionamiento in situ de contenedores y cuándo se volvió estable?

   - A) Escalar réplicas; 1.30
   - B) Cambiar la asignación de CPU y memoria de un Pod existente; 1.35, con restricciones de reinicio y del entorno de ejecución
   - C) Ampliar PVC; 1.31
   - D) Actualizar una imagen sin reiniciar su proceso; 1.34

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cambiar la asignación de CPU y memoria de un Pod existente; 1.35, con restricciones de reinicio y del entorno de ejecución**

La función pasó por alfa en 1.27, beta en 1.33 y llegó a estable en 1.35. `resizePolicy` del contenedor controla el comportamiento de reinicio, y los cambios de recursos pueden quedar pendientes o ser inviables. Que PATCH se haya aceptado o que `containerID` no haya cambiado no demuestra que se aplicara el cambio en cgroups ni que no hubiera disrupción. Compara los recursos deseados y los observados, la generación y las condiciones. Los modos de VPA tienen sus propias versiones y gates.

</details>

---

5. ¿Qué afirmación describe correctamente DRA en Kubernetes 1.31?

   - A) DRA clásico fue reemplazado por Device Plugins v2
   - B) DRA seguía en alfa; las API estructuradas evolucionaban y la asignación clásica seguía detrás de una gate independiente
   - C) DRA ya estaba en GA
   - D) La sintaxis estable de solicitudes `v1` era idéntica a la de todas las API alfa anteriores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) DRA seguía en alfa; las API estructuradas evolucionaban y la asignación clásica seguía detrás de una gate independiente**

El lanzamiento y el código de 1.31 conservan `DRAControlPlaneController` como una gate alfa deshabilitada. Se elimina en 1.32; el núcleo de DRA pasa a beta en 1.32 y a estable en 1.34. Por eso era incorrecta la respuesta del cuestionario anterior que afirmaba que se había eliminado en 1.31. Las solicitudes actuales de `v1` usan `exactly`; hay que verificar los controladores, ResourceSlices y atributos reales.

</details>

---

6. ¿Qué función se volvió estable en 1.30 para validar la admisión nativa mediante CEL?

   - A) OPA Gatekeeper v4
   - B) Un CRD de parámetros obligatorio
   - C) ValidatingAdmissionPolicy
   - D) Todos los mecanismos de admisión mutante

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) ValidatingAdmissionPolicy**

ValidatingAdmissionPolicy usa una política y una vinculación, con objetos de parámetros opcionales que no tienen por qué ser CRD. Para la lógica apropiada, evita depender de un webhook de validación externo, pero los errores o `failurePolicy` aún pueden afectar las solicitudes. Limita el alcance de la vinculación y distingue entre Audit y Deny. MAP es una función distinta de mutación que llegó a estable en 1.36.

</details>

---

7. Según el historial de versiones verificado, ¿qué es KYAML?

   - A) Un validador del servidor de API que rechaza todos los anchors YAML normales
   - B) Un formato de salida de kubectl: alfa en 1.34, beta en 1.35–1.36 y estable en 1.37
   - C) Una función nueva del servidor de EKS que se habilita mediante una solicitud de soporte
   - D) Un requisito para convertir todos los manifiestos de entrada a YAML 1.2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un formato de salida de kubectl: alfa en 1.34, beta en 1.35–1.36 y estable en 1.37**

KYAML corresponde a KEP-5295. Las pruebas nativas con kubectl 1.36.2 aceptaron anchors YAML normales y generaron KYAML. `KUBECTL_KYAML=false` deshabilitó ese formateador de salida, mientras que la entrada KYAML siguió analizándose al solicitar salida JSON. El formato es distinto de la validación de esquema y de admisión. Upstream 1.37 ya se había publicado a la fecha de esta revisión; eso no implica que EKS 1.37 estuviera disponible.

</details>

---

8. ¿Qué enfoque de planificación de actualizaciones de EKS es apropiado?

   - A) Omitir versiones menores para ahorrar tiempo
   - B) Ensayar cada paso de versión menor, verificar la compatibilidad y quién administra cada componente, y preparar la recuperación
   - C) Considerar que el código de salida 0 de un escáner es una prueba completa
   - D) Actualizar siempre todos los complementos después del plano de control en un orden fijo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ensayar cada paso de versión menor, verificar la compatibilidad y quién administra cada componente, y preparar la recuperación**

Usa el calendario de soporte vigente, la evidencia de manifiestos y del uso por los clientes, la compatibilidad exacta de los complementos y la secuencia específica para el modo de cómputo. Algunos requisitos previos se deben completar antes de actualizar el plano de control. Sigue el ID real de actualización; valida la preparación de las cargas de trabajo y los datos, y distingue entre el redimensionamiento de Pods, el reemplazo de nodos y el escalado. La reversión nativa de EKS está sujeta a condiciones y debe iniciarse en un plazo de siete días después de una actualización in situ completada; no revierte bases de datos ni permite omitir todos los controles.

</details>

---
