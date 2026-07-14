# Cuestionario de análisis de observabilidad

> **Documento relacionado**: [Análisis de observabilidad](../../ops/08-observability-analysis.md)

## Preguntas de opción múltiple

### 1. ¿Qué es un Trace ID en el tracing distribuido?

- A) Un identificador único para un solo span
- B) Un identificador único que correlaciona todos los spans de una solicitud entre servicios
- C) El nombre de un servicio
- D) Una marca de tiempo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un identificador único que correlaciona todos los spans de una solicitud entre servicios**

**Explicación:**
Un Trace ID es un identificador único asignado cuando una solicitud entra al sistema y se propaga a través de todas las llamadas a servicios posteriores. Permite conectar logs, spans y métricas de diferentes servicios que gestionaron la misma solicitud.

</details>

### 2. ¿Cuál es la consulta LogQL correcta para encontrar logs de error en un namespace específico?

- A) `SELECT * FROM logs WHERE level='error'`
- B) `{namespace="production"} |= "error"`
- C) `logs.namespace.production.error`
- D) `grep error /var/log/production`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `{namespace="production"} |= "error"`**

**Explicación:**
LogQL usa selectores de labels entre llaves seguidos de expresiones de filtro. `{namespace="production"}` selecciona logs de ese namespace, y `|= "error"` filtra las líneas que contienen "error". El operador `|=` realiza coincidencia de subcadenas sensible a mayúsculas y minúsculas.

</details>

### 3. ¿Qué mide el método RED?

- A) Uso de recursos, eventos, duración
- B) Tasa, errores, duración (para servicios)
- C) Solicitudes, endpoints, datos
- D) Réplicas, endpoints, Deployments

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Tasa, errores, duración (para servicios)**

**Explicación:**
El método RED mide el estado de los servicios mediante Rate (solicitudes por segundo), Errors (tasa de solicitudes fallidas) y Duration (distribución de latencia). Está optimizado para servicios basados en solicitudes y complementa el método USE para recursos.

</details>

### 4. ¿Qué mide el método USE?

- A) Usuario, sesión, eventos
- B) Utilización, saturación, errores (para recursos)
- C) Carga, almacenamiento, cifrado
- D) Unidades, escala, eficiencia

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Utilización, saturación, errores (para recursos)**

**Explicación:**
El método USE mide el estado de los recursos mediante Utilization (porcentaje ocupado), Saturation (profundidad de cola/espera) y Errors (conteo de errores). Está diseñado para analizar recursos de CPU, memoria, red y almacenamiento.

</details>

### 5. ¿Qué son los Exemplars en Prometheus?

- A) Archivos de configuración de ejemplo
- B) Trace IDs adjuntos a muestras de métricas que permiten la correlación de métricas con traces
- C) Consultas Prometheus de ejemplo
- D) Dashboards de plantilla

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Trace IDs adjuntos a muestras de métricas que permiten la correlación de métricas con traces**

**Explicación:**
Los Exemplars son Trace IDs almacenados junto con muestras de métricas en puntos específicos en el tiempo. Al ver un histograma o contador en Grafana, los exemplars te permiten hacer clic directamente en el trace que generó un punto de datos de métrica específico.

</details>

### 6. ¿Qué función de PromQL calcula la latencia del percentil 95 a partir de un histograma?

- A) `avg()`
- B) `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- C) `max()`
- D) `percentile(95, latency)`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`**

**Explicación:**
`histogram_quantile()` calcula cuantiles a partir de conteos de buckets de histograma. El primer argumento (0.95) es el percentil, y opera sobre la tasa de la métrica `_bucket`. Esto da la latencia por debajo de la cual se completa el 95 % de las solicitudes.

</details>

### 7. ¿Para qué se usa TraceQL?

- A) Escribir alertas de Prometheus
- B) Consultar traces distribuidos en Grafana Tempo
- C) Crear reglas de agregación de logs
- D) Definir políticas de service mesh

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Consultar traces distribuidos en Grafana Tempo**

**Explicación:**
TraceQL es el lenguaje de consulta de Tempo para buscar traces. Admite filtrar por nombre de servicio, nombre de span, duración, atributos y estado. Por ejemplo: `{resource.service.name="api-gateway" && duration>1s}` encuentra traces lentos de API gateway.

</details>

### 8. ¿Cómo se extrae un campo JSON en LogQL?

- A) `json.fieldname`
- B) <code v-pre>{app="myapp"} | json | line_format "{{.fieldname}}"</code>
- C) `SELECT fieldname FROM logs`
- D) `logs.fieldname`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) <code v-pre>{app="myapp"} | json | line_format "{{.fieldname}}"</code>**

**Explicación:**
El parser `| json` extrae campos JSON de líneas de log y los convierte en labels. Luego puedes usar `| line_format` con la sintaxis de plantillas de Go para formatear la salida, o filtrar con campos extraídos como `| status_code >= 500`.

</details>

### 9. ¿Qué permite la correlación entre logs y traces en Grafana?

- A) Copiar y pegar IDs manualmente
- B) Incluir trace_id en los campos de log y configurar campos derivados en el datasource de Loki
- C) Usar el mismo dashboard
- D) Instalar un plugin separado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Incluir trace_id en los campos de log y configurar campos derivados en el datasource de Loki**

**Explicación:**
Las aplicaciones deben emitir Trace IDs en sus logs. En Grafana, configuras los campos derivados de Loki para reconocer el campo trace_id y enlazar con Tempo. Esto crea enlaces clicables desde las líneas de log directamente al trace asociado.

</details>

### 10. ¿Cuál es el propósito de los atributos de span en el tracing distribuido?

- A) Dar estilo a la visualización del trace
- B) Adjuntar metadatos contextuales (ID de usuario, parámetros de solicitud) a los spans
- C) Cifrar datos de trace
- D) Comprimir el almacenamiento de traces

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Adjuntar metadatos contextuales (ID de usuario, parámetros de solicitud) a los spans**

**Explicación:**
Los atributos de span son pares clave-valor que agregan contexto a los spans, como `http.method`, `http.status_code`, `user.id` o `db.statement`. Permiten filtrar traces por contexto de negocio y ayudan a identificar qué solicitudes son problemáticas.

</details>
