# Cuestionario de observabilidad de Cilium Service Mesh

Este cuestionario evalúa tu comprensión de Hubble, la recopilación de métricas, los mapas de servicios, el monitoreo de Golden Signals y la integración con OpenTelemetry.

## Preguntas del cuestionario

### 1. ¿Cuál NO es un componente principal de Hubble?

A. Hubble Observer
B. Hubble Relay
C. Hubble Router
D. Hubble UI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Hubble Router**

**Explicación:**
Los componentes principales de Hubble son Hubble Observer (integrado en Cilium Agent), Hubble Relay (agregación de flujos en todo el clúster), Hubble UI (panel de visualización) y Hubble CLI (interfaz de línea de comandos). Hubble Router no es un componente existente.

</details>

### 2. ¿Qué comando filtra y observa únicamente tráfico HTTP en Hubble CLI?

A. hubble observe --type http
B. hubble observe --protocol http
C. hubble observe --filter http
D. hubble observe --layer http

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. hubble observe --protocol http**

**Explicación:**
El comando `hubble observe --protocol http` filtra únicamente el tráfico del protocolo HTTP. Otros protocolos (tcp, dns, etc.) se pueden filtrar de la misma manera.

</details>

### 3. ¿Qué configuración debe habilitarse en values.yaml para recopilar métricas de Hubble en Prometheus?

A. hubble.prometheus.enabled: true
B. hubble.metrics.enabled
C. hubble.export.prometheus: true
D. prometheus.hubble: true

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. hubble.metrics.enabled**

**Explicación:**
Para habilitar las métricas de Hubble, especifica los tipos de métricas que se recopilarán (dns, drop, tcp, flow, http, etc.) como una lista en hubble.metrics.enabled. Además, configurar serviceMonitor.enabled: true permite que Prometheus Operator realice el scraping automáticamente.

</details>

### 4. ¿Cuál NO es una de las cuatro Golden Signals para el monitoreo?

A. Latency
B. Traffic
C. Availability
D. Saturation

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Availability**

**Explicación:**
Las cuatro Golden Signals definidas por Google SRE son Latency, Traffic, Errors y Saturation. Availability no está incluida en las Golden Signals y se mide indirectamente mediante la métrica Errors.

</details>

### 5. ¿Cuál es el comando correcto para observar tráfico denegado por políticas en Hubble?

A. hubble observe --denied
B. hubble observe --verdict DROPPED
C. hubble observe --blocked
D. hubble observe --policy-denied

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. hubble observe --verdict DROPPED**

**Explicación:**
La opción `--verdict DROPPED` filtra el tráfico denegado por Network Policies. Por el contrario, `--verdict FORWARDED` muestra el tráfico permitido.

</details>

### 6. ¿Qué función se utiliza en consultas PromQL para medir la latencia HTTP P99?

A. avg()
B. histogram_quantile()
C. rate()
D. sum()

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. histogram_quantile()**

**Explicación:**
Las métricas de percentiles como la latencia P99 usan la función histogram_quantile(). Ejemplo: `histogram_quantile(0.99, rate(hubble_http_request_duration_seconds_bucket[5m]))`. Aquí, 0.99 representa el percentil 99.

</details>

### 7. ¿Cuál NO es una función principal proporcionada por Hubble UI?

A. Service Map
B. Flow Timeline
C. Auto Scaling
D. Namespace Filter

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Auto Scaling**

**Explicación:**
Hubble UI proporciona mapas de servicios, Flow Timeline, Namespace Filter, filtro de veredictos y detalles de L7 para flujos individuales. Auto Scaling es una función de gestión de cargas de trabajo, no una función de observabilidad.

</details>

### 8. ¿Cuál es la forma correcta de una consulta PromQL para calcular la tasa de errores HTTP en Cilium?

A. hubble_http_errors_total / hubble_http_requests_total
B. sum(rate(hubble_http_responses_total{status=~"5.."}[5m])) / sum(rate(hubble_http_responses_total[5m]))
C. count(hubble_http_errors) / count(hubble_http_requests)
D. hubble_http_error_rate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. sum(rate(hubble_http_responses_total{status=~"5.."}[5m])) / sum(rate(hubble_http_responses_total[5m]))**

**Explicación:**
La tasa de errores HTTP se calcula dividiendo el número de respuestas 5xx entre el número total de respuestas. La función rate() calcula tasas por segundo y el filtro de etiqueta status (status=~"5..") selecciona únicamente errores del servidor.

</details>

### 9. ¿Qué opción se utiliza para observar únicamente tráfico destinado a un servicio específico en Hubble?

A. --destination-service
B. --to-service
C. --target-service
D. --svc

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. --to-service**

**Explicación:**
El comando `hubble observe --to-service <service-name>` filtra el tráfico destinado a un servicio específico. Por el contrario, `--from-service` filtra el tráfico que se origina en un servicio específico.

</details>

### 10. ¿Qué métrica monitorea la utilización de la tabla de seguimiento de conexiones en Cilium?

A. cilium_ct_usage
B. cilium_datapath_conntrack_active
C. cilium_connections_total
D. cilium_ct_table_size

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. cilium_datapath_conntrack_active**

**Explicación:**
La métrica cilium_datapath_conntrack_active representa el número actual de conexiones activas. Se puede usar con cilium_datapath_conntrack_max para calcular la utilización de la tabla de seguimiento de conexiones.

</details>

### 11. ¿Qué opción se utiliza para recibir la salida de Hubble en formato JSON?

A. --format json
B. -o json
C. --json
D. --output-type json

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. -o json**

**Explicación:**
El comando `hubble observe -o json` genera la salida en formato JSON. Esto es útil para canalizarla a herramientas como jq y realizar procesamiento adicional.

</details>

### 12. ¿Qué protocolo se utiliza al integrar OpenTelemetry Collector con Hubble?

A. HTTP REST API
B. OTLP (OpenTelemetry Protocol)
C. Prometheus Remote Write
D. StatsD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. OTLP (OpenTelemetry Protocol)**

**Explicación:**
Hubble puede exportar datos de flujo a OpenTelemetry Collector mediante OpenTelemetry Protocol (OTLP). Esto permite enrutar datos a varios backends como Jaeger, Prometheus, Loki, etc.

</details>
