# Cuestionario de Kafka Connect y MirrorMaker

Este cuestionario evalúa tu comprensión del modelo de conectores source/sink de Kafka Connect, el modo distribuido, los CRD `KafkaConnect`/`KafkaConnector` de Strimzi, y la arquitectura de MirrorMaker 2 y sus patrones de recuperación ante desastres.

## Preguntas de opción múltiple

1. Un conector como Debezium, que lee el WAL/binlog de una base de datos y transmite eventos de cambio hacia Kafka, ¿qué tipo de conector es?
   - A) Sink connector
   - B) Source connector
   - C) Filter connector
   - D) Transform connector

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Source connector**

**Explicación:**
Los source connectors extraen datos HACIA Kafka desde un sistema externo. Debezium es el ejemplo canónico de un source connector de CDC (Change Data Capture): lee el write-ahead log (o binlog) de una base de datos y transmite eventos de cambio a nivel de fila hacia Kafka. Los sink connectors hacen lo contrario: envían datos FUERA de Kafka hacia sistemas externos como S3 o Elasticsearch.
</details>

2. ¿Qué tienen en común el S3 Sink Connector y el Elasticsearch Sink Connector?
   - A) Extraen datos desde un sistema externo hacia Kafka
   - B) Envían datos desde un topic de Kafka hacia un sistema externo
   - C) Replican datos entre topics
   - D) Administran offsets de consumer groups

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Envían datos desde un topic de Kafka hacia un sistema externo**

**Explicación:**
Tanto el S3 Sink Connector como el Elasticsearch Sink Connector son sink connectors, lo que significa que envían datos acumulados en un topic de Kafka hacia un sistema externo. S3 Sink Connector escribe datos de topics en un bucket de S3 en formatos como JSON o Parquet, mientras que Elasticsearch Sink Connector indexa datos de topics para búsqueda y análisis.
</details>

3. En el modo distribuido de Kafka Connect, ¿qué ocurre cuando un worker muere?
   - A) Todo el clúster de Connect se detiene
   - B) Las tareas del worker muerto se rebalancean automáticamente hacia otros workers supervivientes
   - C) El conector cambia automáticamente al modo standalone
   - D) Toda la información de offsets se restablece

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Las tareas del worker muerto se rebalancean automáticamente hacia otros workers supervivientes**

**Explicación:**
En modo distribuido, varios procesos worker forman un grupo que actúa como un único clúster de Connect, con un coordinador de grupo que distribuye conectores y tareas entre los workers. Si un worker muere, el coordinador lo detecta y rebalancea automáticamente las tareas de ese worker hacia los workers restantes para mantener la disponibilidad. Esta es la diferencia clave frente al modo standalone, que se ejecuta como un único proceso sin alta disponibilidad.
</details>

4. ¿Por qué el modo standalone de Kafka Connect nunca se usa en entornos Kubernetes/Strimzi?
   - A) No admite una REST API
   - B) No tiene alta disponibilidad ni escalabilidad horizontal
   - C) Solo admite source connectors
   - D) No admite TLS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) No tiene alta disponibilidad ni escalabilidad horizontal**

**Explicación:**
El modo standalone se ejecuta como un único proceso con un almacén de offsets basado en archivos, diseñado para desarrollo y pruebas locales. Como solo hay un worker, no hay otro worker que tome el control si falla, y la carga de trabajo no puede distribuirse entre varios nodos. Debido a estas limitaciones, los entornos Kubernetes/Strimzi siempre ejecutan el modo distribuido, respaldado por varios Pods.
</details>

5. ¿Cuál es la principal ventaja de usar el CRD `KafkaConnector` en Strimzi?
   - A) Te permite administrar conectores declarativamente mediante GitOps en lugar de llamar directamente a la REST API
   - B) Escribe automáticamente código de plugins de conectores por ti
   - C) Convierte el modo distribuido en modo standalone
   - D) Elimina la necesidad de un topic de almacenamiento de offsets

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Te permite administrar conectores declarativamente mediante GitOps en lugar de llamar directamente a la REST API**

**Explicación:**
Con el CRD `KafkaConnector`, no necesitas llamar directamente a la REST API de Connect para crear, eliminar o reconfigurar conectores: declaras el estado deseado en un manifiesto YAML, y el Strimzi Operator lo reconcilia con el estado real del conector. Esto habilita un flujo de trabajo GitOps donde la configuración del conector se controla por versión en un repositorio Git y se despliega mediante revisión de código/pipelines de CI.
</details>

6. ¿Qué anotación se requiere en un recurso `KafkaConnect` para habilitar el CRD `KafkaConnector` para él?
   - A) `strimzi.io/kraft: enabled`
   - B) `strimzi.io/node-pools: enabled`
   - C) `strimzi.io/use-connector-resources: "true"`
   - D) `strimzi.io/connect-mode: distributed`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) `strimzi.io/use-connector-resources: "true"`**

**Explicación:**
Agregar la anotación `strimzi.io/use-connector-resources: "true"` a los metadatos de un recurso `KafkaConnect` le indica al Strimzi Operator que observe los recursos `KafkaConnector` dirigidos a ese clúster de Connect y los reconcilie en conectores reales. Sin esta anotación, crear recursos `KafkaConnector` no tiene efecto.
</details>

7. ¿Qué caracteriza el enfoque recomendado de Strimzi para construir una imagen personalizada con plugins de conectores mediante `KafkaConnect.spec.build`?
   - A) Debes escribir un Dockerfile a mano
   - B) Declaras URLs de artefactos de plugins, y el Operator construye y envía la imagen al registry que especifiques
   - C) Las imágenes solo pueden enviarse a Docker Hub
   - D) Solo funciona en modo standalone

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Declaras URLs de artefactos de plugins, y el Operator construye y envía la imagen al registry que especifiques**

**Explicación:**
El patrón recomendado de Strimzi es completar declarativamente `KafkaConnect.spec.build` con un `output` (la imagen de registry destino y un push secret) y una lista de `plugins` (cada uno especificando URLs de artefactos tgz/zip/jar o coordenadas Maven). No se requiere Dockerfile: el Strimzi Operator realiza la compilación por sí mismo y envía la imagen resultante a un registry como Amazon ECR.
</details>

8. En MirrorMaker 2, ¿qué conector es responsable de traducir los offsets de consumer groups de un clúster source a los offsets equivalentes en el clúster target?
   - A) MirrorSourceConnector
   - B) MirrorHeartbeatConnector
   - C) MirrorCheckpointConnector
   - D) MirrorTopicConnector

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) MirrorCheckpointConnector**

**Explicación:**
MirrorCheckpointConnector traduce periódicamente los offsets de consumer groups de un clúster source a los offsets equivalentes en el clúster target y los registra en un topic de checkpoint. Esta traducción de offsets es lo que permite a un consumer group saber "cuánto había procesado ya" cuando hace failover al clúster de DR y necesita reanudar el consumo. MirrorSourceConnector maneja la replicación real de mensajes, topics y ACLs, mientras que MirrorHeartbeatConnector envía heartbeats que indican que el pipeline de replicación está vivo.
</details>

9. ¿Qué convención de nombres usa el `DefaultReplicationPolicy` predeterminado de MirrorMaker 2 para topics remotos?
   - A) `<topic>.<source-cluster-alias>`
   - B) `<source-cluster-alias>.<topic>`
   - C) `mirror-<topic>`
   - D) El nombre original del topic sin cambios

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `<source-cluster-alias>.<topic>`**

**Explicación:**
`DefaultReplicationPolicy` nombra los topics remotos como `<source-cluster-alias>.<topic>`. Por ejemplo, replicar el topic `orders` desde un clúster con alias `us-east-1` produce un topic remoto llamado `us-east-1.orders` en el clúster target. Mantener el nombre original sin cambios requiere `IdentityReplicationPolicy` en su lugar, lo que hace más difícil prevenir loops en una configuración active-active.
</details>

10. ¿Cuál es la diferencia central entre los patrones de DR active-passive y active-active?
    - A) Active-passive comprime datos y active-active no
    - B) Active-passive replica solo en una dirección, mientras que active-active replica bidireccionalmente y requiere prevención de loops
    - C) Active-active no usa MirrorMaker 2
    - D) Solo active-passive usa el CRD KafkaConnector

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Active-passive replica solo en una dirección, mientras que active-active replica bidireccionalmente y requiere prevención de loops**

**Explicación:**
El patrón active-passive replica en una sola dirección, desde el clúster primario hacia el clúster de DR, y el clúster de DR normalmente permanece inactivo. El patrón active-active replica bidireccionalmente entre ambos clústeres para que ambas regiones puedan atender tráfico, pero esto significa que un topic replicado podría reflejarse de vuelta a su clúster de origen, causando un loop infinito, a menos que se prevenga explícitamente mediante `replication.policy.class` y filtros de topics.
</details>

## Preguntas de respuesta corta

11. ¿Cuál es el nombre del conector de MirrorMaker 2 que envía periódicamente mensajes de heartbeat para señalar que el clúster source está vivo y que el pipeline de replicación está funcionando?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: MirrorHeartbeatConnector**

**Explicación:**
MirrorHeartbeatConnector envía periódicamente mensajes de heartbeat que indican que el clúster source está operando normalmente y que el pipeline de replicación no se ha interrumpido. Si estos heartbeats dejan de llegar durante un período de tiempo, esa ausencia puede usarse como señal para detectar lag de replicación o una conexión rota con el clúster source.
</details>

12. ¿Cuáles son los nombres de las tres claves de configuración de topics internos que los workers distribuidos de Strimzi Kafka Connect usan para almacenar offsets, configuración de conectores/tareas y estado de tareas? (por ejemplo, offset.storage.topic)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `offset.storage.topic`, `config.storage.topic`, `status.storage.topic`**

**Explicación:**
Los workers de Connect en modo distribuido usan tres topics internos: `offset.storage.topic` para offsets, `config.storage.topic` para configuración de conectores/tareas y `status.storage.topic` para estado de tareas. Si estos topics se pierden, cada conector del clúster pierde su estado, por lo que los despliegues de producción deben establecer su factor de replicación en al menos 3.
</details>

13. ¿Qué clave de configuración controla si MirrorMaker 2 también sincroniza los ACLs de topics del clúster source con el clúster target?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `sync.topic.acls.enabled`**

**Explicación:**
Establecer `sync.topic.acls.enabled` en `true` hace que los ACLs de topics del clúster source también se sincronicen con el clúster target, de modo que la política de control de acceso no tenga que mantenerse dos veces. Sin embargo, si los dos clústeres tienen posturas de seguridad distintas —por ejemplo, si el clúster de DR requiere un control de acceso más estricto— puede ser más seguro deshabilitar esto y administrar los ACLs de forma independiente en cada lado.
</details>

14. ¿Cuál es el nombre de la métrica que expone MirrorMaker 2 y que informa el tiempo desde que un mensaje se produjo en el clúster source hasta que se replicó completamente al target?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `replication-latency-ms`**

**Explicación:**
`replication-latency-ms` es una de las métricas principales expuestas por MirrorMaker 2, e informa el tiempo transcurrido desde que un mensaje se produjo en el clúster source hasta que se replicó completamente al clúster target. Hacer scraping de esta métrica en Prometheus y alertar sobre ella te permite verificar continuamente un SLA de lag de replicación.
</details>

15. En Strimzi, ¿qué campo de `spec` en un recurso `KafkaMirrorMaker2` especifica cuál de los clústeres configurados deben usar los Pods worker de MM2 para almacenar sus propios topics internos (offsets, configuración, etc.)?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `connectCluster`**

**Explicación:**
`KafkaMirrorMaker2.spec.connectCluster` apunta a uno de los alias de clúster definidos en `spec.clusters`, determinando qué clúster usan los Pods worker de MM2 para almacenar sus propios topics internos de Kafka Connect (topics de almacenamiento de offsets, configuración y estado). Normalmente se establece en el clúster de DR o target.
</details>

## Preguntas prácticas

16. Escribe un recurso `KafkaConnector` para un source connector Debezium PostgreSQL que se ejecute en un clúster `KafkaConnect` llamado `connect-cluster` (que tiene establecida la anotación `strimzi.io/use-connector-resources: "true"`). Limítalo a una sola tarea.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnector
metadata:
  name: orders-db-source
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.debezium.connector.postgresql.PostgresConnector
  tasksMax: 1
  config:
    database.hostname: orders-db.xxxxxxx.us-east-1.rds.amazonaws.com
    database.port: 5432
    database.user: debezium
    database.password: "${secrets:kafka/debezium-db-credentials:password}"
    database.dbname: orders
    topic.prefix: orders-db
    plugin.name: pgoutput
    slot.name: debezium_orders
    table.include.list: public.orders,public.order_items
```

**Explicación:**
La etiqueta `metadata.labels.strimzi.io/cluster: connect-cluster` le indica al Strimzi Operator en qué clúster `KafkaConnect` debe ejecutarse este `KafkaConnector`. `spec.class` especifica la clase real de implementación del conector (el conector Debezium PostgreSQL), y `plugin.name: pgoutput` especifica el plugin de salida de replicación lógica de PostgreSQL. `tasksMax: 1` refleja el hecho de que un source connector PostgreSQL solo puede usar un único replication slot, por lo que su trabajo no puede paralelizarse entre varias tareas.
</details>

17. Escribe un recurso `KafkaMirrorMaker2` que replique en una sola dirección topics que coincidan con `orders.*` y `payments.*` desde un clúster con alias `us-east-1` hacia un clúster con alias `dr-region`, sincronizando también offsets de consumer groups.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaMirrorMaker2
metadata:
  name: primary-to-dr
  namespace: kafka
spec:
  version: 3.9.0
  replicas: 3
  connectCluster: dr-region
  clusters:
    - alias: us-east-1
      bootstrapServers: primary-kafka-bootstrap.us-east-1.example.com:9093
    - alias: dr-region
      bootstrapServers: dr-kafka-bootstrap.us-west-2.example.com:9093
      config:
        config.storage.replication.factor: 3
        offset.storage.replication.factor: 3
        status.storage.replication.factor: 3
  mirrors:
    - sourceCluster: us-east-1
      targetCluster: dr-region
      sourceConnector:
        tasksMax: 5
        config:
          replication.factor: 3
          offset-syncs.topic.replication.factor: 3
          sync.topic.acls.enabled: "true"
      heartbeatConnector:
        config:
          heartbeats.topic.replication.factor: 3
      checkpointConnector:
        config:
          checkpoints.topic.replication.factor: 3
          sync.group.offsets.enabled: "true"
      topicsPattern: "orders.*|payments.*"
      groupsPattern: "orders-consumer-.*"
```

**Explicación:**
Cada entrada en la lista `mirrors` define una dirección de replicación (`sourceCluster` a `targetCluster`). `topicsPattern` restringe la replicación a `orders.*` y `payments.*`, y establecer `checkpointConnector.config.sync.group.offsets.enabled: "true"` hace que los offsets traducidos de consumer groups se escriban en `__consumer_offsets` del clúster target. `connectCluster: dr-region` designa la región de DR como el clúster donde los workers de MM2 almacenan sus topics internos.
</details>

18. Explica dos configuraciones que revisarías para evitar que un topic se replique infinitamente en un loop (A a B a A a B...) en una configuración active-active.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
1. `replication.policy.class` — con el `DefaultReplicationPolicy` predeterminado, los topics que ya tienen un prefijo de clúster remoto (`<alias>.<topic>`) se excluyen automáticamente de futuras replicaciones.
2. `topicsPattern` — restringir el patrón en cada dirección de mirroring para incluir explícitamente solo los topics que realmente necesitan replicación evita que topics no previstos queden atrapados en un ciclo de replicación.

**Explicación:**
La convención de nombres de `DefaultReplicationPolicy` (`<source-cluster-alias>.<topic>`) es en sí misma la primera línea de defensa contra loops: si el clúster B intenta replicar un topic como `A.orders` de vuelta al clúster A, MM2 lo reconoce como un topic remoto ya prefijado y no lo vuelve a replicar. Además, restringir explícitamente `topicsPattern` para cada dirección de mirroring reduce el riesgo de que un error de configuración o un patrón inusual de nombres de topics active accidentalmente un loop de replicación.
</details>

---

[Volver a los materiales de aprendizaje](../../../data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [Siguiente cuestionario: Integración con MSK](./06-msk-integration-quiz.md)
