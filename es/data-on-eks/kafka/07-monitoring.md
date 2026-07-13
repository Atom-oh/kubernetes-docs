# Parte 7: Monitoreo

> **Versiones compatibles**: Strimzi 0.45+, Prometheus Operator, KEDA 2.x\
> **Última actualización**: July 9, 2026

Un cluster de Kafka necesita más que gráficos de heap de brokers, disco y red: también necesitas visibilidad sobre la salud de la replicación de partitions y la velocidad de procesamiento de consumers para detectar problemas temprano. Este documento cubre cómo recopilar las métricas de brokers que Strimzi expone con Prometheus, medir el consumer lag por separado y escalar consumers automáticamente con KEDA.

## 1. Cómo Strimzi expone métricas

Strimzi ejecuta un Prometheus JMX Exporter dentro de cada contenedor de broker/controller/Connect: no como un contenedor sidecar separado, sino como un **JVM Java agent** cargado en el mismo proceso JVM. El JMX Exporter lee JMX MBeans internos de la JVM (por ejemplo `kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions`) y los convierte en un endpoint HTTP `/metrics` en formato de texto de Prometheus. Qué MBeans se asignan a qué nombres y labels de métricas se define mediante una configuración de relabeling almacenada en un `ConfigMap`, y el campo `metricsConfig` del CR `Kafka` apunta a ese `ConfigMap`.

El repositorio upstream de Strimzi incluye configuraciones de ejemplo de JMX Exporter para brokers, Connect y Cruise Control bajo [`examples/metrics`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics). En la práctica, los equipos parten de estos ejemplos y ajustan solo las reglas que necesitan, en lugar de escribir reglas de relabeling desde cero.

```yaml
# kafka-metrics-config.yaml (excerpt, based on Strimzi's example)
apiVersion: v1
kind: ConfigMap
metadata:
  name: kafka-metrics
  namespace: kafka
data:
  kafka-metrics-config.yml: |
    lowercaseOutputName: true
    rules:
      # Under-replicated partition count
      - pattern: "kafka.server<type=ReplicaManager, name=UnderReplicatedPartitions><>Value"
        name: "kafka_server_replicamanager_underreplicatedpartitions"
      # Active controller count (KRaft)
      - pattern: "kafka.controller<type=KafkaController, name=ActiveControllerCount><>Value"
        name: "kafka_controller_kafkacontroller_activecontrollercount"
      # Request handler idle ratio
      - pattern: "kafka.server<type=KafkaRequestHandlerPool, name=RequestHandlerAvgIdlePercent><>OneMinuteRate"
        name: "kafka_server_kafkarequesthandlerpool_requesthandleravgidlepercent_oneminuterate"
      # Per-topic bytes in/out
      - pattern: "kafka.server<type=BrokerTopicMetrics, name=(BytesInPerSec|BytesOutPerSec), topic=(.+)><>OneMinuteRate"
        name: "kafka_server_brokertopicmetrics_$1_oneminuterate"
        labels:
          topic: "$2"
```

```yaml
# Kafka CR referencing the ConfigMap above via metricsConfig
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
  namespace: kafka
spec:
  kafka:
    # ...
    metricsConfig:
      type: jmxPrometheusExporter
      valueFrom:
        configMapKeyRef:
          name: kafka-metrics
          key: kafka-metrics-config.yml
```

Una vez que se aplica `metricsConfig`, Strimzi habilita automáticamente el JMX Exporter Java agent dentro de cada contenedor de broker y monta el archivo de reglas del `ConfigMap` referenciado en ese mismo contenedor. Las métricas en formato Prometheus quedan entonces disponibles para scraping en la ruta `/metrics` del puerto `9404` (el predeterminado) de cada broker pod. El mismo campo `metricsConfig` está disponible en los recursos personalizados `KafkaConnect`, `KafkaMirrorMaker2` y `CruiseControl`.

## 2. Métricas principales de brokers

Kafka expone una gran cantidad de métricas JMX, así que ayuda acotar cuáles importan realmente en el día a día.

| Métrica | Significado | Valor saludable / qué vigilar |
| --- | --- | --- |
| `kafka_server_replicamanager_underreplicatedpartitions` | Número de partitions lideradas por este broker cuyo conjunto de replicas in-sync (ISR) es menor que el replication factor configurado | **Debería ser 0.** Cualquier valor por encima de 0 significa que uno o más followers se están quedando detrás del leader: investiga latencia de red, sobrecarga del broker o cuellos de botella de I/O de disco. |
| `kafka_controller_kafkacontroller_activecontrollercount` | Si este broker/controller es actualmente el controller activo (0 o 1) | La **suma a nivel de cluster debe ser exactamente 1**. Una suma de 0 significa que no hay controller activo (elección de leader en progreso o una falla); una suma de 2 o más sugiere una condición de split-brain y requiere investigación inmediata. |
| Request Handler Idle Ratio (`...requesthandleravgidlepercent...`) | Fracción de tiempo en que el thread pool de request handlers del broker permanece idle | Un valor en descenso (por ejemplo, por debajo del 20%) indica que el broker se acerca a saturación de CPU/threads. Valores persistentemente bajos son una señal para escalar brokers horizontalmente o rebalancear partitions. |
| `kafka_server_brokertopicmetrics_bytesinpersec_oneminuterate` / `bytesoutpersec` | Throughput de produce/consume por topic en bytes por segundo | Se usa para planificación de capacidad de broker/red y para detectar picos de tráfico en topics individuales (hot partitions). |
| ISR Shrink/Expand Rate (`kafka_server_replicamanager_isrshrinkspersec`, `isrexpandspersec`) | Tasa a la que las replicas salen (shrink) o vuelven a unirse (expand) al conjunto ISR por segundo | Shrinks frecuentes significan que los followers están saliendo repetidamente de sincronía y normalmente preceden a un aumento de partitions under-replicated. |

De estas, el **conteo de partitions under-replicated** y el **conteo de controllers activos** reflejan de forma más directa la seguridad de los datos y la disponibilidad del cluster, por lo que deben estar al inicio de cada dashboard y conjunto de reglas de alerta.

```promql
# Cluster-wide active controller sum (should be 1)
sum(kafka_controller_kafkacontroller_activecontrollercount)

# Brokers currently reporting under-replicated partitions
kafka_server_replicamanager_underreplicatedpartitions > 0
```

## 3. Monitoreo de Consumer Lag

El **consumer lag** es, por partition, la diferencia entre el último offset producido (el log end offset) y el último offset que un consumer group ha confirmado. Un lag que crece de forma sostenida significa que un consumer group no puede seguir el ritmo de la tasa de producción: una señal de procesamiento lento, un consumer detenido o rebalancing repetido.

Las métricas del JMX Exporter que Strimzi expone mediante este Java agent en proceso describen el **estado propio del broker** (sección 2 anterior) y, de forma predeterminada, no incluyen offsets ni lag de consumer groups. Calcular el lag requiere correlacionar los offsets confirmados de un consumer group (rastreados en el topic interno `__consumer_offsets`) con el offset más reciente de cada topic, lo cual está fuera del alcance del exporter del lado del broker. Por esto, los equipos suelen ejecutar un exporter separado dedicado al consumer lag.

La opción más utilizada es el proyecto comunitario [`kafka-lag-exporter`](https://github.com/seglo/kafka-lag-exporter) (o un exporter similar al estilo Burrow), ejecutado como su propio `Deployment` en el cluster. Consulta la Kafka Admin API en intervalos para leer los offsets confirmados de cada consumer group y los offsets más recientes de cada topic, y luego expone métricas como `kafka_consumergroup_group_lag` (lag desglosado por group, topic y partition) en formato Prometheus.

```yaml
# Minimal ConfigMap for kafka-lag-exporter
apiVersion: v1
kind: ConfigMap
metadata:
  name: kafka-lag-exporter-config
  namespace: kafka
data:
  application.conf: |
    kafka-lag-exporter {
      port = 8000
      clusters = [
        {
          name = "my-cluster"
          bootstrap-brokers = "my-cluster-kafka-bootstrap.kafka.svc:9092"
        }
      ]
      poll-interval = 30 seconds
    }
```

Una vez que este exporter está desplegado y Prometheus está haciendo scraping de su endpoint `/metrics`, el lag se puede consultar así:

```promql
# Total lag per consumer group and topic (summed across partitions)
sum by (group, topic) (kafka_consumergroup_group_lag)

# Group/topic combinations with lag above 1000
sum by (group, topic) (kafka_consumergroup_group_lag) > 1000
```

## 4. Conectar el scraping con ServiceMonitor / PodMonitor

En entornos que ejecutan Prometheus Operator (como kube-prometheus-stack), el enfoque habitual no es editar manualmente `scrape_configs`, sino declarar un CRD `PodMonitor` que descubre targets por label. Debido a que los brokers se ejecutan como pods gestionados por Strimzi en lugar de detrás de un `Service` fijo, seleccionar pods directamente con un `PodMonitor` es más confiable que depender de un `ServiceMonitor` basado en `Service`.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: kafka-broker-metrics
  namespace: kafka
  labels:
    release: kube-prometheus-stack
spec:
  selector:
    matchLabels:
      strimzi.io/kind: Kafka
      strimzi.io/cluster: my-cluster
  namespaceSelector:
    matchNames:
      - kafka
  podMetricsEndpoints:
    - port: tcp-prometheus
      path: /metrics
      interval: 30s
```

Una vez que las métricas fluyen, alertar por partitions under-replicated es la red de seguridad más básica que conviene implementar. La `PrometheusRule` siguiente se dispara cuando las partitions under-replicated permanecen por encima de 0 durante al menos 5 minutos.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kafka-broker-alerts
  namespace: kafka
  labels:
    release: kube-prometheus-stack
spec:
  groups:
    - name: kafka-broker.rules
      rules:
        - alert: KafkaUnderReplicatedPartitions
          expr: sum(kafka_server_replicamanager_underreplicatedpartitions) > 0
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Kafka cluster has under-replicated partitions"
            description: "Under-replicated partitions have been above 0 for over 5 minutes. Check follower brokers for lag or failure."
        - alert: KafkaNoActiveController
          expr: sum(kafka_controller_kafkacontroller_activecontrollercount) != 1
          for: 2m
          labels:
            severity: critical
          annotations:
            summary: "Abnormal Kafka active controller count"
            description: "The cluster-wide sum of active controllers is not 1. Check controller leader election status."
```

## 5. Autoscaling de consumers con KEDA

El HPA basado en CPU/memoria a menudo no refleja la carga real de un workload de consumers: el número de mensajes que esperan ser procesados. El Kafka scaler de KEDA (`triggers.type: kafka`) te permite escalar un `Deployment` de consumers con base en el **consumer group lag**. KEDA consulta el lag del topic/consumer group configurado directamente a través de la Kafka Admin API, por lo que las decisiones de escalado no requieren estrictamente el exporter de lag separado de la sección 3 (aunque ese exporter sigue siendo útil para dashboards y alertas).

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-consumer-scaler
  namespace: default
spec:
  scaleTargetRef:
    name: order-consumer
  minReplicaCount: 1
  maxReplicaCount: 10
  cooldownPeriod: 60
  triggers:
    - type: kafka
      metadata:
        bootstrapServers: my-cluster-kafka-bootstrap.kafka.svc:9092
        consumerGroup: order-consumer-group
        topic: orders
        lagThreshold: "50"
        activationLagThreshold: "5"
        allowIdleConsumers: "false"
```

Parámetros clave del trigger:

* **`bootstrapServers`**: La dirección bootstrap del cluster Kafka que KEDA usa para consultar lag
* **`consumerGroup`**, **`topic`**: El consumer group y el topic cuyo lag se mide
* **`lagThreshold`**: El valor de lag por partition por encima del cual KEDA añade otra replica (por ejemplo, una replica adicional por cada 50 unidades de lag por partition)
* **`activationLagThreshold`**: El lag mínimo necesario para activar el escalado inicial de 0 a 1 replica. Si no se establece, incluso una pequeña cantidad de lag escala inmediatamente a 1.
* **`allowIdleConsumers`**: Cuando es `false` (el predeterminado), KEDA limita las replicas para nunca crear más consumers de los que hay partitions para consumir.

Una vez aplicado este `ScaledObject`, el KEDA Operator crea y gestiona un HPA estándar de Kubernetes detrás de escena, y reduce el escalado después de `cooldownPeriod` cuando el lag disminuye. Para los conceptos más amplios de KEDA — tipos de scalers, arquitectura, escalado a cero — consulta el documento dedicado [Autoscaling: KEDA](../../autoscaling/01-keda.md).

## 6. Dashboards de Grafana

Strimzi incluye JSON de dashboards de Grafana de ejemplo para brokers, ZooKeeper (modo legacy), Kafka Connect y Cruise Control bajo [`examples/metrics/grafana-dashboards`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics/grafana-dashboards) en su repositorio de GitHub. Importarlos y ajustar las variables de nombre de cluster/namespace suele ser más rápido que construir paneles desde cero.

Un dashboard sólido de Kafka debería cubrir al menos estos grupos de paneles:

* **Salud de brokers**: uptime por broker, uso de heap de JVM, tiempo de pausa de GC, ratio idle de request-handler/red
* **Estado de ISR/replicación**: conteo de partitions under-replicated, tasa de ISR shrink/expand, conteo de controllers activos (suma a nivel de cluster)
* **Throughput**: bytes de entrada/salida por topic y por broker por segundo, mensajes por segundo, desequilibrio de throughput por partition (detección de hot partitions)
* **Consumer lag**: tendencia de lag por consumer group, correlacionada con eventos de rebalance para identificar la causa de picos repentinos

## Próximos pasos

Con la recolección de métricas, alertas y autoscaling en funcionamiento, el siguiente paso es aplicar todo esto a estándares operativos reales: SLOs, planificación de capacidad y procedimientos de respuesta a incidentes. Eso se cubre en [Parte 8: Mejores prácticas](./08-best-practices.md).

[Volver a la página principal](./)

## Cuestionario

Para poner a prueba lo que aprendiste en este capítulo, intenta el [cuestionario del topic](../../quizzes/data-on-eks/kafka/07-monitoring-quiz.md).
