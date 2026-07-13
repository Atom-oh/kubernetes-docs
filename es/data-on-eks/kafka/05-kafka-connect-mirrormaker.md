# Parte 5: Kafka Connect y MirrorMaker

> **Versiones compatibles**: Strimzi 0.45+, Kafka 3.9, MirrorMaker 2\
> **Última actualización**: July 9, 2026

## Descripción general de Kafka Connect

Kafka Connect es un framework para mover datos entre Kafka y sistemas externos — bases de datos, almacenamiento de objetos, motores de búsqueda y más — sin escribir código de integración personalizado. Describes un pipeline de datos de forma declarativa mediante la configuración del connector, y Connect se encarga del resto.

Los connectors vienen en dos variantes, según la dirección en la que fluyen los datos:

* **Source connectors** extraen datos HACIA Kafka desde un sistema externo. Debezium es el ejemplo canónico: lee el write-ahead log (o binlog) de una base de datos y transmite eventos de cambio a nivel de fila hacia Kafka como un pipeline de CDC (Change Data Capture). JDBC Source Connector usa un enfoque más simple basado en consultas, consultando periódicamente las tablas y escribiendo los resultados en Kafka.
* **Sink connectors** envían datos FUERA de Kafka hacia un sistema externo. S3 Sink Connector escribe datos de topics en S3 en formatos como JSON o Parquet, mientras que Elasticsearch Sink Connector indexa registros de topics para búsqueda y análisis.

Kafka Connect admite dos modos de runtime:

* **Distributed mode**: múltiples procesos worker (Pods) forman un grupo y actúan como un único cluster de Connect. Un worker actúa como coordinador del grupo, distribuyendo connectors y sus tasks entre el grupo; si un worker muere, sus tasks se rebalancean automáticamente hacia los workers sobrevivientes. El ciclo de vida del connector — crear, eliminar, reconfigurar — se controla mediante una REST API (puerto 8083 de forma predeterminada). Este es el único modo usado en Kubernetes.
* **Standalone mode**: un único proceso con un almacén de offsets basado en archivos, pensado para desarrollo local. No tiene alta disponibilidad ni escalado horizontal, por lo que nunca se usa en Kubernetes.

Los workers distribuidos persisten offsets, configuración de connectors/tasks y estado de tasks en tres topics internos (`offset.storage.topic`, `config.storage.topic`, `status.storage.topic`). Si estos topics se pierden, cada connector del cluster pierde su estado, por lo que los despliegues de producción siempre deben establecer su factor de replicación en al menos 3.

## Despliegue de Kafka Connect en Strimzi

Strimzi administra el propio cluster distribuido de Connect mediante el CRD `KafkaConnect`, y administra las instancias individuales de connectors que se ejecutan encima de él mediante el CRD `KafkaConnector`. Usar recursos `KafkaConnector` significa que los connectors pueden desplegarse y controlarse por versión mediante GitOps en lugar de llamar manualmente a la REST API. Para permitir que Strimzi reconcilie recursos `KafkaConnector`, el recurso `KafkaConnect` necesita la anotación `strimzi.io/use-connector-resources: "true"`.

Los plugins de connectors no vienen incluidos con la imagen base de Strimzi Kafka Connect, así que necesitas una imagen personalizada. El patrón recomendado por Strimzi evita escribir un Dockerfile a mano: declaras artefactos de plugins (tgz/zip/jar, o coordenadas Maven) bajo `KafkaConnect.spec.build`, y el Strimzi Operator construye la imagen y la envía a un registry que especifiques — como Amazon ECR.

### Especificación de build de KafkaConnect

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnect
metadata:
  name: connect-cluster
  namespace: kafka
  annotations:
    strimzi.io/use-connector-resources: "true"
spec:
  version: 3.9.0
  replicas: 3
  bootstrapServers: my-cluster-kafka-bootstrap:9093
  tls:
    trustedCertificates:
      - secretName: my-cluster-cluster-ca-cert
        certificate: ca.crt
  config:
    group.id: connect-cluster
    offset.storage.topic: connect-cluster-offsets
    config.storage.topic: connect-cluster-configs
    status.storage.topic: connect-cluster-status
    offset.storage.replication.factor: 3
    config.storage.replication.factor: 3
    status.storage.replication.factor: 3
    key.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter: org.apache.kafka.connect.json.JsonConverter
  build:
    output:
      type: docker
      image: <account-id>.dkr.ecr.<region>.amazonaws.com/connect-cluster:latest
      pushSecret: ecr-registry-credentials
    plugins:
      - name: debezium-postgres
        artifacts:
          - type: tgz
            url: https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/2.7.3.Final/debezium-connector-postgres-2.7.3.Final-plugin.tar.gz
      - name: aiven-s3-sink
        artifacts:
          - type: zip
            url: https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka/releases/download/v3.4.0/s3-sink-connector-for-apache-kafka-3.4.0.zip
  resources:
    requests:
      cpu: "1"
      memory: 2Gi
    limits:
      cpu: "2"
      memory: 2Gi
```

El Operator reconstruye la imagen y despliega el Deployment automáticamente cada vez que cambia `spec.build` — al agregar un plugin, subir una versión, etc. El Secret referenciado por `pushSecret` necesita credenciales de registry (un Secret de tipo `docker-registry`) para que el push a ECR tenga éxito; puedes conceder ese acceso mediante IRSA si lo deseas.

### KafkaConnector — ejemplo de source Debezium PostgreSQL

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

### KafkaConnector — ejemplo de sink S3

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnector
metadata:
  name: orders-s3-sink
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.aiven.kafka.connect.s3.S3SinkConnector
  tasksMax: 3
  config:
    topics: orders-db.public.orders
    aws.s3.bucket.name: orders-data-lake
    aws.s3.region: us-east-1
    format.output.type: jsonl
    file.compression.type: gzip
    flush.size: 10000
    rotate.schedule.interval.ms: 300000
```

`kubectl get kafkaconnector -n kafka` muestra el estado de cada connector; una condición `Ready: True` significa que sus tasks se han asignado a workers y están en ejecución.

## Arquitectura de MirrorMaker 2

MirrorMaker 2 (MM2) es una herramienta de replicación a nivel de topic, de cluster a cluster, construida sobre el framework Kafka Connect. Hace más que copiar mensajes: conserva el particionamiento del cluster de origen y traduce los offsets de consumer groups, que es lo que hace posible un failover limpio de consumers durante la recuperación ante desastres. Internamente, MM2 está compuesto por tres connectors:

* **MirrorSourceConnector**: realiza la replicación real de mensajes y también sincroniza la configuración de topics y ACLs.
* **MirrorCheckpointConnector**: traduce periódicamente los offsets de consumer groups del cluster de origen a los offsets equivalentes en el cluster de destino, registrándolos en un topic de checkpoints. Esta traducción de offsets es lo que permite que un consumer que hace failover al cluster de DR sepa "hasta dónde ya había procesado".
* **MirrorHeartbeatConnector**: envía mensajes heartbeat periódicos que demuestran que el cluster de origen está activo y que el pipeline de replicación está funcionando, lo que se usa para detectar lag de replicación o una desconexión total.

MM2 no reutiliza literalmente el nombre del topic de origen en el cluster de destino. La `DefaultReplicationPolicy` predeterminada nombra los topics remotos como `<source-cluster-alias>.<topic>`. Por ejemplo, replicar el topic `orders` desde un cluster con alias `us-east-1` produce un topic remoto llamado `us-east-1.orders` en el destino. Esta convención de nombres permite a los consumers distinguir los mensajes producidos localmente de los replicados solo por el nombre del topic, y también funciona como el mecanismo que evita bucles de replicación infinitos en configuraciones bidireccionales.

## Patrones de recuperación ante desastres

### Activo-Pasivo

Este es el patrón más común: la replicación se ejecuta en una sola dirección, desde un cluster de la región primaria hacia un cluster de la región de DR. En operación normal, las aplicaciones solo se comunican con el cluster primario, y el cluster de DR permanece inactivo, acumulando datos replicados. Cuando ocurre una falla regional, usas las traducciones de offsets registradas por MirrorCheckpointConnector para mover consumer groups al cluster de DR y reanudar el consumo desde el checkpoint disponible más reciente. Este no es un cambio exactamente-once perfecto — dependiendo de exactamente cuándo se tomó el checkpoint en relación con la falla, puede reprocesarse una pequeña cantidad de mensajes, y como la replicación de MM2 es asíncrona, cualquier mensaje que aún no se haya replicado al cluster de DR en el momento de la falla se pierde (el RPO está limitado por el lag de replicación, no es cero) — pero el beneficio clave es una recuperación rápida con pérdida de datos minimizada a esa ventana de lag.

### Activo-Activo

Ambas regiones atienden tráfico, y cada cluster replica bidireccionalmente hacia el otro. Esto introduce un riesgo real: un topic replicado A → B (como `A.orders`) podría replicarse de vuelta B → A, creando un bucle infinito, a menos que se evite explícitamente. Strimzi/MM2 se protege contra esto mediante la política de nombres configurada en `replication.policy.class` (la `DefaultReplicationPolicy` predeterminada, o `IdentityReplicationPolicy` si quieres que los topics remotos conserven sus nombres originales) — los topics que ya tienen un prefijo de cluster remoto (como `A.orders`) se excluyen de replicaciones posteriores. Restringir `topicsPattern` solo a los topics que realmente necesitan replicación entre regiones añade una segunda capa de protección contra bucles de replicación accidentales.

### Ejemplo de CR KafkaMirrorMaker2

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
      tls:
        trustedCertificates:
          - secretName: primary-cluster-ca-cert
            certificate: ca.crt
      authentication:
        type: tls
        certificateAndKey:
          secretName: mm2-user
          certificate: user.crt
          key: user.key
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

`connectCluster: dr-region` indica a los Pods worker de MM2 qué cluster (aquí, la región de DR) deben usar para almacenar los propios topics internos de Connect. Activar `sync.group.offsets.enabled: "true"` hace que MirrorCheckpointConnector escriba periódicamente sus offsets traducidos en `__consumer_offsets` del cluster de DR, para que un consumer con failover pueda reanudar el consumo sin confirmar offsets manualmente primero.

## Consideraciones de replicación entre regiones

* **Costo de red y latencia**: la replicación entre regiones (o incluso entre AZs) implica costo de transferencia de datos y latencia de ida y vuelta. Es común ejecutar los workers de MM2 en la región de destino, extrayendo datos del cluster de origen. Ajustar el tamaño de batch (`producer.override.batch.size`) y la compresión (`producer.override.compression.type: zstd`) reduce el volumen que realmente se transfiere, lo que se traduce directamente en un menor costo de transferencia de datos entre regiones.
* **`sync.topic.acls.enabled`**: controla si las ACLs de topics del cluster de origen también se sincronizan con el destino. Habilitarlo significa que no tienes que mantener dos veces la política de control de acceso, pero si los dos clusters tienen posturas de seguridad diferentes — por ejemplo, si el cluster de DR requiere un acceso más estricto que el primario — puede ser más seguro deshabilitarlo y administrar las ACLs de forma independiente en cada lado.
* **Monitoreo del lag de replicación**: MM2 expone sus propias métricas de salud de replicación. `replication-latency-ms` informa el tiempo desde que un mensaje se produjo en el origen hasta que se replicó completamente al destino, y las métricas relacionadas con lag del checkpoint connector muestran qué tan actualizada está la traducción de offsets. Recopilar estas métricas en Prometheus y alertar sobre un SLA (por ejemplo, "lag de replicación por debajo de 5 minutos") te permite verificar continuamente que el cluster de DR realmente está en un estado al que podrías hacer failover.

## Próximos pasos

Con Kafka Connect y MirrorMaker 2 implementados para movimiento de datos y recuperación ante desastres, el siguiente paso es ver cómo esta carga de trabajo se integra con — o se compara con — el servicio completamente administrado Amazon MSK. Eso se cubre en [Parte 6: Integración de MSK](./06-msk-integration.md).

[Volver a la página principal](./)

## Cuestionario

Para comprobar lo que aprendiste en este capítulo, prueba el [cuestionario del tema](../../quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md).
