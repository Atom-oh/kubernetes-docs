# Parte 7: Monitoreo

> **Versiones compatibles**: Strimzi 0.45+, Prometheus Operator, KEDA 2.x\
> **Última actualización**: July 9, 2026

Un clúster de Kafka necesita más que gráficos del heap del broker, disco y red: también se necesita visibilidad sobre el estado de replicación de las particiones y la velocidad de procesamiento de los consumidores para detectar problemas pronto. Este documento cubre la recopilación con Prometheus de las métricas del broker que Strimzi expone, la medición independiente del consumer lag y el autoescalado de consumidores con KEDA.

## 1. Cómo Strimzi expone métricas

Strimzi ejecuta un Prometheus JMX Exporter dentro de cada contenedor de componente broker/controller/Connect, no como un contenedor sidecar independiente, sino como un **agente Java de JVM** cargado en el mismo proceso de JVM. El JMX Exporter lee MBeans JMX internos de la JVM (por ejemplo, `kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions`) y los convierte en un endpoint HTTP `/metrics` con formato de texto de Prometheus. Los MBeans que se asignan a cada nombre y etiqueta de métrica se definen mediante una configuración de relabeling almacenada en un `ConfigMap`, y el campo `metricsConfig` del CR `Kafka` apunta a ese `ConfigMap`.

El repositorio upstream de Strimzi incluye configuraciones de ejemplo de JMX Exporter para brokers, Connect y Cruise Control en [`examples/metrics`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics). En la práctica, los equipos comienzan con estos ejemplos y ajustan solo las reglas que necesitan, en lugar de escribir reglas de relabeling desde cero.

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

Una vez aplicado `metricsConfig`, Strimzi habilita automáticamente el agente Java JMX Exporter dentro de cada contenedor de broker y monta en ese mismo contenedor el archivo de reglas del `ConfigMap` referenciado. Las métricas en formato Prometheus pasan a poder recopilarse en la ruta `/metrics`, en el puerto `9404` (el predeterminado), de cada Pod de broker. El mismo campo `metricsConfig` está disponible en los recursos personalizados `KafkaConnect`, `KafkaMirrorMaker2` y `CruiseControl`.

## 2. Métricas principales del broker

Kafka expone una gran cantidad de métricas JMX, por lo que conviene centrarse en las que realmente importan a diario.

| Métrica | Significado | Valor saludable / qué vigilar |
| --- | --- | --- |
| `kafka_server_replicamanager_underreplicatedpartitions` | Número de particiones lideradas por este broker cuyo conjunto de réplicas en sincronización (ISR) es menor que el factor de replicación configurado | **Debe ser 0.** Cualquier valor por encima de 0 significa que uno o más followers se están quedando atrás del líder; investigue la latencia de red, la sobrecarga del broker o los cuellos de botella de I/O de disco. |
| `kafka_controller_kafkacontroller_activecontrollercount` | Indica si este broker/controller es actualmente el controller activo (0 o 1) | La **suma de todo el clúster debe ser exactamente 1**. Una suma de 0 significa que no hay controller activo (elección de líder en curso o un fallo); una suma de 2 o más sugiere una condición de split-brain y requiere investigación inmediata. |
| Proporción de inactividad del Request Handler (`...requesthandleravgidlepercent...`) | Fracción de tiempo en que el pool de threads de request-handler del broker permanece inactivo | Un valor decreciente (por ejemplo, inferior al 20 %) indica que el broker se acerca a la saturación de CPU/threads. Los valores persistentemente bajos indican que se deben escalar horizontalmente los brokers o reequilibrar las particiones. |
| `kafka_server_brokertopicmetrics_bytesinpersec_oneminuterate` / `bytesoutpersec` | Throughput de producción/consumo por topic, en bytes por segundo | Se usa para la planificación de capacidad de broker/red y para detectar picos de tráfico en topics individuales (particiones calientes). |
| Tasa de reducción/expansión de ISR (`kafka_server_replicamanager_isrshrinkspersec`, `isrexpandspersec`) | Tasa por segundo a la que las réplicas salen (reducción) o se reincorporan (expansión) al conjunto ISR | Las reducciones frecuentes significan que los followers pierden repetidamente la sincronización y suelen preceder un aumento de particiones con replicación insuficiente. |

De estas, el **recuento de particiones con replicación insuficiente** y el **recuento de controllers activos** reflejan más directamente la seguridad y disponibilidad de los datos del clúster, por lo que deben estar en la parte superior de cada dashboard y conjunto de reglas de alerta.

```promql
# Cluster-wide active controller sum (should be 1)
sum(kafka_controller_kafkacontroller_activecontrollercount)

# Brokers currently reporting under-replicated partitions
kafka_server_replicamanager_underreplicatedpartitions > 0
```

## 3. Monitoreo del consumer lag

El **consumer lag** es, por partición, la diferencia entre el offset producido más reciente (el offset del final del log) y el último offset que un grupo de consumidores ha confirmado. Un lag que crece de forma constante significa que un grupo de consumidores no puede seguir el ritmo de producción, lo que indica procesamiento lento, un consumidor detenido o reequilibrios repetidos.

Las métricas de JMX Exporter que Strimzi expone mediante este agente Java en proceso describen el **estado propio del broker** (sección 2 anterior) y no incluyen de forma predeterminada los offsets ni el lag de los grupos de consumidores. Calcular el lag requiere correlacionar los offsets confirmados de un grupo de consumidores (seguidos en el topic interno `__consumer_offsets`) con el offset más reciente de cada topic, lo cual queda fuera del alcance del exporter del lado del broker. Por ello, los equipos normalmente ejecutan un exporter independiente dedicado al consumer lag.

La opción más utilizada es el proyecto comunitario [`kafka-lag-exporter`](https://github.com/seglo/kafka-lag-exporter) (o un exporter similar de estilo Burrow), que se ejecuta como su propio `Deployment` en el clúster. Consulta la API de administración de Kafka a intervalos para leer los offsets confirmados de cada grupo de consumidores y los offsets más recientes de cada topic, y después expone en formato Prometheus métricas como `kafka_consumergroup_group_lag` (lag desglosado por grupo, topic y partición).

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

Una vez que este exporter se implementa y Prometheus recopila su endpoint `/metrics`, el lag se puede consultar así:

```promql
# Total lag per consumer group and topic (summed across partitions)
sum by (group, topic) (kafka_consumergroup_group_lag)

# Group/topic combinations with lag above 1000
sum by (group, topic) (kafka_consumergroup_group_lag) > 1000
```

## 4. Configuración de la recopilación con ServiceMonitor / PodMonitor

En entornos que ejecutan Prometheus Operator (como kube-prometheus-stack), el enfoque habitual no es editar manualmente `scrape_configs`, sino declarar un CRD `PodMonitor` que descubre destinos por etiqueta. Dado que los brokers se ejecutan como Pods administrados por Strimzi y no detrás de un `Service` fijo, seleccionar los Pods directamente con un `PodMonitor` es más fiable que depender de un `ServiceMonitor` basado en `Service`.

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

Una vez que las métricas fluyen, alertar sobre particiones con replicación insuficiente es la red de seguridad más básica que se debe implementar. El `PrometheusRule` siguiente se activa cuando las particiones con replicación insuficiente se mantienen por encima de 0 durante al menos 5 minutos.

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

## 5. Autoescalado de consumidores con KEDA

El HPA basado en CPU/memoria a menudo no refleja la carga real de un workload de consumidores: la cantidad de mensajes que esperan ser procesados. El escalador de Kafka de KEDA (`triggers.type: kafka`) permite escalar un `Deployment` de consumidores según el **consumer group lag**. KEDA consulta el lag del topic/grupo de consumidores configurado directamente a través de la API de administración de Kafka, por lo que las decisiones de escalado no requieren estrictamente el exporter de lag independiente de la sección 3 (aunque ese exporter sigue siendo útil para dashboards y alertas).

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

Parámetros principales del trigger:

* **`bootstrapServers`**: La dirección bootstrap del clúster de Kafka que KEDA usa para consultar el lag
* **`consumerGroup`**, **`topic`**: El grupo de consumidores y el topic cuyo lag se mide
* **`lagThreshold`**: El valor de lag por partición por encima del cual KEDA añade otra réplica (por ejemplo, una réplica adicional por cada 50 unidades de lag por partición)
* **`activationLagThreshold`**: El lag mínimo necesario para activar el escalado inicial de 0 a 1 réplica. Si no se establece, incluso una pequeña cantidad de lag escala inmediatamente a 1.
* **`allowIdleConsumers`**: Cuando es `false` (el valor predeterminado), KEDA limita las réplicas para que nunca cree más consumidores que particiones disponibles para consumir.

Una vez aplicado este `ScaledObject`, KEDA Operator crea y administra un HPA estándar de Kubernetes en segundo plano, y vuelve a reducir el escalado después de `cooldownPeriod` cuando el lag disminuye. Para los conceptos más amplios de KEDA —tipos de escaladores, arquitectura y escalado a cero— consulte el documento específico [Autoescalado: KEDA](../../autoscaling/01-keda.md).

## 6. Dashboards de Grafana

Strimzi incluye JSON de dashboards de Grafana de ejemplo para brokers, ZooKeeper (modo heredado), Kafka Connect y Cruise Control en [`examples/metrics/grafana-dashboards`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics/grafana-dashboards) de su repositorio de GitHub. Importarlos y ajustar las variables de nombre de clúster/namespace suele ser más rápido que crear paneles desde cero.

Un dashboard sólido de Kafka debe cubrir al menos estos grupos de paneles:

* **Estado del broker**: tiempo de actividad por broker, uso del heap de JVM, tiempo de pausa de GC, proporción de inactividad de request-handler/red
* **Estado de ISR/replicación**: recuento de particiones con replicación insuficiente, tasa de reducción/expansión de ISR, recuento de controllers activos (suma de todo el clúster)
* **Throughput**: bytes de entrada/salida por segundo por topic y por broker, mensajes por segundo, desequilibrio de throughput por partición (detección de particiones calientes)
* **Consumer lag**: tendencia del lag por grupo de consumidores, correlacionada con eventos de reequilibrio para identificar la causa de picos repentinos

## Próximos pasos

Con la recopilación de métricas, las alertas y el autoescalado configurados, el siguiente paso es aplicar todo esto a estándares operativos reales: SLO, planificación de capacidad y procedimientos de respuesta a incidentes. Esto se cubre en la [Parte 8: Buenas prácticas](./08-best-practices.md).

[Volver a la página principal](./README.md)

## Cuestionario

Para comprobar lo aprendido en este capítulo, pruebe el [Cuestionario del topic](../../quizzes/data-on-eks/kafka/07-monitoring-quiz.md).
