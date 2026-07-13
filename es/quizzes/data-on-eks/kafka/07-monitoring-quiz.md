# Parte 7: Cuestionario de monitoreo

Este cuestionario evalúa tu comprensión de cómo Strimzi expone métricas, qué significan las métricas principales del broker, cómo se mide el consumer lag y cómo se configura el escalador de Kafka de KEDA.

## Preguntas de opción múltiple

1. ¿Qué ejecuta Strimzi dentro de cada contenedor de broker para convertir métricas JMX a una forma que Prometheus pueda recopilar?
   - A) Un sidecar de Fluent Bit
   - B) Un Prometheus JMX Exporter (agente Java de JVM)
   - C) Un OpenTelemetry Collector DaemonSet
   - D) cAdvisor

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un Prometheus JMX Exporter (agente Java de JVM)**

**Explicación:**
Cuando `metricsConfig` se configura en el CR `Kafka`, Strimzi habilita automáticamente un Prometheus JMX Exporter dentro de cada contenedor de broker (y Connect, etc.), no como un contenedor sidecar separado, sino como un agente Java cargado en el mismo proceso JVM. Este exporter lee valores de JMX MBean internos de la JVM, los renombra según reglas de reetiquetado y los expone en formato de texto de Prometheus en un endpoint HTTP `/metrics`. Fluent Bit es un recopilador de logs y cAdvisor recopila métricas de recursos de contenedores; ninguno cumple este propósito.
</details>

2. ¿A qué tipo de recurso hace referencia `Kafka.spec.kafka.metricsConfig` para obtener las reglas de reetiquetado del JMX Exporter?
   - A) Secret
   - B) PersistentVolumeClaim
   - C) ConfigMap
   - D) CustomResourceDefinition

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) ConfigMap**

**Explicación:**
`metricsConfig.valueFrom.configMapKeyRef` apunta al nombre y la clave de un `ConfigMap` que contiene las reglas de reetiquetado (en YAML). Strimzi monta este archivo de reglas en el contenedor que ejecuta el agente Java JMX Exporter para que sepa qué JMX MBeans se asignan a qué nombres de métricas y etiquetas de Prometheus. Un `Secret` se usa para valores sensibles como certificados o credenciales y no se utiliza para este propósito.
</details>

3. ¿Cuál es el valor saludable para la métrica `kafka_server_replicamanager_underreplicatedpartitions`?
   - A) Debe ser igual al número de brokers
   - B) Debe ser igual al número de particiones
   - C) Siempre debe ser 0
   - D) Siempre debe ser 1

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Siempre debe ser 0**

**Explicación:**
Esta métrica cuenta las particiones lideradas por un broker dado cuyo conjunto de réplicas en sincronía (ISR) es menor que el factor de replicación configurado. En operación normal, cada follower debería mantenerse al día con el leader, por lo que este valor debería ser 0. Un valor superior a 0 indica que algunas réplicas se están quedando atrás, a menudo debido a latencia de red, sobrecarga del broker o cuellos de botella de I/O de disco, y representa un riesgo directo para la durabilidad de los datos si el leader falla con un ISR insuficiente.
</details>

4. ¿Cuál debe ser la suma a nivel de cluster de `kafka_controller_kafkacontroller_activecontrollercount` durante una operación saludable?
   - A) 0
   - B) Igual al número de brokers
   - C) Exactamente 1
   - D) Igual al número de candidatos a controller

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Exactamente 1**

**Explicación:**
Cada broker/controller expone si actualmente es el controller activo como 0 o 1. Sumar esto en todo el cluster debería dar exactamente 1 durante una operación saludable. Una suma de 0 significa que no hay controller activo (elección de leader en curso o una falla); una suma de 2 o más sugiere una anomalía grave, como una condición de split-brain, y justifica una investigación inmediata.
</details>

5. Si el Request Handler Idle Ratio se mantiene persistentemente bajo (por ejemplo, por debajo del 10%), ¿qué deberías sospechar primero?
   - A) La capacidad de disco se está agotando
   - B) El broker se está acercando a la saturación de recursos de CPU/threads
   - C) La conexión con ZooKeeper se ha caído
   - D) Un consumer group se está reequilibrando

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El broker se está acercando a la saturación de recursos de CPU/threads**

**Explicación:**
El Request Handler Idle Ratio es la fracción de tiempo durante la cual el pool de threads de manejo de solicitudes de un broker permanece inactivo. Un valor bajo significa que el pool de threads está constantemente ocupado procesando solicitudes, lo que indica que el broker se acerca a sus límites de capacidad de CPU o threads. Los valores persistentemente bajos son una señal para considerar escalar horizontalmente los brokers, reequilibrar particiones o ajustar el tamaño del pool de threads.
</details>

6. ¿Por qué las métricas de broker que Strimzi expone de forma predeterminada no incluyen el consumer group lag?
   - A) El consumer lag es información sensible que no puede exponerse por razones de seguridad
   - B) Calcular el lag requiere correlacionar los offsets confirmados de un consumer group con los offsets más recientes de un topic, pero el JMX Exporter solo lee los JMX MBeans propios del broker
   - C) La versión de Strimzi utilizada es demasiado antigua para admitirlo
   - D) El consumer lag solo puede medirse desde el lado del cliente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Calcular el lag requiere correlacionar los offsets confirmados de un consumer group con los offsets más recientes de un topic, pero el JMX Exporter solo lee los JMX MBeans propios del broker**

**Explicación:**
El agente Java JMX Exporter solo lee y expone JMX MBeans internos al proceso del broker (estado de replicación, throughput, estado del controller, etc.). El consumer lag es la diferencia entre el último offset confirmado de un consumer group y el offset más reciente (log end) de un topic, lo que requiere consultar ambos valores por separado mediante la Kafka Admin API. Por eso el consumer lag suele medirse con una herramienta dedicada como `kafka-lag-exporter`.
</details>

7. ¿Qué exporter de la comunidad se presenta en este documento para medir el consumer lag?
   - A) node-exporter
   - B) kafka-lag-exporter
   - C) blackbox-exporter
   - D) kube-state-metrics

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) kafka-lag-exporter**

**Explicación:**
`kafka-lag-exporter` es un proyecto de la comunidad que consulta periódicamente los offsets confirmados de un consumer group y los offsets más recientes de cada topic mediante la Kafka Admin API, y luego expone métricas como `kafka_consumergroup_group_lag` en formato Prometheus. `node-exporter` recopila métricas del sistema host, `blackbox-exporter` sondea endpoints y `kube-state-metrics` informa el estado de objetos de Kubernetes; ninguno de estos cumple este propósito.
</details>

8. Al recopilar métricas de pods de broker de Kafka administrados por Strimzi en un entorno de Prometheus Operator, ¿qué CRD es más confiable que apuntar a un `Service` fijo?
   - A) ServiceMonitor
   - B) PodMonitor
   - C) Probe
   - D) AlertmanagerConfig

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) PodMonitor**

**Explicación:**
Los brokers se ejecutan como pods individuales administrados por Strimzi. Un `PodMonitor` que selecciona pods directamente por etiqueta (como `strimzi.io/cluster`) descubre objetivos de scraping de forma más confiable que un `ServiceMonitor`, que apunta a un endpoint de `Service` fijo. `Probe` se usa para comprobaciones de endpoints de estilo blackbox, y `AlertmanagerConfig` configura el enrutamiento de alertas; ninguno se usa para el scraping de métricas a nivel de pod.
</details>

9. En una alerta `PrometheusRule` para particiones subreplicadas, ¿qué hace `for: 5m`?
   - A) Recopila métricas cada 5 minutos
   - B) La condición debe mantenerse verdadera de forma continua durante 5 minutos antes de que la alerta se dispare realmente
   - C) La alerta se resuelve automáticamente 5 minutos después de dispararse
   - D) Calcula un promedio de 5 minutos del valor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La condición debe mantenerse verdadera de forma continua durante 5 minutos antes de que la alerta se dispare realmente**

**Explicación:**
En una regla de alertas de Prometheus, el campo `for` significa que la condición en `expr` debe permanecer verdadera durante la duración especificada antes de que la alerta pase de `pending` a `firing`. Configurar `for: 5m` reduce alertas ruidosas causadas por picos momentáneos y garantiza que las alertas solo se disparen por problemas realmente persistentes.
</details>

10. ¿Cómo determina el escalador de Kafka de KEDA el lag de un consumer group?
    - A) Recopilando las métricas de Prometheus expuestas por kafka-lag-exporter
    - B) Consultando directamente la Kafka Admin API
    - C) Analizando el endpoint `/metrics` del JMX Exporter del broker
    - D) Leyendo offsets almacenados en ZooKeeper

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Consultando directamente la Kafka Admin API**

**Explicación:**
El escalador de Kafka de KEDA llama directamente a la Kafka Admin API, usando parámetros de trigger como `bootstrapServers`, `consumerGroup` y `topic`, para determinar el lag de un consumer group. Esto significa que un exporter de Prometheus separado como `kafka-lag-exporter` no es estrictamente necesario para decisiones de escalado (aunque sigue siendo útil para dashboards y alertas). ZooKeeper ya no almacena offsets en modo KRaft.
</details>

## Preguntas de respuesta corta

11. Define consumer lag en una oración.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: La diferencia, por partición, entre el último offset producido (el log end offset) y el offset que un consumer group ha confirmado por última vez.**

**Explicación:**
El consumer lag mide, en unidades de offsets, cuántos mensajes un consumer aún no ha procesado. Un lag de 0 significa que el consumer se ha puesto al día con el mensaje más reciente; un lag que aumenta de forma sostenida indica que la tasa de procesamiento del consumer no puede mantenerse al ritmo de la tasa de producción.
</details>

12. ¿Cuál es el nombre del componente que Strimzi usa para convertir las métricas JMX de un broker de Kafka en un endpoint HTTP `/metrics`?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Prometheus JMX Exporter (un agente Java de JVM)**

**Explicación:**
El JMX Exporter lee valores de JMX MBean de la JVM, los renombra y reetiqueta según reglas configuradas, y los expone en un formato de texto que Prometheus puede recopilar en una ruta `/metrics`. Cuando `metricsConfig` está configurado, Strimzi lo habilita automáticamente como un agente Java dentro del mismo proceso JVM en contenedores de componentes como brokers, no como un contenedor sidecar separado.
</details>

13. En el trigger de Kafka de un `ScaledObject` de KEDA, ¿qué parámetro establece el valor de lag por partición por encima del cual se agregan réplicas adicionales?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: `lagThreshold`**

**Explicación:**
`lagThreshold` es el valor aceptable de lag por partición; cada vez que el lag real cruza un múltiplo de este valor, el HPA que KEDA administra agrega otra réplica. Por ejemplo, con `lagThreshold: "50"` y un lag de partición de 120, se calcularían aproximadamente 2-3 réplicas como necesarias. Por separado, `activationLagThreshold` determina si ocurre en absoluto el escalado inicial de 0 a 1 réplica.
</details>

14. ¿Qué par de métricas puede servir como indicador adelantado antes de que aumenten las particiones subreplicadas, describiendo con qué frecuencia las réplicas salen o vuelven a unirse al conjunto ISR?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: ISR Shrink Rate e ISR Expand Rate (`isrshrinkspersec`, `isrexpandspersec`)**

**Explicación:**
ISR Shrink Rate es la tasa por segundo a la que las réplicas salen del conjunto ISR, e ISR Expand Rate es la tasa a la que vuelven a unirse. Las reducciones frecuentes indican que los followers se están quedando repetidamente atrás del leader, lo que a menudo precede a un aumento de particiones subreplicadas, convirtiéndolo en una señal útil de alerta temprana.
</details>

## Preguntas prácticas

15. Escribe el YAML para el `metricsConfig` de un CR `Kafka` que hace referencia a un `ConfigMap` llamado `kafka-metrics` con la clave `kafka-metrics-config.yml`.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
  namespace: kafka
spec:
  kafka:
    metricsConfig:
      type: jmxPrometheusExporter
      valueFrom:
        configMapKeyRef:
          name: kafka-metrics
          key: kafka-metrics-config.yml
```

**Explicación:**
`type: jmxPrometheusExporter` es actualmente el único tipo de exposición de métricas que Strimzi admite, y `valueFrom.configMapKeyRef` especifica el `ConfigMap` que contiene las reglas de reetiquetado y la clave dentro de él. Una vez aplicado, el Strimzi Cluster Operator habilita automáticamente el agente Java JMX Exporter dentro de los contenedores de broker y monta el archivo de reglas referenciado.
</details>

16. Escribe un `ScaledObject` de KEDA que escale el `Deployment` `order-consumer` entre 1 y 10 réplicas en función del lag del consumer group `order-consumer-group` en el topic `orders`, usando un umbral de lag por partición de 50.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
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
  triggers:
    - type: kafka
      metadata:
        bootstrapServers: my-cluster-kafka-bootstrap.kafka.svc:9092
        consumerGroup: order-consumer-group
        topic: orders
        lagThreshold: "50"
```

**Explicación:**
`scaleTargetRef.name` identifica el `Deployment` objetivo, mientras que `minReplicaCount`/`maxReplicaCount` limitan el rango de escalado. `type: kafka` en `triggers` selecciona el escalador de Kafka, y sus `metadata` proporcionan los bootstrap servers, consumer group, topic y umbral de lag. El KEDA Operator usa este recurso para crear y administrar un HPA estándar de Kubernetes.
</details>

17. Escribe un `PrometheusRule` que dispare una alerta de severidad `warning` cuando las particiones subreplicadas permanezcan por encima de 0 durante al menos 5 minutos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kafka-broker-alerts
  namespace: kafka
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
            description: "Under-replicated partitions have been above 0 for over 5 minutes."
```

**Explicación:**
La `expr` suma las particiones subreplicadas en todo el cluster y comprueba si el total está por encima de 0. `for: 5m` requiere que la condición se mantenga durante 5 minutos antes de que la alerta pase a `firing`, reduciendo el ruido de picos momentáneos. `labels.severity` clasifica la severidad de la alerta para su uso en el enrutamiento de Alertmanager.
</details>

---

[Volver a los materiales de aprendizaje](../../../data-on-eks/kafka/07-monitoring.md) | [Cuestionario anterior: Integración con MSK](./06-msk-integration-quiz.md) | [Siguiente cuestionario: Mejores prácticas](./08-best-practices-quiz.md)
