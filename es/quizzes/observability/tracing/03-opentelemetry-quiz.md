# Cuestionario de OpenTelemetry

Pon a prueba tus conocimientos sobre OpenTelemetry.

---

1. ¿Cuáles son las tres señales compatibles con OpenTelemetry?
   - A) Logs, Metrics, Events
   - B) Traces, Metrics, Logs
   - C) Spans, Counters, Logs
   - D) Traces, Alerts, Logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Traces, Metrics, Logs**

**Explicación:**
OpenTelemetry estandariza las tres señales principales de observabilidad: Traces (trazado distribuido), Metrics y Logs. Al recopilar y correlacionar estas tres señales de forma integrada, puedes lograr una observabilidad integral del sistema.

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
El pipeline de OTEL Collector se estructura como Receivers (ingesta de datos) -> Processors (procesamiento/transformación de datos) -> Exporters (transmisión al backend). Los Receivers aceptan datos en varios formatos, los Processors realizan procesamiento por lotes, filtrado, incorporación de atributos, etc., y los Exporters envían los datos procesados a los destinos.

</details>

---

3. ¿Cuál NO es una ventaja de la auto-instrumentación en OpenTelemetry?
   - A) Instrumentación sin cambios en el código
   - B) Adopción rápida
   - C) Trazado detallado de la lógica de negocio
   - D) Metadatos consistentes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Trazado detallado de la lógica de negocio**

**Explicación:**
La auto-instrumentación rastrea automáticamente llamadas comunes a bibliotecas como HTTP, bases de datos y colas de mensajes sin cambios en el código. Sin embargo, las operaciones detalladas dentro de la lógica de negocio o las métricas personalizadas requieren instrumentación manual. Es habitual usar conjuntamente la auto-instrumentación y la instrumentación manual.

</details>

---

4. ¿Cuándo resulta más ventajoso el processor tail_sampling de OTEL Collector que el muestreo basado en head?
   - A) Cuando se minimiza el uso de recursos
   - B) Cuando no se pueden perder solicitudes con errores o latencia
   - C) Cuando la implementación debe ser sencilla
   - D) Cuando las decisiones de muestreo deben ser rápidas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuando no se pueden perder solicitudes con errores o latencia**

**Explicación:**
El muestreo basado en tail decide si se realiza el muestreo después de que finalice la solicitud, según los resultados (errores, latencia, etc.). Esto garantiza que nunca se omitan solicitudes importantes (ocurrencias de errores, tiempo de respuesta excedido). En cambio, el muestreo basado en head decide al inicio de la solicitud, por lo que es más sencillo de implementar y utiliza menos recursos, pero puede omitir solicitudes importantes.

</details>

---

5. ¿Cuál es la función de Resource en el SDK de OpenTelemetry?
   - A) Gestión de conexiones de red
   - B) Identificar la entidad que genera datos de telemetría
   - C) Compresión de datos
   - D) Gestión de tokens de autenticación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Identificar la entidad que genera datos de telemetría**

**Explicación:**
Resource son metadatos que identifican la entidad (service, host, container, etc.) que genera datos de telemetría. Incluye atributos como service.name, service.version, deployment.environment para aclarar el origen de los datos. Esta información se adjunta automáticamente a todos los datos de telemetría.

</details>

---

6. ¿Qué patrón de despliegue de OTEL Collector es más eficiente en cuanto a recursos en EKS?
   - A) Patrón Sidecar
   - B) Patrón DaemonSet
   - C) Patrón Gateway
   - D) Patrón Deployment

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Patrón DaemonSet**

**Explicación:**
El patrón DaemonSet es eficiente en cuanto a recursos, ya que ejecuta solo un Collector por nodo. El patrón Sidecar tiene una alta sobrecarga de recursos, ya que ejecuta un Collector para cada Pod. El patrón Gateway está centralizado, pero puede convertirse en un único punto de fallo. Normalmente, se recomienda una combinación de DaemonSet para la recopilación y Gateway para el procesamiento/transmisión.

</details>

---

7. ¿Qué annotation se aplica a un Pod para la inyección de auto-instrumentación mediante OpenTelemetry Operator?
   - A) `otel.io/inject: "true"`
   - B) `instrumentation.opentelemetry.io/inject-java: "true"`
   - C) `opentelemetry.io/auto: "enabled"`
   - D) `trace.otel.io/enabled: "true"`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) instrumentation.opentelemetry.io/inject-java: "true"**

**Explicación:**
OpenTelemetry Operator utiliza annotations con el formato `instrumentation.opentelemetry.io/inject-{language}`. Las annotations específicas de cada lenguaje incluyen inject-java, inject-python, inject-nodejs, inject-dotnet, inject-go, etc. Los agentes de instrumentación se inyectan automáticamente en los Pods que tienen estas annotations.

</details>

---

8. ¿Cuál es la función del processor memory_limiter en la configuración de OTEL Collector?
   - A) Compresión de datos
   - B) Evitar la pérdida de datos cuando la memoria es baja
   - C) Gestión de caché
   - D) Gestión del búfer de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Evitar la pérdida de datos cuando la memoria es baja**

**Explicación:**
El processor memory_limiter supervisa y limita el uso de memoria de Collector. Cuando el uso de memoria alcanza limit_mib, rechaza la ingesta de nuevos datos para evitar la pérdida de datos por OOM (Out of Memory). spike_limit_mib proporciona un búfer para picos repentinos de memoria.

</details>

---

9. ¿Cuál NO es un componente del header traceparent en el estándar W3C Trace Context de OpenTelemetry?
   - A) version
   - B) trace-id
   - C) parent-id
   - D) span-name

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) span-name**

**Explicación:**
El formato del header traceparent de W3C Trace Context es `version-trace_id-parent_id-trace_flags`. version es la versión del formato, trace_id es el identificador de todo el trace, parent_id es el ID del span padre y trace_flags es la marca de muestreo. span-name se almacena dentro del Span y no se incluye en el header de propagación.

</details>

---

10. ¿Cómo se configura el envío de datos a múltiples backends en un pipeline de OTEL Collector?
    - A) Ejecutar Collectors independientes para cada backend
    - B) Enumerar varios exporters en el array exporters
    - C) Configurar varios endpoints en un único exporter
    - D) Usar un processor fanout

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Enumerar varios exporters en el array exporters**

**Explicación:**
En la configuración del pipeline de OTEL Collector, enumerar varios exporters en el array exporters envía los mismos datos a todos los backends. Por ejemplo: `exporters: [otlp/tempo, awsxray, datadog]`. Esto permite usar simultáneamente varios backends de observabilidad con un único Collector.

</details>

---
