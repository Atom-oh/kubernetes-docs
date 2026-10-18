# Parte 7: Supervisión

> **Base de revisión**: Strimzi 1.3.0 / Kafka 4.3.1, JMX Exporter 1.6.0 y Kafka Exporter 1.10.0 incluidos, Prometheus Operator 0.94.1, KEDA 2.21.0\
> **Última revisión**: 16 de octubre de 2026

## Qué observa cada componente

| Componente | Función |
| --- | --- |
| JMX Prometheus Exporter | Asigna MBeans de la JVM en proceso a métricas de Prometheus como agente de Java |
| Strimzi Metrics Reporter | Otro `metricsConfig.type` compatible; expone directamente las métricas de Kafka con su propia configuración y nomenclatura |
| Kafka Exporter | Usa las API de Kafka para exponer los offsets y el retraso de los grupos de consumidores, además de información sobre los temas |
| Prometheus / Prometheus Operator | Detecta y recopila métricas de los destinos, evalúa reglas y pasa las alertas a Alertmanager |
| KEDA Kafka scaler | Consulta las API de Kafka para escalar; no necesita el endpoint de Prometheus del exportador de retrasos |

Este capítulo elige **`jmxPrometheusExporter`**. Sus reglas de mapeo no son lo mismo
que el remapeo de etiquetas de los destinos de Prometheus. También se admite
`strimziMetricsReporter`, así que es incorrecto afirmar que JMX es la única opción.
Para cambiar el tipo de exportador, hay que revisar los nombres de las métricas y los paneles.

Los ejemplos se basan en la [Parte 2](./02-strimzi-operator.md): el espacio de nombres `kafka`,
`my-cluster`, tres Pods de broker, tres Pods de controlador y el tema `orders` de 12 particiones.
Sus grupos de nodos etiquetan los Pods con `docs.example.com/kafka-role: broker` o
`controller`. Prometheus Operator y KEDA ya deben estar instalados.

## Habilitar las métricas JMX sin reemplazar la especificación del clúster

Guarde lo siguiente como `metrics-config.yaml`. Estas reglas específicas exponen métricas
de replicación, la proporción de inactividad del gestor de solicitudes de un broker y
contadores de caudal/ISR. Los nombres de los contadores terminan en `_total`; use
`rate()` con los contadores, no con una tasa ya calculada.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kafka-metrics
  namespace: kafka
data:
  kafka-metrics-config.yml: |
    lowercaseOutputName: true
    rules:
    - pattern: kafka.server<type=ReplicaManager, name=(UnderReplicatedPartitions|UnderMinIsrPartitionCount)><>Value
      name: kafka_server_replicamanager_$1
      type: GAUGE
    - pattern: kafka.controller<type=KafkaController, name=(ActiveControllerCount|OfflinePartitionsCount)><>Value
      name: kafka_controller_kafkacontroller_$1
      type: GAUGE
    - pattern: kafka.server<type=KafkaRequestHandlerPool, name=BrokerRequestHandlerAvgIdlePercent><>MeanRate
      name: kafka_server_kafkarequesthandlerpool_brokerrequesthandleravgidle_percent
      type: GAUGE
    - pattern: kafka.server<type=BrokerTopicMetrics, name=(BytesIn|BytesOut)PerSec, topic=(.+)><>Count
      name: kafka_server_brokertopicmetrics_$1_total
      type: COUNTER
      labels:
        topic: $2
    - pattern: kafka.server<type=ReplicaManager, name=(IsrShrinks|IsrExpands)PerSec><>Count
      name: kafka_server_replicamanager_$1_total
      type: COUNTER
```

Guarde esto como **`metrics.patch.yaml`**. Es un parche merge para el recurso Kafka
existente, no un recurso completo que se deba crear/aplicar. Se conservan los listeners,
la autenticación, el almacenamiento y el resto de la configuración.

```yaml
spec:
  kafka:
    metricsConfig:
      type: jmxPrometheusExporter
      valueFrom:
        configMapKeyRef:
          name: kafka-metrics
          key: kafka-metrics-config.yml
  kafkaExporter:
    topicRegex: ^orders$
    groupRegex: ^order-processor$
    showAllOffsets: true
    template:
      pod:
        metadata:
          labels:
            docs.example.com/kafka-monitor: lag
```

La primera sección habilita el agente JMX en proceso. La segunda despliega el
**Kafka Exporter** de Strimzi, cuya implementación y nombres de métricas difieren de
los de `seglo/kafka-lag-exporter`. Ese proyecto anterior está archivado; este capítulo
no lo recomienda como opción predeterminada actual.

Strimzi gestiona la conexión del exportador y el material de certificados para su
listener Kafka interno; no lo sustituya por una dirección 9092 sin autenticación. Esta
versión del exportador usa el puerto **9404**, llamado **`tcp-prometheus`**, igual que los
endpoints de métricas de los nodos Kafka. Kafka Exporter es una carga de trabajo independiente.

`KafkaConnect` y `KafkaMirrorMaker2` tienen su propia configuración de métricas.
Cruise Control se configura en `Kafka.spec.cruiseControl`; no es un CRD
`CruiseControl` independiente. No reutilice sin más las reglas de MBean de Kafka para todos los componentes.

## Detectar los destinos previstos

Guarde el archivo como `podmonitors.yaml`. Los destinos de los nodos y del exportador de retraso
se seleccionan por separado. El remapeo de etiquetas crea un contexto estable de
`namespace`, `kafka_cluster`, `kafka_component` y, para los nodos de Kafka, `kafka_role`
para las consultas.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: kafka-node-metrics
  namespace: kafka
  labels:
    release: kube-prometheus-stack
spec:
  namespaceSelector:
    matchNames:
    - kafka
  selector:
    matchLabels:
      strimzi.io/cluster: my-cluster
    matchExpressions:
    - key: docs.example.com/kafka-role
      operator: In
      values:
      - broker
      - controller
  podMetricsEndpoints:
  - port: tcp-prometheus
    path: /metrics
    interval: 30s
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_namespace
      targetLabel: namespace
    - sourceLabels:
      - __meta_kubernetes_pod_label_strimzi_io_cluster
      targetLabel: kafka_cluster
    - targetLabel: kafka_component
      replacement: nodes
    - sourceLabels:
      - __meta_kubernetes_pod_label_docs_example_com_kafka_role
      targetLabel: kafka_role
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: kafka-group-lag
  namespace: kafka
  labels:
    release: kube-prometheus-stack
spec:
  namespaceSelector:
    matchNames:
    - kafka
  selector:
    matchLabels:
      strimzi.io/cluster: my-cluster
      docs.example.com/kafka-monitor: lag
  podMetricsEndpoints:
  - port: tcp-prometheus
    path: /metrics
    interval: 30s
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_namespace
      targetLabel: namespace
    - sourceLabels:
      - __meta_kubernetes_pod_label_strimzi_io_cluster
      targetLabel: kafka_cluster
    - targetLabel: kafka_component
      replacement: lag
```

La etiqueta `release` debe coincidir con los selectores de PodMonitor/PrometheusRule
del recurso Prometheus. Sus selectores de espacios de nombres y RBAC también deben permitir
detectar recursos en `kafka`. Compruebe las políticas de red y el acceso al puerto
desde Prometheus a estos pods.

Un **ServiceMonitor** correctamente configurado también funciona con un Service
coincidente. Que se use PodSet o StatefulSet no determina si ServiceMonitor puede
funcionar. Aquí se elige PodMonitor para detectar directamente los Pods; no es un
protocolo intrínsecamente más fiable. Recopile las métricas de cada endpoint una sola vez;
elimine las rutas de detección duplicadas y deduplique las réplicas de Prometheus de alta
disponibilidad antes de agregar una vista federada.

## Interpretar las métricas en contexto

| Métrica de esta asignación | Interpretación |
| --- | --- |
| `kafka_server_replicamanager_underreplicatedpartitions` | Normalmente es cero; puede aumentar durante fallos, retrasos o mantenimiento planificado. Compruebe la duración y las particiones afectadas |
| `kafka_server_replicamanager_underminisrpartitioncount` | Particiones por debajo del ISR mínimo configurado; es importante para la disponibilidad de escritura con `acks=all` |
| `kafka_controller_kafkacontroller_activecontrollercount` | La suma de esta métrica en los Pods de controladores de un clúster debe estabilizarse en uno; verifique la cobertura de muestras y las recopilaciones duplicadas u obsoletas |
| `kafka_controller_kafkacontroller_offlinepartitionscount` | Particiones sin un líder disponible; investigue la disponibilidad |
| `kafka_server_kafkarequesthandlerpool_brokerrequesthandleravgidle_percent` | Proporción de tipo gauge, normalmente de 0 a 1. Los valores bajos requieren correlación con CPU, GC, E/S y latencia de solicitudes, no un diagnóstico automático |
| `kafka_server_brokertopicmetrics_bytesin_total` / `bytesout_total` | Contadores de bytes por tema; use `rate` para obtener la tasa de transferencia |
| `kafka_server_replicamanager_isrshrinks_total` / `isrexpands_total` | Contadores de cambios del ISR; correlacione las fluctuaciones con el estado de la replicación |

Que la suma de esta métrica supere uno es una **observación** anómala,
no una prueba de split brain: primero hay que comprobar la agregación entre clústeres,
los destinos duplicados, los tiempos de recopilación y las muestras obsoletas. La ausencia
de muestras no equivale a cero. La infrareplicación por sí sola tampoco significa que se hayan
perdido datos.

Tasa de ingesta por tema:

```promql
sum by (namespace, kafka_cluster, topic) (
  rate(kafka_server_brokertopicmetrics_bytesin_total{
    namespace="kafka",kafka_cluster="my-cluster"
  }[5m])
)
```

El tráfico agregado por tema no permite identificar qué partición tiene una carga elevada.
Añada observaciones de particiones y clientes con el alcance adecuado al investigar una
distribución desigual. Este mapeo específico no incluye el conjunto completo de métricas
de los paneles del proyecto original.

## El retraso del consumidor es la distancia entre offsets confirmados

Para cada partición, el retraso normalmente es el **offset siguiente del final del log
menos el offset siguiente confirmado por el grupo**. Es una distancia entre offsets, no
siempre un recuento de registros de negocio: influyen la compactación, los saltos de
offset y las transacciones. Una confirmación anterior al procesamiento duradero puede
hacer que el retraso parezca saludable aunque el trabajo siga sin terminar.

El mapeo de MBeans de JMX no realiza por sí mismo las consultas de offsets de
grupos/particiones necesarias para esta medición. Kafka Exporter de Strimzi proporciona
`kafka_consumergroup_lag`, con las etiquetas `consumergroup`, `topic` y `partition`.
No consulte el nombre `kafka_consumergroup_group_lag` del exportador archivado ni
suponga que aquí se aplica la etiqueta `group`.

```promql
sum by (namespace, kafka_cluster, consumergroup, topic) (
  kafka_consumergroup_lag{
    namespace="kafka",kafka_cluster="my-cluster",
    topic="orders",consumergroup="order-processor"
  } >= 0
)
```

El filtro excluye del total de retraso acumulado los valores negativos o desconocidos;
no debe ocultar datos no disponibles. Supervise por separado el estado del exportador,
la ausencia de los grupos esperados y `kafka_consumergroup_current_offset < 0`. Los
grupos sin confirmaciones, los fallos de autenticación y los temas excluidos por filtros
pueden producir resultados ausentes.
Un retraso de cero en los offsets confirmados no equivale a un SLO de procesamiento de
extremo a extremo.

## Las alertas también deben detectar datos ausentes

Guarde el archivo como `alerts.yaml`. Los recuentos previstos —seis nodos de Kafka y
tres controladores— coinciden con la topología de este capítulo. Actualícelos si cambia
los grupos de nodos. La alerta que supervisa el grupo y el tema presupone que se espera
que `order-processor` confirme offsets en `orders`; ajuste su alcance y el período de
gracia inicial a las necesidades de su aplicación.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kafka-alerts
  namespace: kafka
  labels:
    release: kube-prometheus-stack
spec:
  groups:
  - name: kafka.rules
    rules:
    - alert: KafkaUnderReplicatedPartitions
      expr: sum by (namespace, kafka_cluster) (kafka_server_replicamanager_underreplicatedpartitions{namespace="kafka",kafka_cluster="my-cluster"}) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Kafka replication is degraded
    - alert: KafkaUnderMinISR
      expr: sum by (namespace, kafka_cluster) (kafka_server_replicamanager_underminisrpartitioncount{namespace="kafka",kafka_cluster="my-cluster"}) > 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: Kafka partitions are below min ISR
    - alert: KafkaControllerCount
      expr: sum by (namespace, kafka_cluster) (kafka_controller_kafkacontroller_activecontrollercount{namespace="kafka",kafka_cluster="my-cluster",kafka_role="controller"})
        != 1
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: Kafka active-controller observation is abnormal
    - alert: KafkaControllerMetricMissing
      expr: count by (namespace, kafka_cluster) (kafka_controller_kafkacontroller_activecontrollercount{namespace="kafka",kafka_cluster="my-cluster",kafka_role="controller"})
        != 3 or absent(kafka_controller_kafkacontroller_activecontrollercount{namespace="kafka",kafka_cluster="my-cluster",kafka_role="controller"})
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: Expected controller metrics are missing or duplicated
    - alert: KafkaNodeScrapeCoverage
      expr: sum by (namespace, kafka_cluster) (up{namespace="kafka",kafka_cluster="my-cluster",kafka_component="nodes"}) != 6 or absent(up{namespace="kafka",kafka_cluster="my-cluster",kafka_component="nodes"})
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: Expected six Kafka node scrapes are not healthy
    - alert: KafkaLagExporterUnavailable
      expr: sum by (namespace, kafka_cluster) (up{namespace="kafka",kafka_cluster="my-cluster",kafka_component="lag"}) != 1 or absent(up{namespace="kafka",kafka_cluster="my-cluster",kafka_component="lag"})
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: Kafka lag exporter is unavailable
    - alert: KafkaConsumerLagHigh
      expr: sum by (namespace, kafka_cluster, consumergroup, topic) (kafka_consumergroup_lag{namespace="kafka",kafka_cluster="my-cluster",topic="orders",consumergroup="order-processor"}
        >= 0) > 1000
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Kafka committed-offset lag is high
    - alert: KafkaConsumerLagMissing
      expr: absent(kafka_consumergroup_lag{namespace="kafka",kafka_cluster="my-cluster",topic="orders",consumergroup="order-processor"})
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Expected consumer group lag has no samples
    - alert: KafkaConsumerOffsetUnknown
      expr: kafka_consumergroup_current_offset{namespace="kafka",kafka_cluster="my-cluster",topic="orders",consumergroup="order-processor"} < 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Consumer committed offset is unknown
```

Estos umbrales y duraciones son puntos de partida. `for` exige que una condición
verdadera esté presente de forma continua antes de que se active la alerta; no es un intervalo
de recopilación ni un promedio móvil. `sum(metric) != 1` por sí solo **no** detecta una
familia de métricas totalmente ausente, porque el resultado puede ser un vector vacío.
Las reglas de cobertura y `absent()` por separado se ocupan de esos casos.

```bash
kubectl apply -f metrics-config.yaml
kubectl -n kafka patch kafka my-cluster --type=merge --patch-file metrics.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl apply -f podmonitors.yaml -f alerts.yaml
```

Inspeccione la generación y las condiciones observadas del recurso Kafka, los puertos
reales de los Pods y las páginas Targets y Rules de Prometheus. Un cambio de
configuración puede provocar un despliegue gradual de las cargas de trabajo. Valide por
separado el enrutamiento y la entrega de Alertmanager; crear un PrometheusRule no
demuestra que se haya enviado una notificación a un operador.

## Escalar consumidores con consultas autenticadas de KEDA

El recurso `Deployment/order-consumer` ya debe existir **en el espacio de nombres `kafka`**,
conectarse mediante el listener TLS/SCRAM de la Parte 2 y consumir con la identidad
`order-processor`. Sus credenciales de aplicación son distintas de la identidad de solo
lectura de metadatos que usará el escalador. El ScaledObject y TriggerAuthentication
también deben estar en `kafka`.

Guarde el archivo como `keda-auth.yaml`. El Secret del nombre de usuario no contiene ninguna
contraseña; el User Operator genera el Secret de la contraseña. KEDA obtiene el nombre
de usuario, la contraseña y la CA mediante las referencias de TriggerAuthentication.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: keda-lag-reader
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
    - resource:
        type: topic
        name: orders
        patternType: literal
      operations:
      - Describe
    - resource:
        type: group
        name: order-processor
        patternType: literal
      operations:
      - Describe
---
apiVersion: v1
kind: Secret
metadata:
  name: keda-kafka-identity
  namespace: kafka
type: Opaque
stringData:
  username: keda-lag-reader
---
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: kafka-lag-auth
  namespace: kafka
spec:
  secretTargetRef:
  - parameter: username
    name: keda-kafka-identity
    key: username
  - parameter: password
    name: keda-lag-reader
    key: password
  - parameter: ca
    name: my-cluster-cluster-ca-cert
    key: ca.crt
```

Guarde el archivo como `scaledobject.yaml`. La verificación del nombre de host TLS permanece
habilitada. El operador de KEDA debe poder acceder a los endpoints de los brokers y a
los Secrets referenciados.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-consumer-scaler
  namespace: kafka
spec:
  scaleTargetRef:
    name: order-consumer
  minReplicaCount: 1
  maxReplicaCount: 10
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
  triggers:
  - type: kafka
    metadata:
      bootstrapServers: my-cluster-kafka-bootstrap.kafka.svc:9093
      version: 4.3.1
      consumerGroup: order-processor
      topic: orders
      tls: enable
      sasl: scram_sha512
      lagThreshold: '50'
      allowIdleConsumers: 'false'
      offsetResetPolicy: earliest
    authenticationRef:
      name: kafka-lag-auth
```

`lagThreshold: "50"` es el **retraso efectivo total deseado por réplica**, no un umbral
independiente que crea varios consumidores por partición. Para el objetivo
AverageValue predeterminado, la demanda aproximada es `ceil(effective total lag / 50)`,
sujeta a los ajustes del escalador, la tolerancia del HPA, el número mínimo/máximo de
réplicas y la estabilización. Añadir consumidores no permite que varios miembros del
mismo grupo de consumidores convencional consuman simultáneamente una misma partición.

`allowIdleConsumers=false` hace que el escalador tenga en cuenta el número de
particiones; si necesita un límite estricto, defina `maxReplicaCount` como un valor que
no supere el número de particiones disponibles. Este ejemplo establece un máximo de 10
con las 12 particiones del tema de la Parte 2. Si el tema o la carga de trabajo tiene un
número de particiones distinto, revíselo.

Como `minReplicaCount=1`, este ejemplo **no escala a cero**.
`activationLagThreshold` y el `cooldownPeriod` de escalado a cero de KEDA no controlan
el comportamiento entre 1 y N réplicas. La estabilización de la reducción de escala del
HPA está configurada explícitamente. Si más adelante habilita el escalado a cero, pruebe
los grupos nuevos, las confirmaciones ausentes, la política de restablecimiento de
offsets, el inicio y la activación; no trate los offsets desconocidos como una cola vacía.

```bash
kubectl apply -f keda-auth.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=180s kafkauser/keda-lag-reader
kubectl apply -f scaledobject.yaml
kubectl -n kafka get scaledobject order-consumer-scaler -o yaml
kubectl -n kafka get hpa
```

Compare los errores del escalador, las métricas actuales/deseadas del HPA y el
rendimiento real de los consumidores antes de cambiar los límites. La [guía existente de
KEDA](../../autoscaling/01-keda.md) explica el comportamiento general del escalado automático.

## Paneles y validación

Use como referencia los paneles versionados del proyecto para **Kafka, KRaft, Kafka Exporter,
Connect y Cruise Control**, teniendo en cuenta el tipo de exportador y el mapeo de
etiquetas seleccionado. El conjunto de Strimzi 1.3 no es una guía de implementación de
ZooKeeper. Importar un panel no garantiza que sus consultas existan en este mapeo específico.

Incluya métricas de JVM/GC, capacidad y E/S de nodos y PVC, disponibilidad de la
replicación, cobertura de recopilación, distribución del tráfico, progreso de los grupos
y SLO de latencia y errores de la aplicación. El exportador en proceso también expone métricas de la JVM, pero las
señales del host/PVC y de la aplicación proceden de sus recolectores correspondientes.

Las reglas JMX finales del ejemplo y Kafka Exporter (1.9.0) se probaron con un broker
Kafka 4.3.1 local aislado: 15 registros y offsets confirmados produjeron retrasos por
partición de **3, 5 y 5**. Se probaron nueve reglas de alerta en escenarios normales,
de datos ausentes, de fallos y de aislamiento entre clústeres. Estas pruebas no demuestran
el acceso TLS en producción, el comportamiento del quórum multinodo, la conciliación de
Strimzi, la entrega de notificaciones ni el funcionamiento de KEDA con su carga de trabajo real.

- [Ejemplo de métricas de Strimzi 1.3.0](https://github.com/strimzi/strimzi-kafka-operator/blob/1.3.0/examples/metrics/kafka-metrics.yaml)
- [Implementación de Kafka Exporter de Strimzi 1.3.0](https://github.com/strimzi/strimzi-kafka-operator/blob/1.3.0/cluster-operator/src/main/java/io/strimzi/operator/cluster/model/KafkaExporter.java)
- [Versiones de los exportadores incluidos en Strimzi 1.3.0](https://github.com/strimzi/strimzi-kafka-operator/blob/1.3.0/docker-images/kafka-based/kafka/Dockerfile)
- [Kafka Exporter 1.10.0](https://github.com/danielqsj/kafka_exporter/tree/v1.10.0)
- [Proyecto kafka-lag-exporter archivado](https://github.com/seglo/kafka-lag-exporter)
- [Escalador Kafka de KEDA 2.21](https://keda.sh/docs/2.21/scalers/apache-kafka/)
- [Implementación de KEDA 2.21.0](https://github.com/kedacore/keda/blob/v2.21.0/pkg/scalers/kafka_scaler.go)
- [Reglas de alertas de Prometheus](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Paneles de Grafana versionados basados en JMX](https://github.com/strimzi/strimzi-kafka-operator/tree/1.3.0/examples/metrics/grafana-dashboards)
- [Paneles versionados de Strimzi Metrics Reporter](https://github.com/strimzi/strimzi-kafka-operator/tree/1.3.0/examples/metrics/strimzi-metrics-reporter/grafana-dashboards)

## Próximos pasos

[Parte 8: Prácticas recomendadas](./08-best-practices.md)

[Volver a la página principal](./README.md)

## Cuestionario

[Cuestionario del tema](../../quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
