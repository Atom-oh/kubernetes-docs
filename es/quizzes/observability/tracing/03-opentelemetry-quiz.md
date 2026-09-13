# Cuestionario de OpenTelemetry

> **Última actualización**: September 13, 2026

Pon a prueba tus conocimientos sobre OpenTelemetry.

---

1. ¿En cuáles tres señales principales se centra esta guía?
   - A) Logs, Metrics, Events
   - B) Traces, Metrics, Logs
   - C) Spans, Counters, Logs
   - D) Traces, Alerts, Logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Traces, Metrics, Logs**

**Explicación:**
Esta guía se centra en traces, metrics y logs. OpenTelemetry también desarrolla soporte para profiling; la estabilidad difiere según la señal, el componente y el lenguaje. La correlación requiere atributos de recurso compatibles y contexto propagado, no simplemente habilitar tres exporters.

</details>

---

2. ¿Cuál es el orden correcto de los componentes de OpenTelemetry Collector?
   - A) Processors -> Receivers -> Exporters
   - B) Exporters -> Processors -> Receivers
   - C) Receivers -> Processors -> Exporters
   - D) Receivers -> Exporters -> Processors

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Receivers -> Processors -> Exporters**

**Explicación:**
El pipeline de OTEL Collector se estructura como Receivers (ingestión de datos) -> Processors (procesamiento/transformación de datos) -> Exporters (transmisión al backend). Los Receivers aceptan datos en diversos formatos, los Processors realizan procesamiento por lotes, filtrado, adición de atributos, etc., y los Exporters envían los datos procesados a los destinos.

</details>

---

3. ¿Cuál NO es una ventaja de la instrumentación automática en OpenTelemetry?
   - A) Instrumentación sin cambios de código
   - B) Adopción rápida
   - C) Trazado detallado de la lógica de negocio
   - D) Metadatos coherentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Trazado detallado de la lógica de negocio**

**Explicación:**
La instrumentación automática rastrea automáticamente llamadas habituales de bibliotecas, como HTTP, bases de datos y colas de mensajes, sin cambios de código. Sin embargo, las operaciones detalladas dentro de la lógica de negocio o las métricas personalizadas requieren instrumentación manual. Es habitual utilizar juntas la instrumentación automática y la manual.

</details>

---

4. ¿Cuándo resulta útil el processor tail_sampling del Collector en comparación con el muestreo basado en la cabecera?
   - A) Cuando se minimiza el uso de recursos
   - B) Cuando el estado y la duración observados del span deben influir en el muestreo
   - C) Cuando la implementación debe ser sencilla
   - D) Cuando las decisiones de muestreo deben ser rápidas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuando el estado y la duración observados del span deben influir en el muestreo**

**Explicación:**
Con la estrategia predeterminada `trace-complete` de Collector 0.160.0, la evaluación utiliza los spans acumulados cuando se activa el temporizador de decisión; el nombre no demuestra que la solicitud o el trace estén completos. Los spans que ya se descartaron mediante muestreo de cabecera no se pueden recuperar. Los spans tardíos, los límites de capacidad, los reintentos y los cambios de enrutamiento pueden afectar a la retención. El muestreo de cola con estado requiere que los spans de un trace lleguen al mismo Collector de muestreo; no garantiza que se conserve cada error o solicitud lenta.

</details>

---

5. ¿Cuál es el rol de Resource en el SDK de OpenTelemetry?
   - A) Gestión de conexiones de red
   - B) Identificar la entidad que genera datos de telemetría
   - C) Compresión de datos
   - D) Gestión de tokens de autenticación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Identificar la entidad que genera datos de telemetría**

**Explicación:**
Un Resource identifica al productor de telemetría, por ejemplo mediante `service.name`, `service.version` y `deployment.environment.name`. El SDK/provider configurado lo asocia con los datos emitidos. Los atributos de identidad de Kubernetes, de la nube o personalizados requieren la configuración o el detector adecuados; no todos se detectan automáticamente.

</details>

---

6. ¿Qué carga de trabajo de Kubernetes normalmente ejecuta un Collector en cada nodo apto?
   - A) Patrón sidecar
   - B) Patrón DaemonSet
   - C) Patrón gateway
   - D) Patrón Deployment

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Patrón DaemonSet**

**Explicación:**
Un DaemonSet coloca un Pod en cada nodo apto; los selectores, los taints y las restricciones de programación determinan la aptitud. No es compatible con EKS Fargate. Los sidecars comparten un Pod de aplicación, mientras que los gateways usan una capa central que puede tener varias réplicas. Ningún patrón es universalmente el más eficiente en recursos: compare el volumen real de señales, los recuentos de nodos/Pods, el aislamiento, la disponibilidad y las necesidades de procesamiento con estado. Un Service ClusterIP delante de un DaemonSet no enruta automáticamente al nodo local.

</details>

---

7. ¿Qué anotación se aplica a un Pod para la inyección de instrumentación automática mediante OpenTelemetry Operator?
   - A) `otel.io/inject: "true"`
   - B) `instrumentation.opentelemetry.io/inject-java: "true"`
   - C) `opentelemetry.io/auto: "enabled"`
   - D) `trace.otel.io/enabled: "true"`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) instrumentation.opentelemetry.io/inject-java: "true"**

**Explicación:**
El Operator utiliza anotaciones de inyección específicas del lenguaje. Para un Deployment, colóquelas en `spec.template.metadata.annotations` y haga referencia a un recurso Instrumentation existente en el namespace correcto. La inyección correcta también requiere un webhook operativo y una configuración de lenguaje/runtime compatible. Los Pods existentes no se instrumentan de forma retroactiva; los requisitos previos específicos de Go y de otros lenguajes deben revisarse por separado.

</details>

---

8. ¿Cuál es el rol del processor memory_limiter en la configuración de OTEL Collector?
   - A) Compresión de datos
   - B) Aplicar contrapresión cuando se superan los umbrales de memoria configurados
   - C) Gestión de caché
   - D) Gestión de búferes de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplicar contrapresión cuando se superan los umbrales de memoria configurados**

**Explicación:**
`limit_mib` es el límite estricto; el límite flexible es `limit_mib - spike_limit_mib`. Por encima del límite flexible, el processor rechaza datos con un error que admite reintento. Por encima del límite estricto, también fuerza la recolección de basura. El comportamiento de reintento/contrapresión de los componentes upstream es importante: los datos rechazados pueden perderse si no se reintentan. Deje margen por debajo del límite de memoria del contenedor; este processor no es almacenamiento duradero ni una garantía absoluta contra OOM/pérdida de datos.

</details>

---

9. ¿Cuál NO es un componente de la cabecera traceparent en el estándar W3C Trace Context de OpenTelemetry?
   - A) version
   - B) trace-id
   - C) parent-id
   - D) span-name

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) span-name**

**Explicación:**
OpenTelemetry utiliza el estándar W3C Trace Context. Los campos de `traceparent` son version, trace ID, parent ID y trace flags; el parent ID identifica el span que envía, y los flags incluyen un bit de muestreo. Un nombre de span no se transporta en esta cabecera. Propagar el contexto no registra ni exporta por sí mismo un span.

</details>

---

10. ¿Cómo se configura el envío de datos a varios backends en un pipeline de OTEL Collector?
    - A) Ejecutar Collectors independientes para cada backend
    - B) Enumerar varios exporters en el array de exporters
    - C) Configurar varios endpoints en un único exporter
    - D) Usar un processor fanout

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Enumerar varios exporters en el array de exporters**

**Explicación:**
Enumere los exporters configurados que admitan la señal del pipeline, por ejemplo `exporters: [otlp/tempo, awsxray, datadog]` para traces en una distribución que contenga esos componentes. El fan-out no es una transacción atómica entre backends: los errores de exporter, las colas, los reintentos, las transformaciones y la aceptación por parte del backend pueden producir resultados conservados diferentes.

</details>

---

[Volver a la guía](../../../observability/tracing/03-opentelemetry.md)
