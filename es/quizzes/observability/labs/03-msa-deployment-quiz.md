# Laboratorio de Observabilidad, Parte 3: Cuestionario sobre despliegue de MSA y Canary

> **Última actualización**: February 22, 2026

Pon a prueba tu comprensión de los conceptos de despliegue de MSA y lanzamiento Canary tratados en el Laboratorio End-to-End de Observabilidad, Parte 3.

---

1. ¿Qué tipo de Generator de ApplicationSet de ArgoCD es el más adecuado para desplegar la misma aplicación en varios clusters?
   - A) List Generator con nombres de cluster codificados de forma fija
   - B) Cluster Generator que descubre automáticamente los clusters registrados según labels
   - C) Git Generator que lee las configuraciones de cluster desde el repositorio
   - D) Pull Request Generator para entornos efímeros

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cluster Generator que descubre automáticamente los clusters registrados según labels**

**Explicación:**
El Cluster Generator descubre dinámicamente los clusters registrados en ArgoCD y genera Applications para cada uno. Al usar labels de cluster (por ejemplo, `environment: production`, `region: us-east-1`), puedes seleccionar clusters de forma específica. Esto es más fácil de mantener que las listas codificadas de forma fija, porque añadir o eliminar clusters solo requiere actualizar los registros y labels de cluster, no modificar las definiciones de ApplicationSet.

</details>

---

2. ¿Cuál es la principal ventaja del patrón App-of-Apps en ArgoCD?
   - A) Reduce el número total de Applications de ArgoCD necesarias
   - B) Permite una gestión jerárquica en la que una Application principal administra Applications secundarias, proporcionando estructura organizativa y operaciones por lotes
   - C) Mejora el rendimiento de sincronización al paralelizar todos los despliegues
   - D) Elimina la necesidad de Helm o Kustomize

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Permite una gestión jerárquica en la que una Application principal administra Applications secundarias, proporcionando estructura organizativa y operaciones por lotes**

**Explicación:**
El patrón App-of-Apps crea una jerarquía en la que los manifests de una Application raíz contienen definiciones para otras Applications. Esto proporciona: gestión centralizada de múltiples aplicaciones, herencia de configuración coherente, inicialización más sencilla de plataformas completas y la capacidad de aplicar cambios a múltiples aplicaciones actualizando la Application principal. Es especialmente útil para equipos de plataforma que gestionan múltiples microservices o entornos multi-tenant.

</details>

---

3. ¿Qué controlan las configuraciones de weight y limits en un NodePool de Karpenter?
   - A) Weight determina la asignación de CPU por Pod; limits establece los límites de memoria
   - B) Weight establece la prioridad de scheduling entre NodePools; limits restringe los recursos totales que Karpenter puede aprovisionar para ese pool
   - C) Weight controla los niveles de precio de los nodos; limits establece el número máximo de nodos
   - D) Weight determina la densidad de Pods; limits establece el ancho de banda de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Weight establece la prioridad de scheduling entre NodePools; limits restringe los recursos totales que Karpenter puede aprovisionar para ese pool**

**Explicación:**
El weight de NodePool (0-100) determina la preferencia cuando varios NodePools pueden satisfacer los requisitos de un Pod: un weight más alto significa mayor prioridad. Limits define los recursos máximos (CPU, memoria) que Karpenter puede aprovisionar para ese NodePool, lo que evita un escalado ilimitado. Esto permite crear infraestructura por niveles: pools de weight alto para tipos de instancia preferidos con limits para controlar los costes y pools de respaldo de weight más bajo para capacidad excedente.

</details>

---

4. ¿Qué tipos de métricas puede usar el scaler SQS de KEDA para las decisiones de escalado?
   - A) Solo ApproximateNumberOfMessages
   - B) ApproximateNumberOfMessages, ApproximateNumberOfMessagesNotVisible o ApproximateNumberOfMessagesDelayed
   - C) Solo métricas personalizadas de CloudWatch
   - D) Los scalers SQS solo admiten escalado basado en el tiempo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ApproximateNumberOfMessages, ApproximateNumberOfMessagesNotVisible o ApproximateNumberOfMessagesDelayed**

**Explicación:**
El scaler SQS de KEDA admite varias métricas de cola: `ApproximateNumberOfMessages` (mensajes visibles listos para procesar), `ApproximateNumberOfMessagesNotVisible` (mensajes que se están procesando pero aún no se han eliminado) y `ApproximateNumberOfMessagesDelayed` (mensajes en la cola de retraso). Puedes elegir según tu estrategia de escalado: normalmente `ApproximateNumberOfMessages` para escalar según el backlog o métricas combinadas para tener una percepción más completa de la profundidad de la cola.

</details>

---

5. ¿Cuál es la diferencia clave entre la auto-instrumentación de OpenTelemetry y la instrumentación manual?
   - A) La auto-instrumentación proporciona traces más detallados que la instrumentación manual
   - B) La auto-instrumentación captura automáticamente telemetría de frameworks compatibles sin cambios de código, mientras que la instrumentación manual requiere llamadas explícitas al SDK para spans y métricas personalizados
   - C) La instrumentación manual está obsoleta en favor de la auto-instrumentación
   - D) La auto-instrumentación solo funciona con lenguajes interpretados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La auto-instrumentación captura automáticamente telemetría de frameworks compatibles sin cambios de código, mientras que la instrumentación manual requiere llamadas explícitas al SDK para spans y métricas personalizados**

**Explicación:**
La auto-instrumentación (mediante agents, manipulación de bytecode o monkey-patching) captura automáticamente telemetría de frameworks, librerías y runtimes populares sin modificar el código de la aplicación. La instrumentación manual usa el SDK de OTel para crear explícitamente spans, añadir atributos, registrar métricas y emitir logs. La práctica recomendada es combinar ambas: auto-instrumentación para la cobertura estándar de frameworks e instrumentación manual para spans específicos del negocio y métricas personalizadas.

</details>

---

6. ¿Qué habilita el argumento de JVM `-javaagent:opentelemetry-javaagent.jar` para los services Java?
   - A) Habilita únicamente la monitorización JMX
   - B) Adjunta el agent Java de OTel para la instrumentación automática de frameworks y librerías Java comunes
   - C) Configura la telemetría de recolección de basura de Java
   - D) Habilita la integración con Java Flight Recorder

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Adjunta el agent Java de OTel para la instrumentación automática de frameworks y librerías Java comunes**

**Explicación:**
El agent Java de OpenTelemetry usa instrumentación de bytecode para capturar automáticamente telemetría de frameworks Java populares (Spring, JAX-RS, gRPC), clientes HTTP (Apache HttpClient, OkHttp), bases de datos (JDBC, Hibernate) y sistemas de mensajería (Kafka, RabbitMQ). El agent se adjunta al iniciar la JVM mediante `-javaagent` y no requiere cambios de código. La configuración se realiza mediante variables de entorno (por ejemplo, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`).

</details>

---

7. ¿Qué función desempeña AnalysisTemplate en los despliegues Canary de Argo Rollouts?
   - A) Define el análisis de la imagen de contenedor para el escaneo de seguridad
   - B) Especifica las consultas de métricas y los criterios de éxito que determinan si un lanzamiento Canary debe continuar o hacer rollback
   - C) Configura los porcentajes de división del tráfico durante Canary
   - D) Gestiona el número de réplicas durante la entrega progresiva

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Especifica las consultas de métricas y los criterios de éxito que determinan si un lanzamiento Canary debe continuar o hacer rollback**

**Explicación:**
AnalysisTemplate define el análisis automatizado para los lanzamientos Canary. Especifica: proveedores de métricas (Prometheus, Datadog, CloudWatch), consultas que evaluar (por ejemplo, tasa de errores, latencia), umbrales de éxito/error e intervalos de medición. Durante un rollout, Argo Rollouts crea AnalysisRuns a partir de la plantilla y evalúa continuamente las métricas. Si los criterios fallan, el rollout se pausa automáticamente o hace rollback, lo que permite una entrega progresiva segura sin intervención manual.

</details>

---

8. ¿Qué mide una consulta PromQL de tasa de éxito como `sum(rate(http_requests_total{status=~"2.."}[5m])) / sum(rate(http_requests_total[5m]))`?
   - A) El número total de solicitudes exitosas en los últimos 5 minutos
   - B) La proporción de respuestas HTTP 2xx respecto al total de respuestas, que representa la tasa de éxito
   - C) El tiempo de respuesta medio para las solicitudes exitosas
   - D) El número de usuarios únicos exitosos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La proporción de respuestas HTTP 2xx respecto al total de respuestas, que representa la tasa de éxito**

**Explicación:**
Esta consulta PromQL calcula la tasa de éxito dividiendo las solicitudes exitosas (códigos de estado HTTP 2xx, coincidentes mediante la regex `2..`) entre el total de solicitudes, ambas calculadas como tasas de 5 minutos. La función `rate()` calcula el promedio por segundo durante la ventana y `sum()` agrega todas las dimensiones de labels. El resultado es una proporción entre 0 y 1, normalmente mostrada como porcentaje. Este es un SLI clave para la fiabilidad del service.

</details>

---

9. ¿Qué sucede automáticamente cuando un AnalysisRun de Argo Rollouts devuelve un estado FAIL?
   - A) El rollout continúa, pero envía una alerta
   - B) El rollout se pausa y espera intervención manual
   - C) El rollout se cancela automáticamente y reduce el Canary, restaurando la versión estable para todo el tráfico
   - D) El AnalysisRun se reinicia con parámetros distintos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El rollout se cancela automáticamente y reduce el Canary, restaurando la versión estable para todo el tráfico**

**Explicación:**
Cuando un AnalysisRun falla (las métricas superan los umbrales de error), Argo Rollouts activa automáticamente un rollback: el ReplicaSet Canary se escala a cero, todo el tráfico vuelve a la versión estable y el estado del Rollout pasa a ser "Degraded". Este rollback automatizado es una función de seguridad clave de la entrega progresiva: los lanzamientos problemáticos se revierten automáticamente sin requerir intervención humana, lo que minimiza el blast radius de los despliegues defectuosos.

</details>

---

10. ¿Por qué es importante la propagación de contexto de W3C TraceContext al usar el SDK de OpenTelemetry?
    - A) Es necesaria para la recopilación de métricas
    - B) Habilita el tracing distribuido al transmitir el contexto de trace (trace ID, span ID, flags) a través de los límites entre services en headers HTTP
    - C) Mejora la compresión de logs
    - D) Solo es necesaria para los services gRPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Habilita el tracing distribuido al transmitir el contexto de trace (trace ID, span ID, flags) a través de los límites entre services en headers HTTP**

**Explicación:**
W3C TraceContext es un formato estandarizado para propagar información de trace distribuido mediante headers HTTP (`traceparent`, `tracestate`). Cuando el service A llama al service B, la propagación de contexto transmite el trace ID y el span ID principal, lo que permite vincular los spans del service B al trace del service A. Sin una propagación adecuada, los traces se interrumpen en los límites entre services y muestran segmentos desconectados en lugar de flujos de solicitudes completos. El SDK de OTel gestiona esto automáticamente cuando está configurado, pero los services deben reenviar los headers.

</details>
