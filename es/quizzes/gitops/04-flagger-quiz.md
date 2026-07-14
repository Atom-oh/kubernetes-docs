# Cuestionario sobre entrega progresiva con Flagger

1. En el Deployment Canary de Flagger, ¿qué significan `stepWeight: 10`, `maxWeight: 50`?
   - A) Iniciar el tráfico en 10 % e incrementarlo gradualmente hasta 50 %, luego promover al 100 %
   - B) Crear 10 Pods y escalar hasta un máximo de 50
   - C) Desviar el tráfico al 50 % en intervalos de 10 segundos
   - D) Permitir hasta un 10 % de tasa de errores y hacer rollback al 50 %

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Iniciar el tráfico en 10 % e incrementarlo gradualmente hasta 50 %, luego promover al 100 %**

**Explicación:**
`stepWeight` es el porcentaje de tráfico que se incrementa en cada paso de análisis, y `maxWeight` es el porcentaje máximo de tráfico que el Canary puede recibir. El tráfico aumenta 10 % → 20 % → 30 % → 40 % → 50 % y, si todas las métricas pasan, se promueve al 100 %.

</details>

---

2. ¿En qué condición Flagger realiza automáticamente rollback de un Deployment Canary?
   - A) Cuando el uso de CPU supera el 80 %
   - B) Cuando se superan los umbrales de las métricas durante la cantidad configurada de fallos consecutivos
   - C) Cuando la cantidad de Pods supera maxReplicas
   - D) Cuando el tiempo de Deployment supera los 30 minutos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuando se superan los umbrales de las métricas durante la cantidad configurada de fallos consecutivos**

**Explicación:**
Flagger evalúa las métricas definidas (request-success-rate, request-duration, etc.) en cada paso de análisis. Cuando el recuento de fallos consecutivos alcanza el `threshold`, realiza automáticamente un rollback, devolviendo el tráfico Canary al 0 % y manteniendo la versión original.

</details>

---

3. ¿Cuál es la diferencia clave entre Flagger y Argo Rollouts?
   - A) Flagger solo admite Canary, mientras que Argo Rollouts solo admite Blue-Green
   - B) Flagger se integra con el ecosistema Flux, mientras que Argo Rollouts se integra con el ecosistema Argo
   - C) Flagger solo admite Istio, mientras que Argo Rollouts admite todos los meshes
   - D) Flagger no admite análisis de métricas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Flagger se integra con el ecosistema Flux, mientras que Argo Rollouts se integra con el ecosistema Argo**

**Explicación:**
Flagger forma parte del ecosistema Flux/Flagger y se integra naturalmente en los flujos de trabajo GitOps con FluxCD. Argo Rollouts forma parte del ecosistema Argo junto con ArgoCD. Ambos admiten estrategias Canary, Blue-Green y A/B Testing, y ambos funcionan con diversos service meshes y controladores de ingress.

</details>

---

4. ¿Cuál es la función de `spec.analysis.mirror: true` en el Deployment Blue-Green de Flagger?
   - A) Reflejar logs entre los entornos Blue y Green
   - B) Replicar el tráfico de producción al Canary (Green) para realizar pruebas con tráfico real
   - C) Reflejar la base de datos para la sincronización
   - D) Mantener configuraciones idénticas entre ambos entornos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Replicar el tráfico de producción al Canary (Green) para realizar pruebas con tráfico real**

**Explicación:**
`mirror: true` envía una copia del tráfico de producción a la nueva versión (Green) para realizar pruebas con patrones de tráfico reales. Las respuestas reflejadas no se devuelven a los clientes, lo que permite verificar el comportamiento de la nueva versión sin afectar a los usuarios.

</details>

---

5. ¿Cuál es la función de `templateRef` al usar análisis de Custom Metrics en Flagger?
   - A) Hacer referencia a una plantilla de Helm chart
   - B) Hacer referencia a un MetricTemplate CR para ejecutar consultas de Prometheus/Datadog
   - C) Hacer referencia a una plantilla de Deployment para crear Pods
   - D) Hacer referencia a una plantilla de ConfigMap

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Hacer referencia a un MetricTemplate CR para ejecutar consultas de Prometheus/Datadog**

**Explicación:**
`templateRef` hace referencia a un Custom Resource MetricTemplate que contiene consultas Prometheus PromQL o Datadog. Durante la fase de análisis, Flagger ejecuta estas consultas y compara los resultados con los umbrales. Esto permite tomar decisiones de Deployment basadas en métricas de negocio más allá de las métricas HTTP estándar.

</details>

---

6. ¿Cuál es el propósito de las pruebas previas al rollout mediante Flagger Webhooks?
   - A) Ejecutar migraciones de bases de datos antes del Deployment
   - B) Ejecutar pruebas de carga o pruebas de conformidad antes del desvío de tráfico para validar la nueva versión
   - C) Crear tags en el repositorio Git
   - D) Enviar notificaciones de Slack

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ejecutar pruebas de carga o pruebas de conformidad antes del desvío de tráfico para validar la nueva versión**

**Explicación:**
Los webhooks previos al rollout se invocan antes de que comience el desvío de tráfico. Normalmente, ejecutan pruebas de carga (hey, wrk) o pruebas de Helm mediante el loadtester de Flagger para verificar que la nueva versión realiza correctamente las operaciones básicas antes de exponerla a usuarios reales.

</details>

---

7. ¿Cuál es la secuencia correcta al usar FluxCD Image Automation con Flagger?
   - A) Nueva image tag detectada → commit de Git → sincronización de Flux → análisis Canary de Flagger
   - B) Análisis Canary de Flagger → nueva image tag detectada → commit de Git
   - C) Commit de Git → nueva image tag detectada → sincronización de Flux
   - D) Sincronización de Flux → análisis Canary de Flagger → nueva image tag detectada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Nueva image tag detectada → commit de Git → sincronización de Flux → análisis Canary de Flagger**

**Explicación:**
Flux Image Automation detecta nuevas image tags en el registry y crea un commit que actualiza los manifests en el repositorio Git. Cuando Flux sincroniza este cambio, el Deployment se actualiza y Flagger detecta el cambio para iniciar automáticamente el proceso de análisis Canary.

</details>

---

8. ¿En qué se diferencia el enrutamiento basado en headers en A/B Testing de Flagger de los Deployments Canary normales?
   - A) A/B Testing expone la nueva versión a todos los usuarios
   - B) Solo las solicitudes que coinciden con condiciones específicas de HTTP header/cookie se enrutan a la nueva versión
   - C) A/B Testing no admite rollback
   - D) El enrutamiento basado en headers solo se aplica al tráfico TCP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo las solicitudes que coinciden con condiciones específicas de HTTP header/cookie se enrutan a la nueva versión**

**Explicación:**
En A/B Testing, el tráfico se clasifica según las condiciones de HTTP header o cookie definidas en `spec.analysis.match`. Solo las solicitudes que coinciden con estas condiciones se enrutan a la nueva versión, lo que permite exponer nuevas características a grupos específicos de usuarios (beta testers, empleados internos, etc.) mientras otros usuarios continúan utilizando la versión estable.

</details>
