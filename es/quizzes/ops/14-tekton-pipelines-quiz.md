# Cuestionario de Tekton Pipelines

1. ¿Cuál describe correctamente Task, TaskRun y Workspace?
   - A) La definición de una Task ya es un Pod en ejecución
   - B) Un TaskRun ejecuta una Task; Workspace es un campo para asociar volúmenes
   - C) Workspace siempre es un CRD independiente
   - D) Los Steps de un mismo Pod están completamente aislados entre sí

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un TaskRun ejecuta una Task; Workspace es un campo para asociar volúmenes**

Task y Pipeline son definiciones; los Runs son ejecuciones. Los Steps de un mismo Pod comparten la red y los volúmenes, por lo que no constituyen un límite de confianza.

</details>

---

2. ¿Qué es correcto al compartir el código fuente entre TaskRuns?
   - A) emptyDir comparte los mismos archivos entre Pods
   - B) Se puede usar un PVC por ejecución; RWO y RWX por sí solos no son límites de confianza
   - C) Usar distintos subPaths hace que un PVC sea seguro para compartir entre PR externos y versiones de release
   - D) Results siempre admite cadenas ilimitadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se puede usar un PVC por ejecución; RWO y RWX por sí solos no son límites de confianza**

Usa volumeClaimTemplate para tener almacenamiento por ejecución y separa los datos modificables entre niveles de confianza. Reserva Results para valores pequeños y el almacenamiento de artefactos para informes grandes.

</details>

---

3. ¿Cómo se debe gestionar un PR externo después de verificar su HMAC de GitHub?
   - A) Usar los privilegios de firma e IRSA del pipeline de release
   - B) Usar un nivel de confianza de ejecución independiente, con permisos limitados
   - C) Insertar directamente sus comandos de shell en los scripts porque el HMAC pasó la verificación
   - D) Una solicitud verificada siempre corresponde a un push a la rama main

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar un nivel de confianza de ejecución independiente, con permisos limitados**

HMAC valida el origen de la entrega, no autoriza al código a desplegar. La ruta de CI privilegiada de este capítulo se limita a pushes a la rama main protegida del repositorio aprobado.

</details>

---

4. ¿Qué versión de procedencia genera el formateador slsa/v1 de Chains?
   - A) Procedencia SLSA v1.0
   - B) Procedencia SLSA v0.2; v1.0 usa slsa/v2alpha3 o slsa/v2alpha4
   - C) La clave de firma elige automáticamente cualquier versión
   - D) Siempre la misma versión que la API v1 de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Procedencia SLSA v0.2; v1.0 usa slsa/v2alpha3 o slsa/v2alpha4**

Los nombres del formateador y las versiones de la especificación SLSA son distintos. La procedencia a nivel de Pipeline se crea después de completar el Pipeline y requiere verificación y promoción por separado.

</details>

---

5. ¿Cuál es la afirmación correcta sobre las Tasks finally?
   - A) Se ejecutan ante cualquier error, cancelación o timeout
   - B) Se ejecutan después de las Tasks normales, pero la falta de Results, una cancelación o un timeout pueden omitirlas o impedir su ejecución
   - C) Siempre se ejecutan en secuencia, según el orden de declaración
   - D) Proporcionan automáticamente valores predeterminados para los Results de imagen que faltan

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se ejecutan después de las Tasks normales, pero la falta de Results, una cancelación o un timeout pueden omitirlas o impedir su ejecución**

El informe final solo hace referencia al nombre de la ejecución y a tasks.status. No supongas un orden entre las Tasks finally y ten en cuenta el comportamiento de los timeouts.

</details>

---

6. ¿Qué queda por hacer después de que CI termine correctamente y aparezca chains.tekton.dev/signed=true?
   - A) Desplegar de inmediato cualquier etiqueta en producción
   - B) Verificar la clave de confianza, el digest, el builder y la procedencia del código fuente; después, revisar el cambio de GitOps
   - C) Solo decodificar en base64 el JSON de la firma, sin verificarlo
   - D) Comprobar que ArgoCD extraiga la imagen de la aplicación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Verificar la clave de confianza, el digest, el builder y la procedencia del código fuente; después, revisar el cambio de GitOps**

La anotación de firma no constituye verificación criptográfica ni aprobación. ArgoCD sincroniza manifiestos; los kubelets o los runtimes descargan las imágenes.

</details>

---

7. ¿Qué puerto de ServiceMonitor y qué contador del controller corresponden a Pipelines 1.17?
   - A) metrics / pipelinerun_count
   - B) http-metrics / tekton_pipelines_controller_pipelinerun_total
   - C) http / contadores automáticos para todos los espacios de nombres
   - D) 9097 / un histograma de duración de ejecución

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) http-metrics / tekton_pipelines_controller_pipelinerun_total**

Haz coincidir las etiquetas y los puertos reales del Service con los selectores de Prometheus. El contador de finalización actual solo incluye el estado; no tiene una etiqueta de espacio de nombres.

</details>

---

8. ¿Cuál es el comportamiento predeterminado al completar la ejecución para los PVC de volumeClaimTemplate con coschedule=workspaces?
   - A) Siempre se eliminan de inmediato
   - B) Se conservan; la anotación exacta de auto-limpieza con valor true permite eliminarlos al completar
   - C) También se eliminan siempre los PVC existentes proporcionados por el usuario
   - D) PipelineRuns tienen un TTL predeterminado de siete días

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se conservan; la anotación exacta de auto-limpieza con valor true permite eliminarlos al completar**

Otros modos de coschedule y los PVC preexistentes tienen ciclos de vida distintos. Antes de borrar los registros de ejecución, comprueba el tiempo de finalización, la retención y los archivos de registros y firmas.

</details>
