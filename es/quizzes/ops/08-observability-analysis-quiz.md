# Cuestionario de análisis de observabilidad

> **Documento relacionado**: [Análisis de observabilidad](../../ops/08-observability-analysis.md)

## Preguntas de opción múltiple

### 1. ¿Qué es un Trace ID en el rastreo distribuido?

- A) Un identificador único para un solo span
- B) Un identificador único que correlaciona todos los spans de una solicitud entre servicios
- C) El nombre de un servicio
- D) Una marca de tiempo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un identificador único que correlaciona todos los spans de una solicitud entre servicios**

**Explicación:**
Un servicio continúa un contexto de traza entrante válido o crea una traza nueva. Los spans que participan pueden compartir su Trace ID; los diseños asíncronos también pueden iniciar trazas nuevas conectadas mediante vínculos entre spans. Esto permite relacionar los logs, los spans y las métricas de distintos servicios que atendieron la misma solicitud.

</details>

### 2. ¿Cuál es la consulta LogQL correcta para encontrar logs de error en un espacio de nombres específico?

- A) `SELECT * FROM logs WHERE level='error'`
- B) `{namespace="production"} |= "error"`
- C) `logs.namespace.production.error`
- D) `grep error /var/log/production`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `{namespace="production"} |= "error"`**

**Explicación:**
LogQL usa selectores de etiquetas entre llaves, seguidos de expresiones de filtro. `{namespace="production"}` selecciona los logs de ese espacio de nombres, y `|= "error"` filtra las líneas que contienen «error». El operador `|=` realiza una coincidencia de subcadenas que distingue entre mayúsculas y minúsculas.

</details>

### 3. ¿Qué mide el método RED?

- A) Uso de recursos, eventos y duración
- B) Tasa, errores y duración (para servicios)
- C) Solicitudes, endpoints y datos
- D) Réplicas, endpoints y despliegues

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Tasa, errores y duración (para servicios)**

**Explicación:**
El método RED mide el estado de los servicios mediante la tasa (solicitudes por segundo), los errores (tasa de solicitudes fallidas) y la duración (distribución de la latencia). Está optimizado para servicios impulsados por solicitudes y complementa el método USE, que se centra en los recursos.

</details>

### 4. ¿Qué mide el método USE?

- A) Usuario, sesión y eventos
- B) Utilización, saturación y errores (para recursos)
- C) Carga, almacenamiento y cifrado
- D) Unidades, escala y eficiencia

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Utilización, saturación y errores (para recursos)**

**Explicación:**
El método USE mide el estado de los recursos mediante la utilización (porcentaje de tiempo ocupado), la saturación (longitud de la cola o tiempo de espera) y los errores (recuentos de errores). Está diseñado para analizar recursos de CPU, memoria, red y almacenamiento.

</details>

### 5. ¿Qué son los Exemplars en Prometheus?

- A) Archivos de configuración de ejemplo
- B) Trace IDs adjuntos a muestras de métricas que permiten correlacionar las métricas con las trazas
- C) Consultas de Prometheus de ejemplo
- D) Paneles de control de plantilla

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Trace IDs adjuntos a muestras de métricas que permiten correlacionar las métricas con las trazas**

**Explicación:**
Los Exemplars adjuntan etiquetas contextuales, a menudo un Trace ID, a observaciones seleccionadas de métricas. Al ver un histograma o contador en Grafana, los vínculos de ejemplar configurados pueden abrir la traza asociada que se conservó. No garantizan que se registre una traza para cada observación ni identifican la solicitud exacta del P99.

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
`histogram_quantile()` calcula cuantiles a partir de los recuentos de los buckets del histograma. El primer argumento (0.95) es el percentil, y la función opera sobre la tasa de la métrica `_bucket`. El resultado estima el cuantil a partir de los límites de los buckets. Para combinar instancias, agrega las tasas conservando `le` y las etiquetas previstas de servicio o clúster; el tráfico ausente o nulo requiere un tratamiento independiente.

</details>

### 7. ¿Para qué se usa TraceQL?

- A) Escribir alertas de Prometheus
- B) Consultar trazas distribuidas en Grafana Tempo
- C) Crear reglas de agregación de logs
- D) Definir políticas de malla de servicios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Consultar trazas distribuidas en Grafana Tempo**

**Explicación:**
TraceQL es el lenguaje de consulta de Tempo para buscar trazas. Permite filtrar por nombre del servicio, nombre del span, duración, atributos y estado. Por ejemplo: `{resource.service.name="api-gateway" && duration>1s}` encuentra las trazas lentas de la puerta de enlace de API.

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
El analizador `| json` extrae campos JSON de las líneas de log y los convierte en etiquetas. Puedes dar formato a la salida o filtrar por los campos extraídos. Comprueba los errores del analizador o de conversión con filtros `__error__`, sobre todo antes de agregar métricas y después de usar `unwrap`.

</details>

### 9. ¿Qué permite correlacionar los logs con las trazas en Grafana?

- A) Copiar y pegar IDs manualmente
- B) Incluir trace_id en los campos de log y configurar campos derivados en el origen de datos de Loki
- C) Usar el mismo panel de control
- D) Instalar un plugin independiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Incluir trace_id en los campos de log y configurar campos derivados en el origen de datos de Loki**

**Explicación:**
Las aplicaciones deben incluir los Trace IDs en sus logs. En Grafana, configura los campos derivados de Loki para que reconozcan el campo trace_id y enlacen con Tempo. Así se crean vínculos en los que se puede hacer clic desde las líneas de log directamente a la traza asociada.

</details>

### 10. ¿Cuál es el propósito de los atributos de span en el rastreo distribuido?

- A) Dar estilo a la visualización de la traza
- B) Adjuntar metadatos contextuales acotados, como la ruta y la operación
- C) Cifrar los datos de la traza
- D) Comprimir el almacenamiento de trazas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Adjuntar metadatos contextuales acotados, como la ruta y la operación**

**Explicación:**
Los atributos de span añaden contexto; por ejemplo, `http.route` o `app.operation` de la demostración. Ajusta las consultas al esquema real de convenciones semánticas. Limita la cardinalidad y evita registrar de forma indiscriminada credenciales, cuerpos sin procesar de solicitudes o sentencias de base de datos sensibles.

</details>
