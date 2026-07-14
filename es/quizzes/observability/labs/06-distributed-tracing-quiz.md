# Cuestionario de análisis de Distributed Tracing del laboratorio de Observability, parte 6

> **Última actualización**: February 22, 2026

Pon a prueba tu comprensión de los conceptos de análisis de Distributed Tracing abordados en el laboratorio integral de Observability, parte 6.

---

1. ¿Cuál es la estructura sintáctica básica de TraceQL para el filtrado de span?
   - A) Sentencias SELECT similares a SQL con cláusulas JOIN
   - B) Llaves que contienen filtros de atributos de span mediante notación de punto, por ejemplo, `{ span.attribute = "value" }`
   - C) Formato de consulta basado en XML
   - D) Solo expresiones regulares

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Llaves que contienen filtros de atributos de span mediante notación de punto, por ejemplo, `{ span.attribute = "value" }`**

**Explicación:**
TraceQL utiliza una sintaxis basada en pipelines con llaves para selectores de span. Estructura básica: `{ spanset_filter }`, donde los filtros usan notación de punto para los atributos. Los atributos intrínsecos usan el prefijo `span.` (por ejemplo, `span.duration`, `span.status`), los atributos de recursos usan el prefijo `resource.` (por ejemplo, `resource.service.name`) y los atributos de span son directos (por ejemplo, `http.status_code`). Los filtros admiten operadores como `=`, `!=`, `>`, `<`, `=~` (regex) y pueden combinarse con `&&` y `||`.

</details>

---

2. ¿Qué devuelve la consulta TraceQL `{ span.http.status_code >= 500 }`?
   - A) Todos los traces del sistema
   - B) Spans donde el código de estado de respuesta HTTP fue 500 o superior, lo que indica errores del servidor
   - C) Spans que tardaron más de 500 milisegundos
   - D) Los 500 spans más recientes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Spans donde el código de estado de respuesta HTTP fue 500 o superior, lo que indica errores del servidor**

**Explicación:**
Esta consulta filtra spans según el atributo `http.status_code` y devuelve solo aquellos con códigos de estado de error del servidor (500, 502, 503, etc.). Esto resulta útil para investigar condiciones de error en sistemas distribuidos. La consulta devuelve el trace completo que contiene los spans coincidentes, resaltando los spans con errores. Puedes acotar aún más los resultados con filtros adicionales como `{ span.http.status_code >= 500 && resource.service.name = "payment-service" }` para centrarte en Services específicos.

</details>

---

3. ¿Cómo puedes identificar conexiones con una alta tasa de errores o latencia en el Service Graph de Tempo?
   - A) Las conexiones siempre se muestran de forma idéntica independientemente de las métricas
   - B) Service Graph visualiza las conexiones con codificación por color o grosor según las tasas de error y la latencia, destacando comunicaciones problemáticas entre Services
   - C) Debes calcular manualmente las métricas de las conexiones a partir de spans sin procesar
   - D) Service Graph solo muestra nombres de Services sin métricas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Service Graph visualiza las conexiones con codificación por color o grosor según las tasas de error y la latencia, destacando comunicaciones problemáticas entre Services**

**Explicación:**
El Service Graph de Tempo (generado a partir de datos de span mediante metrics-generator) muestra los Services como nodos y sus comunicaciones como conexiones. Las conexiones se enriquecen con métricas: las tasas de error se muestran mediante color (rojo para errores altos), la latencia mediante gradientes de color o tooltips y las tasas de solicitudes mediante el grosor de la conexión. Esta visualización identifica rápidamente dependencias problemáticas; si la conexión del Service A al Service B es roja, investiga esa ruta de comunicación específica. Al hacer clic en las conexiones, a menudo se revelan métricas detalladas y enlaces a traces relevantes.

</details>

---

4. ¿Cómo identificas cuellos de botella mediante la línea de tiempo de Span (Waterfall View)?
   - A) Los cuellos de botella se identifican solo por el nombre del span
   - B) Busca spans con una duración desproporcionadamente larga en comparación con el span padre, grandes brechas entre spans secundarios u operaciones secuenciales que podrían paralelizarse
   - C) La vista de cascada no muestra información de tiempo
   - D) Los cuellos de botella solo son visibles en el Service Graph

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Busca spans con una duración desproporcionadamente larga en comparación con el span padre, grandes brechas entre spans secundarios u operaciones secuenciales que podrían paralelizarse**

**Explicación:**
La vista de cascada muestra relaciones jerárquicas de span con información de tiempo. Los indicadores de cuellos de botella incluyen: spans largos que dominan la duración del trace (por ejemplo, una consulta a la base de datos que ocupa el 80 % del tiempo total), brechas entre spans que indican tiempo de espera (latencia de red, retrasos de cola), spans secundarios secuenciales que podrían ejecutarse en paralelo y spans con alto tiempo propio (tiempo no atribuido a elementos secundarios). Al examinar visualmente la cascada, identificas dónde se invierte el tiempo y si el patrón de ejecución es óptimo.

</details>

---

5. ¿Cómo configuras el campo derivado TraceID de Loki a Tempo para la correlación?
   - A) No se necesita configuración; es automático
   - B) En la configuración de la fuente de datos Loki de Grafana, agrega un campo derivado con una regex para extraer los ID de trace de los logs y configura un enlace interno a la fuente de datos Tempo
   - C) Instala un plugin independiente para la correlación
   - D) Los campos derivados solo funcionan con URL externas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) En la configuración de la fuente de datos Loki de Grafana, agrega un campo derivado con una regex para extraer los ID de trace de los logs y configura un enlace interno a la fuente de datos Tempo**

**Explicación:**
Pasos de configuración: en Grafana, edita la fuente de datos Loki y busca "Derived fields". Agrega un campo con: Name (por ejemplo, "TraceID"), Regex para hacer coincidir los ID de trace en tu formato de log (por ejemplo, `traceID=(\w+)` o `"trace_id":"([^"]+)"`), Internal link habilitado, que apunte a tu fuente de datos Tempo, con Query que use el grupo de captura de regex (`${__value.raw}`). Al ver logs, los ID de trace extraídos se convierten en enlaces en los que se puede hacer clic y que abren el trace correspondiente en la vista de exploración de Tempo.

</details>

---

6. ¿Qué permite la funcionalidad Span to Logs de Tempo?
   - A) Genera automáticamente logs a partir de spans
   - B) Permite navegar desde un span de un trace directamente a logs correlacionados en Loki según el intervalo de tiempo y etiquetas como el nombre del Service o el ID de trace
   - C) Reemplaza por completo los logs por spans
   - D) Solo funciona con CloudWatch Logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Permite navegar desde un span de un trace directamente a logs correlacionados en Loki según el intervalo de tiempo y etiquetas como el nombre del Service o el ID de trace**

**Explicación:**
La funcionalidad "Span to Logs" de Tempo (configurada en los ajustes de la fuente de datos Tempo) crea enlaces desde spans a consultas de Loki. Al ver un trace, cada span tiene un enlace "Logs" que construye una consulta Loki utilizando la ventana temporal del span, el nombre del Service y, opcionalmente, el ID de trace. Esto permite investigar qué registró un Service durante la ejecución del span, lo cual es invaluable para comprender errores o depurar comportamientos inesperados. La configuración especifica qué etiquetas de Loki asignar a partir de atributos de span.

</details>

---

7. ¿Cómo permite el mecanismo de exemplars profundizar desde métricas hasta traces?
   - A) Los exemplars reemplazan por completo las métricas
   - B) Los exemplars adjuntan ID de trace a muestras de métricas en el momento de registro, lo que permite navegar directamente desde un punto de datos de una métrica hasta un trace representativo
   - C) Los exemplars solo funcionan con métricas de contador
   - D) Debes correlacionar manualmente las métricas y los traces por marca de tiempo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los exemplars adjuntan ID de trace a muestras de métricas en el momento de registro, lo que permite navegar directamente desde un punto de datos de una métrica hasta un trace representativo**

**Explicación:**
Los exemplars son metadatos (incluido el ID de trace) adjuntos a observaciones de métricas. Al registrar un histograma o contador, la aplicación incluye un ID de trace del contexto de la solicitud actual. En Grafana, las visualizaciones de métricas muestran exemplars como puntos en el gráfico. Al hacer clic en un exemplar, se revela su ID de trace con un enlace al backend de tracing. Esto permite flujos de trabajo eficaces: detecta un pico de latencia en un dashboard, haz clic en un exemplar en ese pico e inmediatamente verás un trace representativo que muestra por qué esa solicitud fue lenta.

</details>

---

8. ¿Qué representan Rate, Errors y Duration en los dashboards de métricas RED?
   - A) Métricas de utilización de recursos para nodos
   - B) Rate es el throughput de solicitudes por segundo, Errors es el recuento o porcentaje de solicitudes fallidas y Duration es la latencia del tiempo de respuesta (normalmente como percentiles)
   - C) Solo métricas específicas de bases de datos
   - D) Mediciones de ancho de banda de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Rate es el throughput de solicitudes por segundo, Errors es el recuento o porcentaje de solicitudes fallidas y Duration es la latencia del tiempo de respuesta (normalmente como percentiles)**

**Explicación:**
RED es una metodología de monitoreo centrada en Services: Rate mide el throughput (solicitudes por segundo) y responde "¿cuánto tráfico está gestionando el Service?". Errors mide la tasa de fallos (recuento o porcentaje de errores) y responde "¿con qué frecuencia falla el Service?". Duration mide la distribución de latencia (p50, p95, p99) y responde "¿cuánto tardan las solicitudes?". En conjunto, estas métricas proporcionan una visibilidad completa del estado del Service. Si Rate baja, algo está bloqueando las solicitudes; si Errors aumenta, algo está fallando; si Duration aumenta, algo es lento.

</details>

---

9. ¿Cómo configurarías un indicador de dashboard SLI/SLO para una disponibilidad del 99.9 % y una latencia p99 inferior a 500ms?
   - A) Estas métricas no se pueden mostrar en un solo dashboard
   - B) Crea paneles de indicador con consultas PromQL que calculen los valores SLI actuales y configura umbrales para mostrar zonas verde/amarilla/roja en relación con los objetivos SLO
   - C) Los dashboards SLI/SLO requieren una licencia comercial de Grafana
   - D) Usa paneles de texto estático con valores introducidos manualmente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crea paneles de indicador con consultas PromQL que calculen los valores SLI actuales y configura umbrales para mostrar zonas verde/amarilla/roja en relación con los objetivos SLO**

**Explicación:**
Para el SLI de disponibilidad: consulta `sum(rate(requests_total{status!~"5.."}[30d])) / sum(rate(requests_total[30d])) * 100`, que muestra el porcentaje de disponibilidad actual con umbrales (verde >= 99.9 %, amarillo >= 99.5 %, rojo < 99.5 %). Para la latencia p99: consulta `histogram_quantile(0.99, sum(rate(request_duration_seconds_bucket[5m])) by (le)) * 1000` (en ms), con umbrales (verde <= 500ms, amarillo <= 750ms, rojo > 750ms). Agrega paneles de presupuesto de errores que muestren el presupuesto restante según los objetivos SLO y la tasa de consumo actual.

</details>

---

10. ¿Cómo son útiles los atributos de span de consultas de bases de datos como `db.system` y `db.statement` en Distributed Tracing?
    - A) Solo se usan para el agrupamiento de conexiones de bases de datos
    - B) Identifican el tipo de base de datos y capturan la consulta real, lo que permite identificar consultas lentas, problemas N+1 y cuellos de botella relacionados con bases de datos en traces
    - C) Estos atributos están obsoletos en OpenTelemetry
    - D) Solo se aplican a bases de datos SQL, no a NoSQL

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Identifican el tipo de base de datos y capturan la consulta real, lo que permite identificar consultas lentas, problemas N+1 y cuellos de botella relacionados con bases de datos en traces**

**Explicación:**
Las convenciones semánticas de OpenTelemetry definen atributos estándar de span de base de datos: `db.system` identifica el tipo de base de datos (postgresql, mysql, redis, mongodb), `db.statement` contiene el texto de la consulta (con sanitización por seguridad), `db.operation` muestra el tipo de operación (SELECT, INSERT) y `db.name` indica el nombre de la base de datos. Estos atributos permiten: filtrar traces por tipo de base de datos, identificar consultas lentas en la vista de cascada, detectar patrones de consulta N+1 (muchas consultas secuenciales similares) y correlacionar spans de base de datos con la latencia general de las solicitudes. Esta visibilidad es crucial para la optimización del rendimiento.

</details>
