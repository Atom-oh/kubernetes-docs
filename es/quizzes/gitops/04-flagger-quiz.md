# Cuestionario sobre entrega progresiva con Flagger

1. En un despliegue Canary de Flagger, ¿qué significan `stepWeight: 10` y `maxWeight: 50`?
   - A) Aumentar el peso del tráfico de análisis en incrementos de 10 % hasta 50 %, y después realizar la promoción
   - B) Crear 10 Pods y escalar hasta un máximo de 50
   - C) Desviar el 50 % del tráfico en intervalos de 10 segundos
   - D) Permitir una tasa de errores de hasta el 10 % y hacer rollback al 50 %

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Aumentar el peso del tráfico de análisis en incrementos de 10 % hasta 50 %, y después realizar la promoción**

**Explicación:**
`stepWeight` es el incremento del peso en cada paso de análisis, y `maxWeight` es el objetivo del análisis. Las comprobaciones avanzan por 10→20→30→40→50 %; después se actualiza el primario y se promociona el tráfico. Durante la promoción, el Canary puede recibir temporalmente todo el tráfico; el 50 % no es un límite permanente.

</details>

---

2. ¿En qué condición Flagger revierte automáticamente un despliegue Canary?
   - A) Cuando el uso de CPU supera el 80 %
   - B) Cuando los fallos de las comprobaciones de una revisión alcanzan el umbral
   - C) Cuando la cantidad de Pods supera maxReplicas
   - D) Cuando el despliegue supera los 30 minutos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuando los fallos de las comprobaciones de una revisión alcanzan el umbral**

**Explicación:**
Flagger evalúa las métricas definidas (por ejemplo, tasa de solicitudes correctas y duración de las solicitudes) en cada paso del análisis. Los fallos se acumulan para una revisión y no se restablecen cada vez que una comprobación tiene éxito. Al alcanzar el umbral, Flagger revierte el cambio en una reconciliación posterior. Los fallos al promocionar el primario pueden requerir otra recuperación, como conservar el Canary que sigue sano.

</details>

---

3. ¿Cuál es la diferencia clave entre Flagger y Argo Rollouts?
   - A) Flagger solo admite Canary, mientras que Argo Rollouts solo admite Blue-Green
   - B) Flagger se integra con el ecosistema Flux, mientras que Argo Rollouts se integra con el ecosistema Argo
   - C) Flagger solo admite Istio, mientras que Argo Rollouts admite todas las mallas de servicio
   - D) Flagger no admite el análisis de métricas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Flagger se integra con el ecosistema Flux, mientras que Argo Rollouts se integra con el ecosistema Argo**

**Explicación:**
Flagger forma parte del ecosistema Flux/Flagger y se integra de forma natural con los flujos de trabajo GitOps de FluxCD. Argo Rollouts pertenece al ecosistema Argo, junto con ArgoCD. Estas asociaciones no son requisitos exclusivos. Flagger controla una carga de trabajo existente mediante un recurso Canary, mientras que Argo Rollouts usa el recurso Rollout y admite workloadRef. Las capacidades concretas de enrutamiento y experimentación dependen del proveedor.

</details>

---

4. ¿Qué función cumple `spec.analysis.mirror: true` en un despliegue Blue-Green de Flagger?
   - A) Reflejar los registros entre los entornos Blue y Green
   - B) Enviar una copia del tráfico de producción al Canary (Green) para probarlo con tráfico real
   - C) Replicar la base de datos para sincronizarla
   - D) Mantener configuraciones idénticas en ambos entornos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Enviar una copia del tráfico de producción al Canary (Green) para probarlo con tráfico real**

**Explicación:**
`mirror: true` envía una copia del tráfico de producción a la nueva versión (Green) para probarla con patrones de tráfico reales. Las respuestas se descartan, pero las escrituras en bases de datos, los mensajes, los pagos y la carga adicional aún pueden producirse. Usa solicitudes cuya seguridad de solo lectura esté verificada, o controles de aislamiento e idempotencia.

</details>

---

5. ¿Qué función cumple `templateRef` al analizar métricas personalizadas en Flagger?
   - A) Hacer referencia a una plantilla de gráfico de Helm
   - B) Hacer referencia a un recurso MetricTemplate que ejecuta consultas de Prometheus o Datadog
   - C) Hacer referencia a una plantilla de Deployment para crear Pods
   - D) Hacer referencia a una plantilla de ConfigMap

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Hacer referencia a un recurso MetricTemplate que ejecuta consultas de Prometheus o Datadog**

**Explicación:**
`templateRef` hace referencia a un recurso personalizado MetricTemplate que contiene consultas PromQL de Prometheus o consultas de Datadog. Durante el análisis, Flagger ejecuta estas consultas y compara los resultados con los umbrales. Así, las decisiones sobre el despliegue también pueden basarse en métricas de negocio, además de las métricas HTTP estándar.

</details>

---

6. ¿Para qué se usan las pruebas previas al despliegue mediante webhooks de Flagger?
   - A) Ejecutar migraciones de bases de datos antes del despliegue
   - B) Ejecutar pruebas de carga o de conformidad antes de desviar el tráfico para validar la nueva versión
   - C) Crear etiquetas en el repositorio Git
   - D) Enviar notificaciones de Slack

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ejecutar pruebas de carga o de conformidad antes de desviar el tráfico para validar la nueva versión**

**Explicación:**
Los webhooks previos al despliegue se ejecutan antes de que empiece el desvío del tráfico. Ejecuta pruebas de humo o de conformidad con las herramientas y los permisos preparados. Que se acepte una prueba de carga asíncrona mediante cmd no significa que la nueva versión haya superado la evaluación; las pruebas bloqueantes, como las ejecutadas con bash, deben finalizar dentro del tiempo de espera configurado.

</details>

---

7. ¿Cuál es la secuencia correcta al usar la automatización de imágenes de FluxCD con Flagger?
   - A) Selección de imagen → cambio de Git revisado y combinado → aplicación por Flux → análisis de Flagger
   - B) Análisis Canary de Flagger → detección de una nueva etiqueta de imagen → confirmación de Git
   - C) Confirmación de Git → detección de una nueva etiqueta de imagen → sincronización de Flux
   - D) Sincronización de Flux → análisis Canary de Flagger → detección de una nueva etiqueta de imagen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Selección de imagen → cambio de Git revisado y combinado → aplicación por Flux → análisis de Flagger**

**Explicación:**
image-reflector evalúa las etiquetas y la política; image-automation modifica el YAML marcado. Si los cambios se envían a una rama aparte, primero hay que revisarlos y combinar el pull request; después Flux aplica la rama de origen y Flagger detecta el cambio de la carga de trabajo. Flagger no reconcilia directamente los objetos HelmRelease.

</details>

---

8. ¿En qué se diferencia el enrutamiento basado en encabezados de las pruebas A/B de Flagger de un despliegue Canary normal?
   - A) Las pruebas A/B exponen la nueva versión a todos los usuarios
   - B) Solo las solicitudes que cumplen condiciones específicas de encabezado HTTP o cookie se dirigen a la nueva versión
   - C) Las pruebas A/B no admiten rollback
   - D) El enrutamiento basado en encabezados solo se aplica al tráfico TCP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo las solicitudes que cumplen condiciones específicas de encabezado HTTP o cookie se dirigen a la nueva versión**

**Explicación:**
En las pruebas A/B, el tráfico se clasifica según las condiciones de encabezado HTTP o cookie definidas en `spec.analysis.match`. Solo las solicitudes que cumplen esas condiciones se dirigen a la nueva versión; las demás usan la versión estable. Los encabezados y las cookies que controla el cliente no sirven para autorizar al personal ni para proteger funciones confidenciales.

</details>
