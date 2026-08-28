# Parte 5: Kafka Connect y MirrorMaker

> **Versiones compatibles**: Strimzi 0.45+, Kafka 3.9, MirrorMaker 2\
> **Última actualización**: July 9, 2026

## Descripción general de Kafka Connect

Kafka Connect es un framework para mover datos entre Kafka y sistemas externos — bases de datos, almacenamiento de objetos, motores de búsqueda y más — sin escribir código de integración personalizado. Se describe un pipeline de datos de forma declarativa mediante la configuración del conector, y Connect se encarga del resto.

Los conectores se presentan en dos modalidades, según la dirección en que fluyen los datos:

* Los **conectores Source** extraen datos HACIA Kafka desde un sistema externo. Debezium es el ejemplo canónico: lee el write-ahead log de una base de datos (o binlog) y transmite eventos de cambio a nivel de fila a Kafka como un pipeline de CDC (Change Data Capture). JDBC Source Connector adopta un enfoque más simple basado en consultas, sondeando periódicamente las tablas y escribiendo los resultados en Kafka.
* Los **conectores Sink** envían datos FUERA de Kafka hacia un sistema externo. S3 Sink Connector escribe datos de topics en S3 en formatos como JSON o Parquet, mientras que Elasticsearch Sink Connector indexa registros de topics para búsqueda y análisis.

Kafka Connect admite dos modos de ejecución:

* **Modo distribuido**: varios procesos worker (Pods) forman un grupo y actúan como un único clúster de Connect. Un worker actúa como coordinador del grupo, distribuyendo los conectores y sus tareas por el grupo; si un worker falla, sus tareas se reequilibran automáticamente entre los workers supervivientes. El ciclo de vida del conector — crear, eliminar, reconfigurar — se controla mediante una API REST (puerto 8083 de forma predeterminada). Este es el único modo usado en Kubernetes.
* **Modo standalone**: un único proceso con un almacén de offsets basado en archivos, diseñado para el desarrollo local. No tiene alta disponibilidad ni escalado horizontal, por lo que nunca se usa en Kubernetes.

Los workers distribuidos conservan los offsets, la configuración de conectores/tareas y el estado de las tareas en tres topics internos (`offset.storage.topic`, `config.storage.topic`, `status.storage.topic`). Si estos topics se pierden, todos los conectores del clúster pierden su estado, por lo que los despliegues de producción siempre deben establecer su factor de replicación en al menos 3.

## Despliegue de Kafka Connect en Strimzi

Strimzi administra el clúster distribuido de Connect mediante el CRD `KafkaConnect`, y administra las instancias individuales de conectores que se ejecutan sobre él mediante el CRD `KafkaConnector`. Usar recursos `KafkaConnector` significa que los conectores se pueden desplegar y controlar por versiones mediante GitOps en lugar de llamar manualmente a la API REST. Para permitir que Strimzi reconcilie los recursos `KafkaConnector`, el recurso `KafkaConnect` necesita la anotación `strimzi.io/use-connector-resources: "true"`.

Los plugins de conectores no se incluyen en la imagen base de Strimzi Kafka Connect, así que se necesita una imagen personalizada. El patrón recomendado por Strimzi evita escribir un Dockerfile manualmente: se declaran los artefactos de plugins (tgz/zip/jar o coordenadas Maven) en `KafkaConnect.spec.build`, y Strimzi Operator crea la imagen y la envía a un registro que se especifique — como Amazon ECR.

### Especificación de compilación de KafkaConnect

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

El Operator recompila la imagen y realiza el despliegue progresivo del Deployment automáticamente cada vez que cambia `spec.build` — al añadir un plugin, actualizar una versión, etc. El Secret al que hace referencia `pushSecret` necesita credenciales de registro (un Secret de tipo `docker-registry`) para que el envío a ECR tenga éxito; si se desea, se puede conceder ese acceso mediante IRSA.

### KafkaConnector — ejemplo de Source de Debezium PostgreSQL

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

### KafkaConnector — ejemplo de Sink de S3

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

`kubectl get kafkaconnector -n kafka` muestra el estado de cada conector; una condición `Ready: True` significa que sus tareas se han asignado a workers y están en ejecución.

## Arquitectura de MirrorMaker 2

MirrorMaker 2 (MM2) es una herramienta de replicación de topics, de clúster a clúster, construida sobre el framework Kafka Connect. Hace más que copiar mensajes: conserva el particionamiento del clúster de origen y traduce los offsets de los grupos de consumidores, lo que permite una conmutación por error limpia de consumidores durante la recuperación ante desastres. Internamente, MM2 se compone de tres conectores:

* **MirrorSourceConnector**: realiza la replicación efectiva de mensajes y también sincroniza la configuración de topics y las ACL.
* **MirrorCheckpointConnector**: traduce periódicamente los offsets de grupos de consumidores del clúster de origen a los offsets equivalentes en el clúster de destino, registrándolos en un topic de checkpoint. Esta traducción de offsets permite que un consumidor que realiza conmutación por error al clúster de DR sepa «hasta dónde ya había procesado».
* **MirrorHeartbeatConnector**: envía mensajes periódicos de heartbeat que demuestran que el clúster de origen está activo y que el pipeline de replicación funciona; esto se utiliza para detectar lag de replicación o una desconexión total.

MM2 no reutiliza literalmente el nombre del topic de origen en el clúster de destino. La `DefaultReplicationPolicy` predeterminada nombra los topics remotos como `<source-cluster-alias>.<topic>`. Por ejemplo, replicar el topic `orders` desde un clúster con el alias `us-east-1` genera un topic remoto llamado `us-east-1.orders` en el destino. Esta convención de nomenclatura permite a los consumidores distinguir los mensajes producidos localmente de los replicados solo por el nombre del topic, y también funciona como el mecanismo que evita bucles de replicación infinitos en configuraciones bidireccionales.

## Patrones de recuperación ante desastres

### Activo-pasivo

Este es el patrón más común: la replicación se ejecuta en un único sentido, desde un clúster de región primaria a un clúster de región de DR. Durante la operación normal, las aplicaciones solo se comunican con el clúster primario y el clúster de DR permanece inactivo, acumulando datos replicados. Cuando se produce un fallo regional, se usan las traducciones de offsets registradas por MirrorCheckpointConnector para mover los grupos de consumidores al clúster de DR y reanudar el consumo desde el checkpoint disponible más reciente. No es una transición perfecta de exactly-once — según el momento exacto en que se tomó el checkpoint con respecto al fallo, se puede reprocesar un pequeño número de mensajes y, debido a que la replicación de MM2 es asíncrona, se pierde cualquier mensaje que todavía no se hubiera replicado al clúster de DR en el momento del fallo (el RPO está limitado por el lag de replicación, no es cero) — pero el beneficio clave es una recuperación rápida con la pérdida de datos reducida al mínimo dentro de esa ventana de lag.

### Activo-activo

Ambas regiones atienden tráfico y cada clúster replica bidireccionalmente al otro. Esto introduce un riesgo real: un topic replicado A → B (como `A.orders`) podría replicarse inmediatamente de vuelta de B → A, en un bucle infinito, a menos que se evite explícitamente. Strimzi/MM2 se protege contra esto mediante la política de nomenclatura establecida en `replication.policy.class` (la `DefaultReplicationPolicy` predeterminada o `IdentityReplicationPolicy` si se quiere que los topics remotos mantengan sus nombres originales) — los topics que ya llevan un prefijo de clúster remoto (como `A.orders`) se excluyen de una replicación posterior. Restringir `topicsPattern` únicamente a los topics que realmente necesitan replicación entre regiones añade una segunda capa de protección contra bucles de replicación accidentales.

### Ejemplo de CR de KafkaMirrorMaker2

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

`connectCluster: dr-region` indica a los Pods worker de MM2 qué clúster (en este caso, la región de DR) deben usar para almacenar los propios topics internos de Connect. Activar `sync.group.offsets.enabled: "true"` hace que MirrorCheckpointConnector escriba periódicamente sus offsets traducidos en `__consumer_offsets` del clúster de DR, de modo que un consumidor que haya realizado conmutación por error pueda reanudar el consumo sin confirmar offsets manualmente primero.

## Consideraciones sobre la replicación entre regiones

* **Costo y latencia de red**: la replicación entre regiones (o incluso entre AZ) implica un costo de transferencia de datos y latencia de ida y vuelta. Es habitual ejecutar los workers de MM2 en la región de destino, extrayendo datos del clúster de origen. Ajustar el tamaño de lote (`producer.override.batch.size`) y la compresión (`producer.override.compression.type: zstd`) reduce el volumen realmente transferido, lo que se traduce directamente en un menor costo de transferencia de datos entre regiones.
* **`sync.topic.acls.enabled`**: controla si las ACL de topics del clúster de origen también se sincronizan con el destino. Activarlo significa que no es necesario mantener la política de control de acceso dos veces, pero si los dos clústeres tienen posturas de seguridad diferentes — por ejemplo, el clúster de DR requiere acceso más estricto que el primario — puede ser más seguro desactivarlo y administrar las ACL de forma independiente en cada lado.
* **Monitorización del lag de replicación**: MM2 expone sus propias métricas de estado de la replicación. `replication-latency-ms` informa el tiempo transcurrido desde que se produjo un mensaje en el origen hasta que se replicó completamente en el destino, y las métricas relacionadas con el lag del conector de checkpoint muestran qué tan actualizada está la traducción de offsets. Incorporarlas a Prometheus y generar alertas para un SLA (por ejemplo, «lag de replicación inferior a 5 minutos») permite verificar continuamente que el clúster de DR realmente está en un estado al que se podría realizar conmutación por error.

## Próximos pasos

Con Kafka Connect y MirrorMaker 2 preparados para el movimiento de datos y la recuperación ante desastres, el siguiente paso es analizar cómo esta carga de trabajo se integra con — o se compara con — el servicio Amazon MSK completamente administrado. Esto se aborda en la [Parte 6: Integración con MSK](./06-msk-integration.md).

[Volver a la página principal](./README.md)

## Cuestionario

Para comprobar lo aprendido en este capítulo, prueba el [Cuestionario de topics](../../quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md).
