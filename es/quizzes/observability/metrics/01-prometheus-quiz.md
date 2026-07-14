# Cuestionario de Prometheus

Un cuestionario para poner a prueba tu comprensión de Prometheus.

---

1. ¿Cuál es el método de recopilación de datos de Prometheus?
   - A) Basado en Push: las aplicaciones envían métricas
   - B) Basado en Pull: Prometheus recopila métricas de los objetivos
   - C) Basado en streaming: flujos de datos en tiempo real
   - D) Basado en lotes: transferencias periódicas de archivos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Basado en Pull: Prometheus recopila métricas de los objetivos**

**Explicación:**
Prometheus es un sistema de recopilación de métricas basado en Pull que recopila periódicamente métricas de los endpoints /metrics de los objetivos mediante HTTP. Las ventajas de este enfoque son el control centralizado de los objetivos y los intervalos de recopilación, y la detección automática de la disponibilidad de los objetivos.

</details>

---

2. ¿Cuál es la consulta PromQL correcta para calcular la tasa de solicitudes HTTP durante los últimos 5 minutos?
   - A) `rate(http_requests_total, 5m)`
   - B) `rate(http_requests_total[5m])`
   - C) `increase(http_requests_total[5m])`
   - D) `avg(http_requests_total[5m])`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `rate(http_requests_total[5m])`**

**Explicación:**
La función `rate()` calcula la tasa de incremento promedio por segundo de las métricas Counter. Los vectores de rango especifican el tiempo entre corchetes `[]`. `increase()` devuelve el incremento total y `avg()` es una función de agregación que calcula promedios. `rate(http_requests_total[5m])` calcula las solicitudes por segundo durante 5 minutos.

</details>

---

3. ¿Cuál es la función de ServiceMonitor en Prometheus Operator?
   - A) Despliega el servidor Prometheus
   - B) Define reglas de alertas
   - C) Define los servicios que se monitorizarán y las configuraciones de recopilación
   - D) Crea dashboards de Grafana

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Define los servicios que se monitorizarán y las configuraciones de recopilación**

**Explicación:**
ServiceMonitor es un CRD de Prometheus Operator que define de forma declarativa las configuraciones de recopilación para monitorizar servicios de Kubernetes. Puedes configurar selectores de servicios objetivo, endpoints, intervalos de recopilación, relabeling de etiquetas, etc. PrometheusRule gestiona las reglas de alertas y el CRD Prometheus gestiona el despliegue del servidor.

</details>

---

4. ¿Qué afirmación sobre la función histogram_quantile es correcta?
   - A) Solo puede utilizarse con métricas Summary
   - B) Calcula cuantiles a partir de buckets Histogram
   - C) Devuelve valores de cuantiles exactos
   - D) Calcula la tasa de cambio de las métricas Counter

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Calcula cuantiles a partir de buckets Histogram**

**Explicación:**
`histogram_quantile()` calcula cuantiles a partir de datos de buckets Histogram. Por ejemplo, `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` calcula la latencia p95. Devuelve aproximaciones basadas en los límites de los buckets; utiliza Summary para cuantiles exactos.

</details>

---

5. ¿Qué componente NO está incluido en el chart Helm kube-prometheus-stack?
   - A) Prometheus Operator
   - B) Grafana
   - C) VictoriaMetrics
   - D) Alertmanager

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) VictoriaMetrics**

**Explicación:**
kube-prometheus-stack es un chart Helm que incluye Prometheus Operator, Prometheus, Alertmanager, Grafana, kube-state-metrics, node-exporter y más. VictoriaMetrics es un proyecto independiente, instalado mediante el chart victoria-metrics-k8s-stack.

</details>

---

6. ¿Cuál es el propósito principal de Remote Write en Prometheus?
   - A) Mejorar el rendimiento del almacenamiento local
   - B) Enviar datos al almacenamiento de métricas a largo plazo
   - C) Enviar alertas en tiempo real
   - D) Sincronizar dashboards de Grafana

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Enviar datos al almacenamiento de métricas a largo plazo**

**Explicación:**
Remote Write es una funcionalidad que envía las métricas recopiladas por Prometheus a sistemas externos (VictoriaMetrics, Mimir, AMP, Cortex, etc.). Dado que el almacenamiento local de Prometheus tiene limitaciones de retención y escalabilidad, Remote Write se utiliza para enviar datos a almacenamiento especializado para la retención a largo plazo.

</details>

---

7. ¿Cuál es la función del campo `for` en el CRD PrometheusRule?
   - A) Establecer el intervalo de evaluación de reglas
   - B) Establecer la duración de la condición antes de que se active la alerta
   - C) Establecer el intervalo de reenvío de alertas
   - D) Establecer el período de retención de métricas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Establecer la duración de la condición antes de que se active la alerta**

**Explicación:**
El campo `for` en PrometheusRule establece el tiempo de espera después de que se cumpla una condición de alerta antes de que la alerta se active realmente. Por ejemplo, `for: 5m` significa que la condición debe persistir durante 5 minutos antes de que se active la alerta. Esto evita alertas innecesarias causadas por picos temporales.

</details>

---

8. ¿Cuál es el propósito de la función `predict_linear` en PromQL?
   - A) Calcular el valor absoluto del valor actual
   - B) Predecir valores futuros basándose en regresión lineal
   - C) Ordenar datos de series temporales
   - D) Transformar valores de etiquetas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Predecir valores futuros basándose en regresión lineal**

**Explicación:**
`predict_linear(v range-vector, t scalar)` utiliza regresión lineal para predecir valores futuros. Por ejemplo, `predict_linear(node_filesystem_avail_bytes[6h], 24*60*60) < 0` predice si el espacio en disco se agotará en 24 horas con la tendencia actual. Es útil para la planificación de capacidad y las alertas proactivas.

</details>

---

9. ¿Cuál es la función de la configuración `groupBy` de Alertmanager?
   - A) Enviar alertas solo a grupos específicos
   - B) Agrupar alertas por etiquetas especificadas
   - C) Establecer la prioridad de las alertas
   - D) Eliminar alertas duplicadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Agrupar alertas por etiquetas especificadas**

**Explicación:**
`groupBy` agrupa las alertas por etiquetas especificadas y las envía como una única notificación. Por ejemplo, `groupBy: ['alertname', 'namespace']` agrupa las alertas con el mismo alertname y namespace. Esto evita tormentas de alertas y permite ver juntas las alertas relacionadas.

</details>

---

10. ¿Cuál es la función de WAL (Write-Ahead Log) en Prometheus TSDB?
    - A) Caché de consultas
    - B) Registro anticipado de escritura para evitar la pérdida de datos
    - C) Almacenar el historial de alertas
    - D) Almacenar la configuración de dashboards

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Registro anticipado de escritura para evitar la pérdida de datos**

**Explicación:**
WAL (Write-Ahead Log) es un registro que guarda datos secuencialmente antes de que se escriban por completo desde la memoria en bloques de disco. Incluso si Prometheus termina de forma anómala, los datos pueden recuperarse mediante el WAL para evitar la pérdida de datos. Es un mecanismo de durabilidad utilizado habitualmente en bases de datos.

</details>
