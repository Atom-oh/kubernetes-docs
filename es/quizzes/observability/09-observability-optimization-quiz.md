# Cuestionario de optimización de observabilidad

> **Versiones de ejemplo validadas**: Prometheus 3.14.0 · OTel Collector Contrib 0.160.0

> **Última actualización**: September 13, 2026

Este cuestionario evalúa tu comprensión de la guía de optimización de observabilidad de EKS. Cubre los tres pilares de la observabilidad —registro, métricas y trazado—, así como el monitoreo basado en eBPF y las estrategias de optimización de costos.

---

## Preguntas de opción múltiple

1. Entre los tres pilares de la observabilidad, ¿qué tipo de datos es más adecuado para responder a la pregunta «¿Por qué es lento?»?
   - A) Registro
   - B) Métricas
   - C) Trazado
   - D) Eventos

<details>
<summary>Ver respuesta</summary>

**Respuesta: C) Trazado**

**Explicación:**
Los tres pilares de la observabilidad responden a distintos tipos de preguntas. El registro responde «¿Qué ocurrió?», las métricas responden «¿El sistema está saludable?» y el trazado responde «¿Por qué es lento?». El trazado está optimizado para rastrear flujos de solicitudes con el fin de comprender la causalidad y analizar cuellos de botella. En sistemas distribuidos, el trazado es esencial al analizar la latencia de solicitudes que atraviesan múltiples Services.

</details>

2. ¿Qué solución de almacenamiento de logs destaca en el filtrado rápido basado en etiquetas y logra una alta eficiencia de costos al utilizar almacenamiento de objetos (S3)?
   - A) CloudWatch Logs
   - B) OpenSearch
   - C) Loki
   - D) ClickHouse

<details>
<summary>Ver respuesta</summary>

**Respuesta: C) Loki**

**Explicación:**
Loki utiliza indexación de etiquetas y almacenamiento de objetos, pero el costo total incluye cómputo, cachés, solicitudes a objetos, consultas y operaciones. Compara la misma Region, volumen, retención y disponibilidad en lugar de considerar el precio de almacenamiento de S3 como el costo total.

</details>

3. ¿Qué agente basado en C puede recopilar logs en EKS?
   - A) Fluentd
   - B) Fluent Bit
   - C) Vector
   - D) Logstash

<details>
<summary>Ver respuesta</summary>

**Respuesta: B) Fluent Bit**

**Explicación:**
Fluent Bit es un recopilador basado en C que puede utilizarse en implementaciones de AWS. La memoria y el rendimiento dependen de la versión, los analizadores, el tamaño de los registros, el almacenamiento en búfer y el hardware; las afirmaciones fijas de 15 MB o 200K msg/s no son garantías.

</details>

4. ¿Cuál es la causa principal de la explosión de cardinalidad en Prometheus?
   - A) Cuando el intervalo de scrape es demasiado largo
   - B) Cuando se usan Pod UID o marca de tiempo como etiquetas
   - C) Cuando se usan demasiadas Recording Rules
   - D) Cuando se habilita Remote Write

<details>
<summary>Ver respuesta</summary>

**Respuesta: B) Cuando se usan Pod UID o marca de tiempo como etiquetas**

**Explicación:**
Cambiar las etiquetas de ID de solicitud/marca de tiempo incrementa el número de series. Limita las etiquetas en el origen y verifica la unicidad. labeldrop no agrega muestras y puede crear colisiones; el relabeling de destinos y el relabeling de métricas se ejecutan en distintas etapas.

</details>

5. En la estrategia Tail Sampling de OpenTelemetry Collector, ¿qué tipo de política selecciona los trazos recibidos que contienen un span ERROR?
   - A) probabilistic
   - B) latency
   - C) status_code
   - D) string_attribute

<details>
<summary>Ver respuesta</summary>

**Respuesta: C) status_code**

**Explicación:**
La política status_code de ERROR selecciona trazos utilizando spans de error recibidos por ese sampler. La afinidad de trazos, el momento de la decisión, los límites de búfer, los spans tardíos y el head sampling ascendente impiden garantizar que se retenga cada solicitud fallida.

</details>

6. ¿Cuál es la mayor ventaja del monitoreo basado en eBPF?
   - A) Puede recopilar más tipos de métricas
   - B) Puede instrumentar aplicaciones sin modificar el código
   - C) Reduce los costos de almacenamiento de métricas
   - D) Mejora el rendimiento de las consultas

<details>
<summary>Ver respuesta</summary>

**Respuesta: B) Puede instrumentar aplicaciones sin modificar el código**

**Explicación:**
Puede reducir los cambios en el código fuente para kernels, runtimes y protocolos compatibles, pero no cubre por igual todos los lenguajes, bibliotecas TLS o spans de negocio. Valida los permisos, la sobrecarga y las cargas útiles sensibles; la auto-instrumentación de SDK también puede evitar cambios en el código fuente.

</details>

7. ¿Cuál es el uso principal de Cilium Hubble?
   - A) Monitoreo del uso de recursos de contenedores
   - B) Observación y análisis de flujos de red
   - C) Recopilación y almacenamiento de logs
   - D) Backend de trazado distribuido

<details>
<summary>Ver respuesta</summary>

**Respuesta: B) Observación y análisis de flujos de red**

**Explicación:**
Hubble observa flujos de red en una implementación compatible de Cilium. La visibilidad de L7 depende de los protocolos y de la configuración del proxy/la política. Verifica la cobertura real en lugar de prometer todos los flujos o el trazado completo de la aplicación.

</details>

8. ¿Cuál es la métrica principal que mide Kepler (Kubernetes Efficient Power Level Exporter)?
   - A) Temperatura de CPU
   - B) Ancho de banda de red
   - C) Energía (julios) y potencia (vatios)
   - D) Latencia de I/O de disco

<details>
<summary>Ver respuesta</summary>

**Respuesta: C) Energía (julios) y potencia (vatios)**

**Explicación:**
Kepler 0.10+ difiere de la versión heredada 0.7. En 0.11.4, kepler_pod_cpu_watts es un gauge de potencia y rate(kepler_pod_cpu_joules_total[5m]) es J/s=W. Multiplicar por 1000 proporciona milivatios. Verifica el acceso al hardware y el soporte de atribución.

</details>

9. ¿Cuál es el método recomendado para rastrear los costos por equipo en OpenCost/KubeCost?
   - A) Crear clusters de Kubernetes independientes por equipo
   - B) Estandarizar etiquetas como cost-center y team en namespaces y Pods
   - C) Asignar cuentas de AWS independientes a cada equipo
   - D) Configurar únicamente ResourceQuotas

<details>
<summary>Ver respuesta</summary>

**Respuesta: B) Estandarizar etiquetas como cost-center y team en namespaces y Pods**

**Explicación:**
OpenCost asigna costos según las etiquetas de Kubernetes. Al aplicar de manera coherente etiquetas como `cost-center`, `team` y `environment` a namespaces y Pods, puedes consultar los costos por equipo mediante la API de OpenCost con `aggregate=label:team`. Este enfoque permite un análisis detallado de costos y chargeback mientras mantiene la estructura actual del cluster.

</details>

10. En el monitoreo basado en SLO (Service Level Objective), ¿qué significa «Error Budget»?
    - A) Presupuesto asignado para las operaciones del sistema de monitoreo
    - B) La cantidad de errores permitidos al desviarse de los objetivos de SLO
    - C) Costo de enviar alertas
    - D) Capacidad de almacenamiento disponible para logs

<details>
<summary>Ver respuesta</summary>

**Respuesta: B) La cantidad de errores permitidos al desviarse de los objetivos de SLO**

**Explicación:**
Para un SLO basado en solicitudes de 99.9%, las solicitudes incorrectas permitidas equivalen al total de solicitudes×0.001 durante la ventana definida. No lo confundas con tiempo de inactividad basado en el tiempo. El presupuesto restante de 30 días requiere una proporción de errores ponderada por solicitudes de 30 días, no la proporción más reciente de cinco minutos.

</details>

---

## Preguntas de respuesta corta

1. ¿Cuál es el nombre de la característica de Prometheus que mejora el rendimiento de las consultas de dashboards al precalcular y almacenar consultas complejas?

<details>
<summary>Ver respuesta</summary>

**Respuesta:** Recording Rules

**Explicación:**
Las Recording Rules evalúan periódicamente expresiones PromQL y almacenan los resultados como nuevas series temporales. Por ejemplo, precalcular la utilización de CPU del nodo con `record: node:cpu_utilization:ratio` permite que los dashboards consulten esta métrica directamente en lugar de ejecutar consultas complejas, lo que resulta en respuestas más rápidas. Se definen mediante el campo `record` en el CRD PrometheusRule.

</details>

2. En OpenTelemetry, ¿cómo se llama el método de sampling que recopila spans durante una ventana de decisión y realiza el muestreo utilizando los resultados observados?

<details>
<summary>Ver respuesta</summary>

**Respuesta:** Tail Sampling

**Explicación:**
El sampling predeterminado de trazos completos decide utilizando spans recibidos durante su ventana de decisión. No puede demostrar la finalización ni la llegada de todos los spans; considera afinidad, búferes, spans tardíos, reinicios y sampling ascendente.

</details>

3. ¿Cuál es la característica de Prometheus que vincula los ID de trazos con puntos de datos de métricas y permite la navegación directa de métricas a trazos?

<details>
<summary>Ver respuesta</summary>

**Respuesta:** Exemplars

**Explicación:**
Exemplars es una característica que adjunta contexto adicional (normalmente traceID) a las muestras de métricas. Cuando se añaden exemplars a métricas de histogramas o contadores, puedes hacer clic en un punto específico del gráfico de métricas en Grafana para navegar directamente al trazo de ese momento. Esto facilita el análisis de correlación entre datos de observabilidad, lo que te permite analizar en el trazo «por qué la latencia tuvo un pico en este punto».

</details>

4. En el modo cluster de VictoriaMetrics, ¿cuál es el nombre del componente responsable del almacenamiento de datos de métricas?

<details>
<summary>Ver respuesta</summary>

**Respuesta:** vmstorage

**Explicación:**
vmstorage almacena los datos. Múltiples instancias por sí solas no establecen replicación: configura los factores de replicación, el comportamiento de vminsert/vmselect, la deduplicación de consultas y el manejo de fallos.

</details>

5. ¿Cómo se llama la estrategia para reducir los costos de almacenamiento de logs/métricas moviendo los datos más antiguos a almacenamiento de bajo costo como S3 Glacier?

<details>
<summary>Ver respuesta</summary>

**Respuesta:** Almacenamiento por niveles

**Explicación:**
La clasificación por niveles depende de la frecuencia de acceso, el retraso de restauración y la retención. Mover bloques activos de Loki/Tempo a Glacier puede interrumpir las consultas; valida la compatibilidad/recuperación o utiliza un archivo independiente. Los ahorros no son un porcentaje fijo.

</details>

---

## Preguntas prácticas

1. Escribe una configuración de Fluent Bit para filtrar y excluir logs de nivel DEBUG y TRACE.

<details>
<summary>Ver respuesta</summary>

**Respuesta:**
```ini
[FILTER]
    Name     grep
    Match    *
    Exclude  level ^(DEBUG|TRACE)$
```

**Explicación:**
Haz coincidir ^(DEBUG|TRACE)$ en un campo level analizado en lugar de texto arbitrario del mensaje. Mide las pérdidas y el impacto en la investigación de incidentes; no se garantizan ahorros del 40–60%.

</details>

2. Escribe una PrometheusRule que active una advertencia cuando la tasa de errores HTTP por Service supere el 5% y persista durante 5 minutos.

<details>
<summary>Ver respuesta</summary>

**Respuesta:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: http-error-rate-alert
  namespace: monitoring
spec:
  groups:
    - name: slo.alerts
      rules:
        - alert: HighHTTPErrorRate
          expr: |
            sum by (service) (
              rate(http_requests_total{status=~"5.."}[5m])
            )
            /
            sum by (service) (
              rate(http_requests_total[5m])
            )
            > 0.05
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "HTTP error rate for service {{ $labels.service }} exceeded 5%"
            description: "Current error rate: {{ $value | humanizePercentage }}"
```

**Explicación:**
Esta regla de alerta calcula la proporción de códigos de estado 5XX por Service. `status=~"5.."` es una expresión regular que coincide con los códigos de estado 500-599. `for: 5m` activa la alerta únicamente cuando la condición persiste durante 5 minutos, lo que evita alertas falsas por picos temporales. El uso de `sum by (service)` genera alertas independientes para cada Service.

</details>

3. Escribe una configuración del procesador tail_sampling para OpenTelemetry Collector que muestree los trazos de error al 100%, los trazos con latencia superior a 1 segundo al 100% y el resto solo al 10%.

<details>
<summary>Ver respuesta</summary>

**Respuesta:**
```yaml
processors:
  tail_sampling:
    decision_wait: 2s
    num_traces: 1000
    maximum_trace_size_bytes: 1048576
    policies:
    - name: errors
      type: status_code
      status_code:
        status_codes:
        - ERROR
    - name: slow
      type: latency
      latency:
        threshold_ms: 1000
    - name: baseline
      type: probabilistic
      probabilistic:
        sampling_percentage: 10
```

**Explicación:**
Estas políticas positivas retienen los trazos de error/lentos recibidos que coinciden y muestrean probabilísticamente el resto. Se mantienen los límites de búfer, afinidad y spans tardíos. La retención total depende de la proporción de errores/trazos lentos; no se garantiza una reducción del 90%. No generalices la semántica de primera coincidencia a las políticas drop/composite.

</details>

---

## Preguntas avanzadas

1. Diseña una arquitectura para lograr alta disponibilidad de la pila de observabilidad en un cluster de EKS a gran escala (más de 500 nodos). Explica qué componentes deben implementarse y cómo en cada capa: recopilación, almacenamiento y consulta.

<details>
<summary>Ver respuesta</summary>

**Respuesta:**

No derives los recuentos de réplicas únicamente del número de nodos. Separa los agentes de logs de nodos y los gateways, enruta Tail Sampling por ID de trazo y mide el almacenamiento en búfer/la contrapresión y las pérdidas. Sigue los requisitos actuales de replicación/quórum/AZ del modo Loki/Tempo; configura la replicación/deduplicación de consultas de VictoriaMetrics y las cuotas/retención de AMP. Presupuesta PVC/memoria para réplicas×shards de Prometheus y combina las consultas de shards. Grafana necesita una base de datos compartida y Alerting HA independiente; verifica el soporte de la edición para el caché de consultas. Los PDB y la durabilidad de S3 no garantizan disponibilidad de extremo a extremo; prueba los fallos y la recuperación.

</details>

2. En un entorno con $5,000/mes en costos de observabilidad, propón estrategias de optimización para lograr una reducción de costos del 50% manteniendo la calidad. Explica métodos específicos para cada área: logs, métricas y trazos.

<details>
<summary>Ver respuesta</summary>

**Respuesta:**

La línea base de $5,000 y el objetivo del 50% son hipotéticos. Atribuye los costos de ingesta, almacenamiento, escaneo, cómputo y operación antes de optimizar la categoría más grande. Prueba por separado el filtrado por nivel analizado, el muestreo probabilístico a nivel de solicitud, la reducción segura de métricas/buckets, Tail Sampling y la retención. El throttling no es un sampler del 10%, y las Recording Rules no cambian la retención de datos sin procesar. Compara los costos completos con los mismos requisitos de Region, disponibilidad, consulta y retención. Los ahorros se superponen; evalúa la factura, la pérdida de datos, la cobertura de SLO y el éxito de la investigación en lugar de sumar porcentajes. Si el objetivo no está establecido, informa la evidencia y el siguiente experimento.

</details>

---

**Cálculo de puntuación:**
- 18-20 respuestas correctas: Excelente (nivel experto en observabilidad)
- 14-17 respuestas correctas: Bueno (aplicable en la práctica)
- 10-13 respuestas correctas: Promedio (se recomienda estudio adicional)
- 6-9 respuestas correctas: Básico (revisa los conceptos fundamentales)
- 0-5 respuestas correctas: Insuficiente (se necesita revisar todo el contenido)

---

**Materiales de aprendizaje relacionados:**
- [EKS Observability Optimization Guide](../../observability/09-observability-optimization.md)
