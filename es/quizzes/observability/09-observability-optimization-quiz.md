# Cuestionario de optimización de observabilidad

> **Versiones compatibles**: Amazon EKS 1.29+, OpenTelemetry 0.90+
> **Última actualización**: February 22, 2026

Este cuestionario evalúa tu comprensión de la Guía de optimización de observabilidad de EKS. Cubre los tres pilares de la observabilidad: logging, metrics y tracing, además del monitoreo basado en eBPF y las estrategias de optimización de costos.

---

## Preguntas de opción múltiple

1. Entre los tres pilares de la observabilidad, ¿qué tipo de datos es el más adecuado para responder la pregunta «¿Por qué es lento?»?
   - A) Logging
   - B) Metrics
   - C) Tracing
   - D) Events

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Tracing**

**Explicación:**
Los tres pilares de la observabilidad responden a distintos tipos de preguntas. Logging responde «¿Qué ocurrió?», Metrics responde «¿El sistema está saludable?» y Tracing responde «¿Por qué es lento?». Tracing está optimizado para rastrear los flujos de solicitudes, comprender la causalidad y analizar los cuellos de botella. En los sistemas distribuidos, tracing es esencial al analizar la latencia de las solicitudes que atraviesan varios Services.

</details>

2. ¿Qué solución de almacenamiento de logs destaca por el filtrado rápido basado en labels y logra una alta eficiencia de costos mediante el uso de object storage (S3)?
   - A) CloudWatch Logs
   - B) OpenSearch
   - C) Loki
   - D) ClickHouse

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Loki**

**Explicación:**
Grafana Loki utiliza indexación basada en labels para proporcionar filtrado rápido sin índices de búsqueda de texto completo. Almacena datos de logs en object storage como S3, lo que reduce mucho los costos de almacenamiento (S3: $0.023/GB/month). OpenSearch es sólido en la búsqueda de texto completo, pero tiene costos elevados de almacenamiento de índices, mientras que CloudWatch Logs tiene costos de ingesta relativamente altos ($0.50/GB).

</details>

3. ¿Qué agente de logs tiene el menor uso de memoria, está escrito en C y cuenta con soporte nativo en EKS?
   - A) Fluentd
   - B) Fluent Bit
   - C) Vector
   - D) Logstash

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Fluent Bit**

**Explicación:**
Fluent Bit está escrito en C y utiliza solo unos 15MB de memoria. Es más ligero que Fluentd (~60MB, Ruby/C) o Vector (~30MB, Rust), y proporciona un alto rendimiento de hasta ~200K msg/s. AWS recomienda oficialmente Fluent Bit como el recopilador de logs para EKS y proporciona la imagen aws-for-fluent-bit.

</details>

4. ¿Cuál es la causa principal de la explosión de cardinalidad en Prometheus?
   - A) Cuando el intervalo de scrape es demasiado largo
   - B) Cuando se usan el UID de un Pod o una marca de tiempo como labels
   - C) Cuando se usan demasiadas Recording Rules
   - D) Cuando se habilita Remote Write

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuando se usan el UID de un Pod o una marca de tiempo como labels**

**Explicación:**
La cardinalidad se refiere al número de series temporales únicas. Usar valores únicos como el UID de un Pod, marcas de tiempo o IDs de solicitudes como labels hace que las combinaciones de labels crezcan infinitamente, lo que produce una explosión de series temporales. Esto provoca picos en el uso de memoria de Prometheus y degrada el rendimiento de las consultas. Se recomienda eliminar labels como pod_template_hash y controller_revision_hash en relabel_configs.

</details>

5. En la estrategia Tail Sampling de OpenTelemetry Collector, ¿qué tipo de policy conserva el 100% de los traces que contienen errores?
   - A) probabilistic
   - B) latency
   - C) status_code
   - D) string_attribute

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) status_code**

**Explicación:**
Tail Sampling toma decisiones de sampling basándose en la información completa del trace después de que este finaliza. La policy `status_code` realiza el sampling según el código de estado del trace (OK, ERROR). Configurar `status_codes: [ERROR]` conserva el 100% de los traces que contienen errores. Esta es una estrategia efectiva que conserva los traces importantes para el análisis de problemas mientras reduce el volumen total de datos.

</details>

6. ¿Cuál es la mayor ventaja del monitoreo basado en eBPF?
   - A) Puede recopilar más tipos de metrics
   - B) Puede instrumentar aplicaciones sin modificar el código
   - C) Reduce los costos de almacenamiento de metrics
   - D) Mejora el rendimiento de las consultas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Puede instrumentar aplicaciones sin modificar el código**

**Explicación:**
eBPF (extended Berkeley Packet Filter) ejecuta de forma segura programas en el kernel de Linux para observar llamadas al sistema, paquetes de red y más. La instrumentación tradicional requiere añadir SDKs, modificar el código y volver a realizar el Deployment, pero eBPF opera de forma transparente en el nivel del kernel, lo que permite el monitoreo sin cambios en la aplicación. También es independiente del lenguaje e instrumenta por igual aplicaciones escritas en cualquier lenguaje.

</details>

7. ¿Cuál es el uso principal de Cilium Hubble?
   - A) Monitoreo del uso de recursos de contenedores
   - B) Observación y análisis de flujos de red
   - C) Recopilación y almacenamiento de logs
   - D) Backend de tracing distribuido

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Observación y análisis de flujos de red**

**Explicación:**
Cilium Hubble es el componente de observabilidad de Cilium, un CNI basado en eBPF. Hubble observa en tiempo real todos los flujos de red del cluster y analiza solicitudes DNS, conexiones TCP, tráfico HTTP y más. Con el comando `hubble observe`, puedes filtrar el tráfico de Services específicos o analizar paquetes descartados. Es útil para la visualización de mapas de Services y la validación de network policies.

</details>

8. ¿Cuál es la metric principal que mide Kepler (Kubernetes Efficient Power Level Exporter)?
   - A) Temperatura de la CPU
   - B) Ancho de banda de red
   - C) Consumo de energía (joules/watts)
   - D) Latencia de Disk I/O

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Consumo de energía (joules/watts)**

**Explicación:**
Kepler es un proyecto de CNCF que utiliza eBPF para medir el consumo de energía de los contenedores y los Pods. Proporciona el consumo de energía (joules) mediante la metric `kepler_container_joules_total`, y el consumo de potencia (watts) puede calcularse con `rate(kepler_container_joules_total[5m]) * 1000`. Esto permite analizar el uso de energía por namespace o Pod, lo que ayuda a lograr objetivos de computación ecológica.

</details>

9. ¿Cuál es el método recomendado para realizar el seguimiento de costos por equipo en OpenCost/KubeCost?
   - A) Crear clusters de Kubernetes independientes para cada equipo
   - B) Estandarizar labels como cost-center y team en namespaces y Pods
   - C) Asignar AWS accounts independientes a cada equipo
   - D) Configurar únicamente ResourceQuotas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Estandarizar labels como cost-center y team en namespaces y Pods**

**Explicación:**
OpenCost asigna costos basándose en labels de Kubernetes. Al aplicar de forma coherente labels como `cost-center`, `team` y `environment` a namespaces y Pods, puedes consultar los costos por equipo mediante la API de OpenCost usando `aggregate=label:team`. Este enfoque permite un análisis detallado de costos y chargeback, a la vez que mantiene la estructura existente del cluster.

</details>

10. En el monitoreo basado en SLO (Service Level Objective), ¿qué significa «Error Budget»?
    - A) Presupuesto asignado para las operaciones del sistema de monitoreo
    - B) La cantidad de errores permitidos al desviarse de los objetivos de SLO
    - C) Costo de enviar alertas
    - D) Capacidad de almacenamiento disponible para logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La cantidad de errores permitidos al desviarse de los objetivos de SLO**

**Explicación:**
El error budget es un concepto derivado del SLO que representa la cantidad total de errores permitidos. Por ejemplo, un SLO de disponibilidad del 99.9% significa un error budget del 0.1%. En un período de 30 días, se permiten aproximadamente 43 minutos de inactividad. Cuando el error budget se agota, se deben detener los Deployments de nuevas funcionalidades para centrarse en las mejoras de estabilidad. La proporción restante del error budget puede calcularse con la expresión `1 - (1 - sli:availability:ratio) / (1 - 0.999)`.

</details>

---

## Preguntas de respuesta corta

1. ¿Cómo se llama la funcionalidad de Prometheus que mejora el rendimiento de las consultas de los dashboards al precalcular y almacenar consultas complejas?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Recording Rules

**Explicación:**
Las Recording Rules evalúan periódicamente expresiones PromQL y almacenan los resultados como nuevas series temporales. Por ejemplo, precalcular la utilización de CPU de un nodo con `record: node:cpu_utilization:ratio` permite que los dashboards consulten esta metric directamente en lugar de ejecutar consultas complejas, lo que resulta en respuestas más rápidas. Se definen mediante el campo `record` en el CRD PrometheusRule.

</details>

2. En OpenTelemetry, ¿cómo se llama el método de sampling que toma decisiones basándose en la información completa del trace después de que este finaliza?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Tail Sampling

**Explicación:**
Tail Sampling toma decisiones de sampling después de que han llegado todos los spans de un trace. Esto contrasta con Head Sampling (sampling probabilístico), que toma decisiones al inicio del trace. La ventaja de Tail Sampling es que puede conservar selectivamente solo los traces con errores o alta latencia. Sin embargo, dado que todos los spans deben mantenerse en memoria antes de tomar una decisión, las configuraciones `decision_wait` y `num_traces` son importantes.

</details>

3. ¿Cuál es la funcionalidad de Prometheus que vincula IDs de traces con puntos de datos de metrics, lo que permite navegar directamente de las metrics a los traces?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Exemplars

**Explicación:**
Exemplars es una funcionalidad que adjunta contexto adicional (normalmente traceID) a las muestras de metrics. Cuando se añaden exemplars a metrics de histogram o counter, puedes hacer clic en un punto específico del gráfico de metrics en Grafana para navegar directamente al trace de ese momento. Esto facilita el análisis de correlación entre datos de observabilidad y permite analizar en el trace «por qué la latencia aumentó en este punto».

</details>

4. En el modo cluster de VictoriaMetrics, ¿cómo se llama el componente responsable del almacenamiento de datos de metrics?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** vmstorage

**Explicación:**
El modo cluster de VictoriaMetrics consta de tres componentes. vminsert gestiona la recopilación y distribución de metrics, vmselect gestiona el procesamiento de consultas y vmstorage gestiona el almacenamiento real de datos de metrics. vmstorage puede escalar horizontalmente con varias instancias y proporciona alta disponibilidad mediante replicación. Esta arquitectura separada permite el escalado independiente de las cargas de trabajo de ingesta, almacenamiento y consultas.

</details>

5. ¿Cómo se llama la estrategia para reducir los costos de almacenamiento de logs/metrics al trasladar los datos más antiguos a almacenamiento de bajo costo como S3 Glacier?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Tiered Storage

**Explicación:**
La estrategia de tiered storage almacena los datos en diferentes niveles de almacenamiento según su importancia y frecuencia de acceso. Los datos recientes se almacenan en almacenamiento de alto rendimiento (SSD, EBS), los datos a medio plazo en S3 Standard-IA y los datos de archivo a largo plazo en S3 Glacier Deep Archive. Esto puede reducir los costos de almacenamiento en un 70-90%. Las soluciones basadas en object storage como Loki y Tempo admiten esta estrategia de forma predeterminada.

</details>

---

## Preguntas prácticas

1. Escribe una configuración de Fluent Bit para filtrar y excluir los logs de nivel DEBUG y TRACE.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
```ini
[FILTER]
    Name     grep
    Match    *
    Exclude  log ^.*DEBUG.*$
    Exclude  log ^.*TRACE.*$
```

O usando expresiones regulares:
```ini
[FILTER]
    Name     grep
    Match    *
    Exclude  log (DEBUG|TRACE)
```

**Explicación:**
El filtro grep de Fluent Bit utiliza expresiones regulares para filtrar logs. La directiva `Exclude` excluye los logs que coinciden con el patrón. Filtrar logs DEBUG/TRACE en entornos de producción puede reducir el volumen de logs en un 40-60%, reduciendo significativamente los costos de almacenamiento. Sin embargo, los logs DEBUG se pueden habilitar selectivamente para Services específicos cuando se necesite solucionar problemas.

</details>

2. Escribe una PrometheusRule que active una advertencia cuando la tasa de errores HTTP por Service supere el 5% y persista durante 5 minutos.

<details>
<summary>Mostrar respuesta</summary>

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
Esta regla de alerta calcula la proporción de códigos de estado 5XX por Service. `status=~"5.."` es una regex que coincide con los códigos de estado 500-599. `for: 5m` activa la alerta únicamente cuando la condición persiste durante 5 minutos, lo que evita alertas falsas por picos temporales. El uso de `sum by (service)` genera alertas independientes para cada Service.

</details>

3. Escribe una configuración del processor tail_sampling para OpenTelemetry Collector que muestree al 100% los traces con errores, al 100% los traces con latencia superior a 1 segundo y el resto solo al 10%.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
processors:
  tail_sampling:
    decision_wait: 10s
    num_traces: 100000
    policies:
      # Keep 100% of traces with errors
      - name: errors-policy
        type: status_code
        status_code:
          status_codes: [ERROR]

      # Keep 100% of traces with latency over 1 second
      - name: slow-traces-policy
        type: latency
        latency:
          threshold_ms: 1000

      # Sample only 10% of the rest
      - name: default-policy
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
```

**Explicación:**
Las policies de Tail Sampling se evalúan en orden y, si alguna policy coincide, el trace se conserva. `decision_wait` es el tiempo de espera para que el trace se complete y requiere tiempo suficiente para que lleguen todos los spans. `num_traces` es el número máximo de traces que se mantienen en memoria. Esta configuración puede reducir el volumen total de datos en aproximadamente un 90%, mientras conserva los traces importantes para el análisis de errores y rendimiento.

</details>

---

## Preguntas avanzadas

1. Diseña una arquitectura para lograr alta disponibilidad del stack de observabilidad en un cluster de EKS a gran escala (más de 500 nodos). Explica qué componentes se deben desplegar y cómo, para cada capa: recopilación, almacenamiento y consulta.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Capa de recopilación de datos:**
- Fluent Bit: realizar el Deployment como DaemonSet en cada nodo (límite de memoria de 100-200Mi)
- OTel Collector: realizar el Deployment como DaemonSet con un load balancer delante
- Redundancia de Collector: al menos 2+ instancias de Collector por AZ

**Capa de almacenamiento:**
- Logs: modo Loki Simple Scalable
  - Ruta de escritura: 2+ réplicas (distribuidas entre AZ)
  - Ruta de lectura: 2+ réplicas (load balancing de consultas)
  - Backend: S3 (durabilidad del 99.999999999%)

- Metrics: cluster de VictoriaMetrics o AMP
  - vminsert: 2+ réplicas (load balancing de escritura)
  - vmstorage: 3+ réplicas (factor de replicación 2)
  - vmselect: 2+ réplicas (load balancing de lectura)

- Traces: Grafana Tempo
  - Distributor: 2+ réplicas
  - Ingester: 3+ réplicas (WAL habilitado)
  - Backend: S3

**Capa de consultas:**
- Grafana: 2+ réplicas, PostgreSQL/MySQL externo para almacenamiento de sesiones
- Caching: caché de resultados de consultas con Redis/Memcached

**Consideraciones clave:**
1. Realizar el Deployment de todos los componentes con estado entre varias AZ
2. Usar S3 como almacenamiento compartido (eliminar el punto único de fallo)
3. Sharding de Prometheus (3-5 shards) + Remote Write para descargar datos al almacenamiento central
4. PodDisruptionBudget para garantizar la disponibilidad durante actualizaciones graduales

</details>

2. En un entorno con $5,000/month en costos de observabilidad, propón estrategias de optimización para lograr una reducción de costos del 50% manteniendo la calidad. Explica métodos específicos para cada área: logging, metrics y tracing.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

**Optimización de logging (ahorro esperado: $1,500-2,000)**

1. **Filtrado por nivel de logs** (reducción del 40-60%)
   - Excluir logs DEBUG/TRACE en el entorno de producción
   - Implementación: filtro grep de Fluent Bit con `Exclude log (DEBUG|TRACE)`

2. **Aplicar sampling** (reducción del 30-50%)
   - Sampling del 10% para logs de alta frecuencia (logs de acceso, health checks)
   - Implementación: filtro throttle de Fluent Bit `Rate 10, Window 60`

3. **Optimización del período de retención** (reducción del 20-40%)
   - Producción: 14 días, Dev/Staging: 7 días
   - Retención a largo plazo únicamente para logs importantes (trasladarlos a S3 Glacier)

4. **Migración de almacenamiento** (reducción del 50-70%)
   - CloudWatch Logs ($0.50/GB de ingesta) -> Loki + S3 ($0.023/GB de almacenamiento)

**Optimización de metrics (ahorro esperado: $500-800)**

1. **Gestión de cardinalidad**
   - Eliminar labels innecesarios (pod_template_hash, controller_revision_hash)
   - Descartar metrics: excluir metrics internas como `go_.*`, `promhttp_.*`

2. **Ajuste del intervalo de scrape**
   - Metrics críticas: 15s, metrics generales: 30s-60s
   - Limitar buckets de histogram (eliminar valores le innecesarios)

3. **Utilizar Recording Rules**
   - Precalcular consultas de agregación usadas con frecuencia
   - Eliminación temprana de datos originales de alta resolución (7 días -> 3 días)

4. **Migración de almacenamiento**
   - Prometheus autogestionado -> VictoriaMetrics (proporción de compresión de 7x)
   - O usar AMP (eliminar la carga operativa, costos predecibles)

**Optimización de tracing (ahorro esperado: $500-1,000)**

1. **Aplicar Tail Sampling** (reducción del 80-90%)
   - Traces con errores/lentos: retención del 100%
   - Traces normales: sampling de solo el 5-10%

2. **Migración de almacenamiento**
   - X-Ray ($5/million traces) -> Tempo + S3 (solo costos de almacenamiento)

3. **Optimización del período de retención**
   - Traces detallados: 7 días
   - Datos agregados: 30 días

**Ahorro total esperado: $2,500-3,800 (50-76%)**

La clave es la clasificación por importancia. En lugar de tratar todos los datos por igual, reduce los datos agresivamente mientras conservas lo necesario para el análisis de problemas.

</details>

---

**Cálculo de la puntuación:**
- 18-20 respuestas correctas: Excelente (nivel experto en observabilidad)
- 14-17 respuestas correctas: Bueno (aplicable en la práctica)
- 10-13 respuestas correctas: Promedio (se recomienda estudio adicional)
- 6-9 respuestas correctas: Básico (revisar conceptos fundamentales)
- 0-5 respuestas correctas: Insuficiente (se necesita una revisión completa del contenido)

---

**Materiales de aprendizaje relacionados:**
- [Guía de optimización de observabilidad de EKS](../../observability/09-observability-optimization.md)
